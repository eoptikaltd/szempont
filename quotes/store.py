"""Szempont M2 — quote stores.

InMemoryQuoteStore backs local dev/UI and the pytest suite; BQQuoteStore is
the staging/production implementation over szempont.quotes (DDL 001+002).
Both expose the same API and the same semantics:

  * append-only revisions — save() never mutates a stored row, it appends
    revision N+1 with a fresh saved_at; readers take the latest revision
    (BQ: QUALIFY dedup, see 002_w2_rulings.sql);
  * D3 audit — a save that introduces or changes a discount emits a
    structured event for szempont.audit_log (event_type='discount');
  * validation — payer block (D1) and curated-discount invariants are
    enforced on every save, whatever path built the record.

Clock and id generation are injectable so tests stay deterministic; the
records layer itself stays pure.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .records import QuoteError, QuoteRecord, to_bq_row, validate_payer


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def validate_for_save(record: QuoteRecord) -> None:
    validate_payer(record.payer)
    if record.discount_net < 0:
        raise QuoteError("discount_net cannot be negative")
    if record.discount_net > 0 and not record.discount_config_id:
        raise QuoteError("discounts must come from a curated config (D3) — "
                         "discount_config_id missing")
    # Discount lines must declare their provenance (wave-gate fix 2026-07-16):
    # 'config' = D3 curated discount, config id must be on the quote;
    # 'override' = lens_price_overrides akciós ár, sku carries the override_id.
    for line in record.lines:
        if line.line_type != "discount":
            continue
        if line.source == "config":
            if not record.discount_config_id:
                raise QuoteError(f"config-sourced discount line {line.name!r} "
                                 "without discount_config_id (D3)")
        elif line.source == "override":
            if not line.sku:
                raise QuoteError(f"override discount line {line.name!r} "
                                 "missing the override_id (sku field)")
        else:
            raise QuoteError(f"discount line {line.name!r} has unknown "
                             f"source {line.source!r} — must be "
                             "'config' or 'override'")


def _discount_changed(prev: QuoteRecord | None, cur: QuoteRecord) -> bool:
    if cur.discount_net == 0 and cur.discount_config_id is None:
        return False
    return (prev is None
            or prev.discount_net != cur.discount_net
            or prev.discount_config_id != cur.discount_config_id)


def discount_audit_event(record: QuoteRecord, event_id: str,
                         occurred_at: str, marker: str | None = None) -> dict:
    """szempont.audit_log row for a discount grant/change (code standard).

    marker: extra provenance flag in the payload — e.g. 'auto_approved_pre_m5'
    when the UI approved a gated discount itself because the M5 permission
    system has not shipped yet (review ruling 2026-07-16).
    """
    payload = {
        "quote_id": record.quote_id,
        "revision": record.revision,
        "discount_config_id": record.discount_config_id,
        "discount_net": str(record.discount_net),
        "approved_by": record.discount_approved_by,
    }
    if marker:
        payload["marker"] = marker
    return {
        "event_id": event_id,
        "event_type": "discount",
        "actor": record.discount_approved_by or record.created_by,
        "payload": json.dumps(payload, ensure_ascii=False),
        "occurred_at": occurred_at,
    }


class InMemoryQuoteStore:
    """Dev/UI/test store. Keeps full revision history per quote_id."""

    def __init__(self, now_fn=_utc_now, id_fn=_new_id):
        self._revs: dict[str, list[QuoteRecord]] = {}
        self.audit_events: list[dict] = []
        self._now = now_fn
        self._id = id_fn

    def save(self, record: QuoteRecord) -> QuoteRecord:
        import dataclasses
        validate_for_save(record)
        prev_revs = self._revs.setdefault(record.quote_id, [])
        prev = prev_revs[-1] if prev_revs else None
        rev = dataclasses.replace(record, revision=len(prev_revs),
                                  saved_at=self._now())
        if _discount_changed(prev, rev):
            self.audit_events.append(
                discount_audit_event(rev, self._id(), rev.saved_at))
        prev_revs.append(rev)
        return rev

    def load(self, quote_id: str) -> QuoteRecord | None:
        revs = self._revs.get(quote_id)
        return revs[-1] if revs else None

    def revisions(self, quote_id: str) -> tuple[QuoteRecord, ...]:
        return tuple(self._revs.get(quote_id, ()))

    def load_offer_set(self, offer_set_id: str) -> tuple[QuoteRecord, ...]:
        """Latest revision of every variant in the carousel set (D6)."""
        return tuple(revs[-1] for revs in self._revs.values()
                     if revs and revs[-1].offer_set_id == offer_set_id)


class BQQuoteStore:  # pragma: no cover — exercised in staging against real BQ
    """Append-only store over szempont.quotes + szempont.audit_log.

    Uses batch load jobs (not streaming inserts) for the same reason as
    ingest.bq_client.BQClient: streamed rows are stuck in the streaming
    buffer, which would break read-after-write for the POS UI.
    """

    QUOTES = "szempont.quotes"
    AUDIT = "szempont.audit_log"
    _LATEST = """
    SELECT * FROM `szempont.quotes`
    WHERE {where}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY quote_id ORDER BY IFNULL(revision, 0) DESC) = 1
    """

    def __init__(self, client, now_fn=_utc_now, id_fn=_new_id):
        self.client = client
        self._now = now_fn
        self._id = id_fn

    def _load_rows(self, table: str, rows: list[dict]) -> None:
        from google.cloud import bigquery
        job = self.client.load_table_from_json(
            rows, table,
            job_config=bigquery.LoadJobConfig(
                labels={"tool": "szempont"},
                write_disposition="WRITE_APPEND",
            ),
        )
        job.result()
        if job.errors:
            raise RuntimeError(f"BQ load errors on {table}: {job.errors[:5]}")

    def _query_latest(self, where: str, params: list) -> list[QuoteRecord]:
        from google.cloud import bigquery
        from .records import from_bq_row
        job = self.client.query(
            self._LATEST.format(where=where),
            job_config=bigquery.QueryJobConfig(
                labels={"tool": "szempont"}, query_parameters=params))
        return [from_bq_row(dict(r)) for r in job.result()]

    def save(self, record: QuoteRecord) -> QuoteRecord:
        import dataclasses
        validate_for_save(record)
        prev = self.load(record.quote_id)
        rev = dataclasses.replace(
            record,
            revision=(prev.revision + 1) if prev else 0,
            saved_at=self._now())
        rows = [to_bq_row(rev)]
        self._load_rows(self.QUOTES, rows)
        if _discount_changed(prev, rev):
            self._load_rows(self.AUDIT, [
                discount_audit_event(rev, self._id(), rev.saved_at)])
        return rev

    def load(self, quote_id: str) -> QuoteRecord | None:
        from google.cloud import bigquery
        recs = self._query_latest("quote_id = @qid", [
            bigquery.ScalarQueryParameter("qid", "STRING", quote_id)])
        return recs[0] if recs else None

    def load_offer_set(self, offer_set_id: str) -> tuple[QuoteRecord, ...]:
        from google.cloud import bigquery
        return tuple(self._query_latest("offer_set_id = @oid", [
            bigquery.ScalarQueryParameter("oid", "STRING", offer_set_id)]))
