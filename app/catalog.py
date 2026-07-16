"""Catalog snapshot loader for the Szempont UI.

Today: demo fixture (same shape the tests use) so the UI runs before M1 has
ingested a real supplier file. Production: read the latest catalog_version
per supplier from szempont.lens_catalog_* (dedup by _ingested_at) and build
the same CatalogSnapshot — the pricing engine never knows the difference.
"""
from decimal import Decimal as D
from functools import lru_cache

from pricing.models import (
    CatalogSnapshot, CoatingTier, LensDesign, LensProduct, PriceOverride,
    RxRange, Surcharge,
)


@lru_cache(maxsize=1)
def load_snapshot() -> CatalogSnapshot:
    # TODO(M1→UI wiring): replace with BigQuery-backed loader once a real
    # catalog is ingested; keep the return type identical.
    sv = RxRange(D("-8"), D("6"), D("0"), D("4"))
    lenses = {}
    def add(sku, sup, code, name, design, idx, dia, tier, photo, retail, cost,
            surch, rank='0', dormant=False):
        lenses[sku] = LensProduct(
            sku=sku, supplier=sup, supplier_code=code, name=name, design=design,
            index=D(idx), diameter_mm=dia, coating_tier=tier, photochromic=photo,
            rx_range=sv, base_retail_net=D(retail), base_cost_net=D(cost),
            available_surcharges=surch, rank_score=D(rank), is_dormant=dormant)
    add("HOY-NLX-150-HMC-70", "hoya", "H1101", "Hoya Nulux 1.50 HMC",
        LensDesign.SINGLE_VISION, "1.50", 70, CoatingTier.HMC, False,
        "12500", "5000", ("photochromic", "tint_solid", "prizma"))
    add("HOY-NLX-160-HMC-70", "hoya", "H1201", "Hoya Nulux 1.60 HMC",
        LensDesign.SINGLE_VISION, "1.60", 70, CoatingTier.HMC, False,
        "18000", "7200", ("photochromic", "tint_solid", "prizma"), rank="60")
    add("HOY-NLX-167-PREM-70", "hoya", "H1301", "Hoya Nulux 1.67 Hi-Vision",
        LensDesign.SINGLE_VISION, "1.67", 70, CoatingTier.PREMIUM, False,
        "32000", "13500", ("photochromic", "prizma"))
    add("EYT-ALAP-150-HARD-65", "eyetech", "ET001", "EyeTech Alap 1.50 kemény réteg",
        LensDesign.SINGLE_VISION, "1.50", 65, CoatingTier.HARD, False,
        "6900", "1500", ("tint_solid",))
    add("EYT-KOMF-160-HMC-70", "eyetech", "ET102", "EyeTech Komfort 1.60 HMC",
        LensDesign.SINGLE_VISION, "1.60", 70, CoatingTier.HMC, False,
        "11900", "3100", ("photochromic", "tint_solid", "prizma"), rank="80")
    add("EYT-PREM-167-PREM-70", "eyetech", "ET203", "EyeTech Prémium 1.67 AR",
        LensDesign.SINGLE_VISION, "1.67", 70, CoatingTier.PREMIUM, True,
        "24900", "8200", ("prizma",))
    add("XCE-ULTRA-167-PREM-70", "xcelens", "X900", "Xcelens Ultra 1.67 Premium",
        LensDesign.SINGLE_VISION, "1.67", 70, CoatingTier.PREMIUM, True,
        "42000", "21000", ("prizma",))
    add("HOY-SYNC-160-PREM-70", "hoya", "H2101", "Hoya Sync III 1.60 (office)",
        LensDesign.OFFICE, "1.60", 70, CoatingTier.PREMIUM, False,
        "36500", "16800", ("photochromic",))
    # Ruling 10: dormant SKU — sellable, muted pill in the finder.
    add("HOY-NLX-174-PREM-70", "hoya", "H1401", "Hoya Nulux 1.74 Hi-Vision",
        LensDesign.SINGLE_VISION, "1.74", 70, CoatingTier.PREMIUM, False,
        "55000", "26000", ("prizma",), dormant=True)
    # D5 choice group: sun lens — exactly one mirror color MUST be picked.
    add("EYT-SUN-150-HMC-65", "eyetech", "ET310", "EyeTech Sun 1.50 HMC",
        LensDesign.SINGLE_VISION, "1.50", 65, CoatingTier.HMC, False,
        "9900", "2600", ("mirror_blue", "mirror_gold"))

    surcharges = {
        "photochromic": Surcharge("photochromic", "Fényre sötétedő", D("12000"), D("5000")),
        "tint_solid": Surcharge("tint_solid", "Színezés (egyszínű)", D("3500"), D("900")),
        "prizma": Surcharge("prizma", "Prizma", D("6000"), D("2400")),
        "mirror_blue": Surcharge("mirror_blue", "e-mirror Kék", D("9000"),
                                 D("3000"), choice_group="Tükrös bevonat"),
        "mirror_gold": Surcharge("mirror_gold", "e-mirror Arany", D("9000"),
                                 D("3000"), choice_group="Tükrös bevonat"),
    }
    overrides = (
        PriceOverride(sku="EYT-KOMF-160-HMC-70",
                      option_codes=frozenset({"photochromic"}),
                      retail_net=D("19900"), valid_from="2026-07-01",
                      override_id="AKCIO-EYT-PHOTO-JUL"),
    )
    return CatalogSnapshot(catalog_version="demo-fixture-000000000001",
                           lenses=lenses, surcharges=surcharges,
                           overrides=overrides, vat_rate=D("0.27"))


