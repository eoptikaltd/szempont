"""Szempont M4 — order stores + eseménynapló.

Same store discipline as quotes/store.py: append-only revisions (readers
take the latest revision; BQ uses the QUALIFY dedup pattern), injectable
clock/id functions, validation on every save. Two extra surfaces:

  * order_events (eseménynapló) — one append-only row per meaningful thing
    that happened to an order (created, status change, cancel, Tharanis
    dry-run, SKU promotion registration). The UI renders this verbatim.
  * cancel audit — R7: EVERY cancel writes a szempont.audit_log event with
    the acting operator, whoever they are (any staff member may cancel).
"""

from __future__ import annotations

import dataclasses
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .records import (OrderError, OrderRecord, OrderStatus, order_totals,
                      to_bq_row, validate_payer)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


EVENT_TYPES = ("created", "status", "cancel", "tharanis_dry_run",
               "promotion", "note")


@dataclass(frozen=True, slots=True)
class OrderEvent:
    """One szempont.order_events row (eseménynapló entry)."""
    event_id: str
    order_id: str
    event_type: str                   # EVENT_TYPES
    actor: str
    occurred_at: str                  # ISO timestamp
    note: str = ""                    # human-readable, Hungarian, UI-rendered
    payload: str | None = None        # JSON detail (dry-run XML, statuses...)


def validate_for_save(order: OrderRecord) -> None:
    validate_payer(order.payer)
    if order.discount_net < 0:
        raise OrderError("discount_net cannot be negative")
    if order.discount_net > 0 and not order.discount_config_id:
        raise OrderError("order discounts must reference the curated config "
                         "(D3) — discount_config_id missing")
    if order.status is OrderStatus.LEMONDVA and not order.cancel_reason:
        raise OrderError("cancelled order without cancel_reason (R7)")


def order_cancel_audit_event(order: OrderRecord, actor: str, event_id: str,
                             occurred_at: str) -> dict:
    """szempont.audit_log row for a cancel — R7: any staff may cancel, but
    every cancel lands here with the actor."""
    return {
        "event_id": event_id,
        "event_type": "order_cancel",
        "actor": actor,
        "payload": json.dumps({
            "order_id": order.order_id,
            "quote_id": order.quote_id,
            "reason": order.cancel_reason,
            "gross": str(order_totals(order).total_retail_gross),
        }, ensure_ascii=False),
        "occurred_at": occurred_at,
    }


def _same_content(a: OrderRecord, b: OrderRecord) -> bool:
    norm = lambda r: dataclasses.replace(r, revision=0, saved_at="")  # noqa: E731
    return norm(a) == norm(b)


class InMemoryOrderStore:
    """Dev/UI/test store. Full revision history + eseménynapló per order."""

    def __init__(self, now_fn=_utc_now, id_fn=_new_id):
        self._revs: dict[str, list[OrderRecord]] = {}
        self._events: dict[str, list[OrderEvent]] = {}
        self.audit_events: list[dict] = []
        self._now = now_fn
        self._id = id_fn

    # ------------------------------------------------------------------ orders
    def save(self, order: OrderRecord, *, actor: str,
             event_note: str = "", expect_new: bool = False) -> OrderRecord:
        validate_for_save(order)
        revs = self._revs.setdefault(order.order_id, [])
        prev = revs[-1] if revs else None
        if expect_new and prev is not None:
            # F-W3-02: the sequence-race backstop promised in orders/ids.py —
            # a collided SZP- id must fail LOUD, never merge two orders into
            # one revision chain.
            raise OrderError(f"order id {order.order_id} already exists — "
                             "sequence race, retry the save")
        if prev is not None and _same_content(prev, order):
            return prev                              # unchanged -> no-op
        rev = dataclasses.replace(order, revision=len(revs),
                                  saved_at=self._now())
        revs.append(rev)
        if prev is None:
            self.add_event(rev.order_id, "created", actor,
                           note=event_note or f"Megrendelés felvéve "
                                              f"({rev.order_id})")
        elif prev.status != rev.status:
            if rev.status is OrderStatus.LEMONDVA:
                ev_id = self._id()
                self.audit_events.append(order_cancel_audit_event(
                    rev, actor, ev_id, rev.saved_at))
                self.add_event(rev.order_id, "cancel", actor,
                               note=event_note
                               or f"Lemondva — {rev.cancel_reason}",
                               payload=json.dumps(
                                   {"from": str(prev.status),
                                    "reason": rev.cancel_reason},
                                   ensure_ascii=False))
            else:
                from .records import STATUS_HU
                self.add_event(rev.order_id, "status", actor,
                               note=event_note or
                               f"{STATUS_HU[prev.status]} → "
                               f"{STATUS_HU[rev.status]}",
                               payload=json.dumps(
                                   {"from": str(prev.status),
                                    "to": str(rev.status)}))
        elif event_note:
            self.add_event(rev.order_id, "note", actor, note=event_note)
        return rev

    def load(self, order_id: str) -> OrderRecord | None:
        revs = self._revs.get(order_id)
        return revs[-1] if revs else None

    def list_orders(self) -> tuple[OrderRecord, ...]:
        """Latest revision of every order, newest order_id first."""
        latest = [revs[-1] for revs in self._revs.values() if revs]
        return tuple(sorted(latest, key=lambda o: o.order_id, reverse=True))

    def all_ids(self) -> tuple[str, ...]:
        return tuple(self._revs.keys())

    # ------------------------------------------------------------ eseménynapló
    def add_event(self, order_id: str, event_type: str, actor: str, *,
                  note: str = "", payload: str | None = None) -> OrderEvent:
        if event_type not in EVENT_TYPES:
            raise OrderError(f"unknown event_type {event_type!r}")
        ev = OrderEvent(event_id=self._id(), order_id=order_id,
                        event_type=event_type, actor=actor,
                        occurred_at=self._now(), note=note, payload=payload)
        self._events.setdefault(order_id, []).append(ev)
        return ev

    def events(self, order_id: str) -> tuple[OrderEvent, ...]:
        return tuple(self._events.get(order_id, ()))


