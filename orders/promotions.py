"""Szempont M4 — SKU promotion registry (R13, hard rule 9).

Every lens variation is a real SKU living in the Szempont catalog (BQ); a
SKU reaches the company-wide ERP on its FIRST SALE. Per R13 + F-W3-01 the
automated Tharanis article-create (berak → cikk) is NOT built yet — the
registry records first sales (status 'pending') and a daily digest artifact
surfaces them for the manual/verified path. Automated create becomes a
separate flagged commit only after F-W3-01 gains a "berak verified"
follow-up.

Terminology ruling 2026-07-18: Unas is webshop-only and NOT in the store
order loop — the promotion target is Tharanis (tharanis_cikksz column), not
Unas. The DDL 001 sku_promotions stub carried a unas_product_id column;
DDL 003 replaces it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .records import OrderRecord

PROMO_STATUSES = ("pending", "created", "failed")


@dataclass(frozen=True, slots=True)
class PromotionRow:
    """One szempont.sku_promotions row (DDL 003)."""
    sku: str
    catalog_version: str
    first_sale_order_id: str
    registered_at: str                # ISO timestamp
    status: str = "pending"           # pending|created|failed
    tharanis_cikksz: str | None = None  # set only after a verified create


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryPromotionRegistry:
    """Dev/test registry; BQPromotionRegistry mirrors the API in staging."""

    def __init__(self, now_fn=_utc_now):
        self._rows: dict[str, PromotionRow] = {}
        self._now = now_fn

    def register(self, sku: str, catalog_version: str,
                 order_id: str) -> PromotionRow | None:
        """Idempotent: only the FIRST sale registers; later sales no-op."""
        if sku in self._rows:
            return None
        row = PromotionRow(sku=sku, catalog_version=catalog_version,
                           first_sale_order_id=order_id,
                           registered_at=self._now())
        self._rows[sku] = row
        return row

    def known(self, sku: str) -> bool:
        return sku in self._rows

    def rows(self) -> tuple[PromotionRow, ...]:
        return tuple(self._rows.values())

    def pending(self) -> tuple[PromotionRow, ...]:
        return tuple(r for r in self._rows.values() if r.status == "pending")


def register_first_sale(registry, order: OrderRecord) -> list[PromotionRow]:
    """Register every lens SKU on the order that the registry hasn't seen.
    Returns the NEW rows (empty when all SKUs were already registered) so
    the caller can put them on the order's eseménynapló."""
    new: list[PromotionRow] = []
    seen: set[str] = set()
    for line in order.lines:
        if line.line_type != "lens" or not line.sku or line.sku in seen:
            continue
        seen.add(line.sku)
        row = registry.register(line.sku, order.catalog_version,
                                order.order_id)
        if row is not None:
            new.append(row)
    return new


def daily_digest(rows, digest_date: str) -> str:
    """R13 daily digest artifact: the pending SKUs awaiting their Tharanis
    article, as a small Hungarian markdown report (mailed/posted by the
    scheduler once M9-lite lands; until then it is written to GCS/stdout)."""
    pending = [r for r in rows if r.status == "pending"]
    lines = [f"# Szempont — új SKU-k Tharanis felvételre · {digest_date}", ""]
    if not pending:
        lines.append("Nincs függőben lévő SKU. ✔")
        return "\n".join(lines) + "\n"
    lines += [f"{len(pending)} lencse SKU vár cikktörzs-felvételre "
              "(első eladás megtörtént, R13 — kézi/ellenőrzött út):", ""]
    lines += ["| SKU | Katalógusverzió | Első eladás | Regisztrálva |",
              "|---|---|---|---|"]
    for r in sorted(pending, key=lambda r: r.registered_at):
        lines.append(f"| `{r.sku}` | {r.catalog_version} "
                     f"| {r.first_sale_order_id} | {r.registered_at[:10]} |")
    lines += ["", "Automatikus cikk-berak: F-W3-01 lezárásáig tiltva; "
              "a felvétel után a sor státusza 'created' + tharanis_cikksz."]
    return "\n".join(lines) + "\n"


class BQPromotionRegistry:  # pragma: no cover — staging only
    """szempont.sku_promotions over batch loads (DDL 003)."""

    TABLE = "szempont.sku_promotions"

    def __init__(self, client, now_fn=_utc_now):
        self.client = client
        self._now = now_fn

    def known(self, sku: str) -> bool:
        from google.cloud import bigquery
        job = self.client.query(
            f"SELECT 1 FROM `{self.TABLE}` WHERE sku = @sku LIMIT 1",
            job_config=bigquery.QueryJobConfig(
                labels={"tool": "szempont"},
                query_parameters=[bigquery.ScalarQueryParameter(
                    "sku", "STRING", sku)]))
        return len(list(job.result())) > 0

    def register(self, sku: str, catalog_version: str,
                 order_id: str) -> PromotionRow | None:
        if self.known(sku):
            return None
        row = PromotionRow(sku=sku, catalog_version=catalog_version,
                           first_sale_order_id=order_id,
                           registered_at=self._now())
        from google.cloud import bigquery
        job = self.client.load_table_from_json(
            [asdict(row)], self.TABLE,
            job_config=bigquery.LoadJobConfig(
                labels={"tool": "szempont"},
                write_disposition="WRITE_APPEND"))
        job.result()
        return row

    def pending(self) -> tuple[PromotionRow, ...]:
        from google.cloud import bigquery
        job = self.client.query(
            f"SELECT * FROM `{self.TABLE}` WHERE status = 'pending'",
            job_config=bigquery.QueryJobConfig(labels={"tool": "szempont"}))
        return tuple(PromotionRow(**{k: v for k, v in dict(r).items()})
                     for r in job.result())


if __name__ == "__main__":  # pragma: no cover — scheduler entry (digest)
    import sys
    from datetime import date
    print(daily_digest([], date.today().isoformat()), file=sys.stdout)