# --- real-data mode ---------------------------------------------------------
import os


def rows_to_snapshot(rows, version: str) -> CatalogSnapshot:
    """Map CatalogRows (per-power real SKUs) to the pricing model.
    Each SKU gets a degenerate RxRange (exact powers) — the finder resolves a
    prescription straight to orderable SKUs, hard rule 9 by construction."""
    from pricing.models import LensDesign as LD
    design_map = {"spheric": LD.SINGLE_VISION, "aspheric": LD.SINGLE_VISION}
    tier_map = {"HMC": CoatingTier.HMC}
    lenses = {}
    for r in rows:
        lenses[r.sku] = LensProduct(
            sku=r.sku, supplier=r.supplier, supplier_code=r.famcode,
            name=r.name,
            design=design_map.get(r.design, LD.SINGLE_VISION),
            index=D(str(r.refractive_index)),
            diameter_mm=int(r.diameter_mm),
            coating_tier=tier_map.get(r.coating_code, CoatingTier.HMC),
            photochromic=False,
            rx_range=RxRange(D(str(r.sph)), D(str(r.sph)),
                             D(str(min(r.cyl, 0.0))), D(str(max(r.cyl, 0.0)))),
            base_retail_net=D(str(r.retail_net_huf)),
            base_cost_net=D("0"),      # ruling 2026-07-16: no COGS in Szempont
            available_surcharges=(),   # EyeTech PL: no priced options yet
            rank_score=D(str(r.rank_score)),
            is_dormant=bool(r.is_dormant),   # ruling 10: muted pill in UI
        )
    return CatalogSnapshot(catalog_version=version, lenses=lenses,
                           surcharges={}, overrides=(), vat_rate=D("0.27"))


def load_snapshot_live() -> CatalogSnapshot:  # pragma: no cover — needs GCP creds
    """Latest synced catalog from szempont.lens_catalog; falls back to the
    converter view directly if the sync job has not run yet."""
    from google.cloud import bigquery
    from ingest.source import BQEyeTechSource, CatalogRow
    client = bigquery.Client(project=os.environ.get(
        "GCP_PROJECT", "natural-caster-496309-j3"))
    sql = """
    SELECT * FROM `szempont.lens_catalog`
    QUALIFY ROW_NUMBER() OVER (PARTITION BY sku ORDER BY _ingested_at DESC) = 1
    """
    try:
        it = list(client.query(sql, job_config=bigquery.QueryJobConfig(
            labels={"tool": "szempont"})).result())
        if it:
            rows = [CatalogRow(
                sku=r["sku"], supplier=r["supplier"], famcode=r["famcode"],
                name=r["name"], sph=r["sph"], cyl=r["cyl"],
                add_power=r["add_power"], diameter_mm=r["diameter_mm"],
                refractive_index=r["refractive_index"], design=r["design"],
                coating_code=r["coating_code"], blue_filter=r["blue_filter"],
                retail_net_huf=r["retail_net_huf"],
                rank_score=float(r["rank_score"] or 0),
                is_dormant=r["is_dormant"],
            ) for r in it]
            return rows_to_snapshot(rows, it[0]["catalog_version"])
    except Exception:
        pass  # table not created yet -> fall through to the converter view
    rows = BQEyeTechSource(client).fetch()
    return rows_to_snapshot(rows, "pl-live-unversioned")


_MODE = os.environ.get("SZEMPONT_CATALOG", "demo")
if _MODE == "bq":  # pragma: no cover
    _demo_impl = load_snapshot

    @lru_cache(maxsize=1)
    def load_snapshot() -> CatalogSnapshot:  # type: ignore[no-redef]
        return load_snapshot_live()