class BQOrderStore:  # pragma: no cover — exercised in staging against real BQ
    """Append-only store over szempont.orders + order_events + audit_log
    (DDL 003). Batch load jobs, not streaming inserts — read-after-write."""

    ORDERS = "szempont.orders"
    EVENTS = "szempont.order_events"
    AUDIT = "szempont.audit_log"
    _LATEST = """
    SELECT * FROM `szempont.orders`
    WHERE {where}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_id ORDER BY IFNULL(revision, 0) DESC) = 1
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
                write_disposition="WRITE_APPEND"))
        job.result()
        if job.errors:
            raise RuntimeError(f"BQ load errors on {table}: {job.errors[:5]}")

    def _query_latest(self, where: str, params: list) -> list[OrderRecord]:
        from google.cloud import bigquery
        from .records import from_bq_row
        job = self.client.query(
            self._LATEST.format(where=where),
            job_config=bigquery.QueryJobConfig(
                labels={"tool": "szempont"}, query_parameters=params))
        return [from_bq_row(dict(r)) for r in job.result()]

    def save(self, order: OrderRecord, *, actor: str,
             event_note: str = "", expect_new: bool = False) -> OrderRecord:
        validate_for_save(order)
        prev = self.load(order.order_id)
        if expect_new and prev is not None:
            raise OrderError(f"order id {order.order_id} already exists — "
                             "sequence race, retry the save (F-W3-02)")
        if prev is not None and _same_content(prev, order):
            return prev
        rev = dataclasses.replace(
            order, revision=(prev.revision + 1) if prev else 0,
            saved_at=self._now())
        self._load_rows(self.ORDERS, [to_bq_row(rev)])
        if prev is None:
            self.add_event(rev.order_id, "created", actor,
                           note=event_note or f"Megrendelés felvéve "
                                              f"({rev.order_id})")
        elif prev.status != rev.status:
            if rev.status is OrderStatus.LEMONDVA:
                self._load_rows(self.AUDIT, [order_cancel_audit_event(
                    rev, actor, self._id(), rev.saved_at)])
                self.add_event(rev.order_id, "cancel", actor,
                               note=event_note
                               or f"Lemondva — {rev.cancel_reason}")
            else:
                from .records import STATUS_HU
                self.add_event(rev.order_id, "status", actor,
                               note=event_note or
                               f"{STATUS_HU[prev.status]} → "
                               f"{STATUS_HU[rev.status]}")
        return rev

    def load(self, order_id: str) -> OrderRecord | None:
        from google.cloud import bigquery
        recs = self._query_latest("order_id = @oid", [
            bigquery.ScalarQueryParameter("oid", "STRING", order_id)])
        return recs[0] if recs else None

    def list_orders(self) -> tuple[OrderRecord, ...]:
        return tuple(self._query_latest("TRUE", []))

    def all_ids(self) -> tuple[str, ...]:
        from google.cloud import bigquery
        job = self.client.query(
            f"SELECT DISTINCT order_id FROM `{self.ORDERS}`",
            job_config=bigquery.QueryJobConfig(labels={"tool": "szempont"}))
        return tuple(r["order_id"] for r in job.result())

    def add_event(self, order_id: str, event_type: str, actor: str, *,
                  note: str = "", payload: str | None = None) -> OrderEvent:
        if event_type not in EVENT_TYPES:
            raise OrderError(f"unknown event_type {event_type!r}")
        ev = OrderEvent(event_id=self._id(), order_id=order_id,
                        event_type=event_type, actor=actor,
                        occurred_at=self._now(), note=note, payload=payload)
        self._load_rows(self.EVENTS, [dataclasses.asdict(ev)])
        return ev

    def events(self, order_id: str) -> tuple[OrderEvent, ...]:
        from google.cloud import bigquery
        job = self.client.query(
            f"SELECT * FROM `{self.EVENTS}` WHERE order_id = @oid "
            "ORDER BY occurred_at",
            job_config=bigquery.QueryJobConfig(
                labels={"tool": "szempont"},
                query_parameters=[bigquery.ScalarQueryParameter(
                    "oid", "STRING", order_id)]))
        return tuple(OrderEvent(**dict(r)) for r in job.result())
