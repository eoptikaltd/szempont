"""M1 (rev 2) — catalog sources for Szempont.

RULING (Sabie, 2026-07-12): Szempont does NOT parse FS6/SF6. Supplier and
private-label catalogues reach BigQuery via the separate sf6-converter
project (eoptikaltd/sf6-converter, package sf6gen); Szempont consumes the
converted, eOptika-specific SKU data. Hard rule 2 still applies: the source
sits behind an adapter so tomorrow's Hoya import lands as another
CatalogSource, not a rewrite.

Current production source: sf6_catalog_converter.pl_items_enriched
(EyeTech private label, 1,111 SKUs, one row per real power SKU).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

PL_VIEW = "natural-caster-496309-j3.sf6_catalog_converter.pl_items_enriched"


@dataclass(frozen=True)
class CatalogRow:
    """One real, orderable lens SKU (hard rule 9) with exact powers."""
    sku: str
    supplier: str
    famcode: str
    name: str
    sph: float
    cyl: float
    add_power: float
    diameter_mm: float
    refractive_index: float
    design: str            # spheric | aspheric (per family)
    coating_code: str      # HMC (SHMC label decision pending w/ Sabie)
    blue_filter: bool
    retail_net_huf: float
    rank_score: float      # precomputed outside Szempont (ruling 2026-07-16: no COGS here)
    is_dormant: bool


class CatalogSource(Protocol):
    def fetch(self) -> Iterable[CatalogRow]: ...


class InMemorySource:
    def __init__(self, rows: list[CatalogRow]):
        self._rows = rows

    def fetch(self) -> list[CatalogRow]:
        return list(self._rows)


PL_SQL = f"""
SELECT sku, famcode, sku_name, sph, cyl, add_power, diameter_mm,
       refractive_index, design, coating_code, blue_filter,
       price_huf, is_dormant
FROM `{PL_VIEW}`
WHERE NOT is_quarantined
ORDER BY sku
"""


class BQEyeTechSource:  # pragma: no cover — exercised on dev-box/staging
    """Reads the converted EyeTech PL catalogue. Read-only, label tool=szempont."""

    def __init__(self, client):
        self.client = client

    def fetch(self) -> list[CatalogRow]:
        from google.cloud import bigquery
        job = self.client.query(PL_SQL, job_config=bigquery.QueryJobConfig(
            labels={"tool": "szempont"}))
        out = []
        for r in job.result():
            out.append(CatalogRow(
                sku=r["sku"], supplier="eyetech", famcode=r["famcode"],
                name=r["sku_name"] or r["sku"],
                sph=float(r["sph"] or 0), cyl=float(r["cyl"] or 0),
                add_power=float(r["add_power"] or 0),
                diameter_mm=float(r["diameter_mm"] or 0),
                refractive_index=float(r["refractive_index"] or 0),
                design=r["design"] or "", coating_code=r["coating_code"] or "",
                blue_filter=bool(r["blue_filter"]),
                retail_net_huf=float(r["price_huf"] or 0),
                rank_score=0.0,  # TODO: read from rank view once published
                is_dormant=bool(r["is_dormant"]),
            ))
        return out
