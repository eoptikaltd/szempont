"""M1 (rev 2) — szempont-catalog-sync (Cloud Run job, STAGING ONLY this wave).

Flow:
  1. Fetch rows from a CatalogSource (production: BQEyeTechSource over
     sf6_catalog_converter.pl_items_enriched — no FS6 parsing anywhere here).
  2. catalog_version = "<supplier>-<sha256[:12]>" of the canonical row set
     (sorted, stable JSON) — same data twice => same version.
  3. Write szempont.lens_catalog: delete version, batch-load rows stamped
     with catalog_version / effective_from / _ingested_at. Idempotent.
  4. Health report: row counts per family, price deltas vs previous version,
     dormant share, and data-quality warnings (non-positive price,
     SKU charset anomalies; the '|' zero-power separator is known grammar
     and counted, not warned).

Every BQ job labeled tool=szempont; writes only inside szempont*.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import asdict, dataclass

from .source import CatalogRow, CatalogSource

BQ_LABELS = {"tool": "szempont"}
TARGET = "szempont.lens_catalog"

_SKU_OK = re.compile(r"^[A-Z0-9+\-|.]+$")


def compute_catalog_version(supplier: str, rows: list[CatalogRow]) -> str:
    canon = json.dumps([asdict(r) for r in sorted(rows, key=lambda x: x.sku)],
                       sort_keys=True, ensure_ascii=False)
    return f"{supplier}-{hashlib.sha256(canon.encode('utf-8')).hexdigest()[:12]}"


@dataclass
class SyncResult:
    catalog_version: str
    supplier: str
    row_count: int
    health_report: dict


def build_health_report(version: str, supplier: str, rows: list[CatalogRow],
                        previous_prices: dict[str, float] | None) -> dict:
    by_family: dict[str, int] = {}
    warnings: list[str] = []
    pipe_skus = 0
    for r in rows:
        by_family[r.famcode] = by_family.get(r.famcode, 0) + 1
        if r.retail_net_huf <= 0:
            warnings.append(f"non-positive price on {r.sku}")
        if "|" in r.sku:
            pipe_skus += 1
        elif not _SKU_OK.match(r.sku):
            warnings.append(f"unexpected characters in SKU {r.sku!r}")

    deltas: list[dict] = []
    if previous_prices:
        current = {r.sku: r.retail_net_huf for r in rows}
        for sku, old in sorted(previous_prices.items()):
            new = current.get(sku)
            if new is None:
                deltas.append({"sku": sku, "change": "removed",
                               "old": old, "new": None})
            elif abs(new - old) >= 0.5:
                deltas.append({"sku": sku, "change": "price",
                               "old": old, "new": new,
                               "pct": round((new - old) / old * 100, 1) if old else None})
        for sku in sorted(set(current) - set(previous_prices)):
            deltas.append({"sku": sku, "change": "added",
                           "old": None, "new": current[sku]})

    dormant = sum(1 for r in rows if r.is_dormant)
    return {
        "catalog_version": version,
        "supplier": supplier,
        "row_count": len(rows),
        "rows_by_family": by_family,
        "dormant_count": dormant,
        "dormant_share_pct": round(100 * dormant / len(rows), 1) if rows else 0,
        "zero_power_pipe_skus": pipe_skus,
        "warnings": warnings,
        "warning_count": len(warnings),
        "price_deltas": deltas,
        "delta_count": len(deltas),
    }


def run_sync(
    source: CatalogSource,
    supplier: str,
    bq,                      # duck-typed: delete_version(), load_rows(), fetch_prices()
    effective_from: str | None = None,
    now: dt.datetime | None = None,
) -> SyncResult:
    now = now or dt.datetime.now(dt.timezone.utc)
    effective_from = effective_from or now.date().isoformat()

    rows = list(source.fetch())
    version = compute_catalog_version(supplier, rows)

    previous_prices = bq.fetch_prices(supplier=supplier, exclude_version=version)

    stamped = [{
        **asdict(r),
        "catalog_version": version,
        "effective_from": effective_from,
        "_ingested_at": now.isoformat(),
    } for r in rows]

    bq.delete_version(TARGET, version)
    bq.load_rows(TARGET, stamped, labels=BQ_LABELS)

    report = build_health_report(version, supplier, rows, previous_prices)
    return SyncResult(catalog_version=version, supplier=supplier,
                      row_count=len(rows), health_report=report)


def main() -> None:  # pragma: no cover — GCP wiring, exercised in staging
    import os
    from google.cloud import bigquery

    from .bq_client import BQClient
    from .source import BQEyeTechSource

    client = bigquery.Client(
        project=os.environ.get("GCP_PROJECT", "natural-caster-496309-j3"))
    result = run_sync(source=BQEyeTechSource(client), supplier="eyetech",
                      bq=BQClient(client))
    print(json.dumps(result.health_report, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    main()
