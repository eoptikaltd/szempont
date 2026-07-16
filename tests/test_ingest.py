"""M1 rev-2 tests: catalog sync from a CatalogSource, using rows shaped
exactly like sf6_catalog_converter.pl_items_enriched (verified live 2026-07-12),
including the '|0000' zero-power SKU grammar and Hungarian names."""

import datetime as dt

from ingest.job import build_health_report, compute_catalog_version, run_sync
from ingest.source import CatalogRow, InMemorySource


def row(sku, sph, cyl, price, fam="ETBIS", dormant=False, dia=72.0, idx=1.56,
        blue=False):
    return CatalogRow(
        sku=sku, supplier="eyetech", famcode=fam,
        name=f"EyeTech Biolar, SPH: {sph:+.2f}, CYL: {cyl:.2f}, SHMC",
        sph=sph, cyl=cyl, add_power=0.0, diameter_mm=dia,
        refractive_index=idx, design="spheric", coating_code="HMC",
        blue_filter=blue, retail_net_huf=price, rank_score=0.0,
        is_dormant=dormant)


REAL_SHAPED = [
    row("ETLARS156SV-0200|000072SHMC", -2.0, 0.0, 3543.0),
    row("ETLARS156SV-0200-005072SHMC", -2.0, -0.5, 3543.0),
    row("ETSHIS156SV+0025-002572SHMC", 0.25, -0.25, 5906.0, fam="ETBLS",
        blue=True, dormant=True),
]


class FakeBQ:
    def __init__(self, previous=None):
        self.store = {}
        self._prev = previous or {}
        self.labels = []

    def delete_version(self, table, version):
        self.store.setdefault(table, {}).pop(version, None)

    def load_rows(self, table, rows, labels=None):
        self.labels.append(labels)
        self.store.setdefault(table, {})[rows[0]["catalog_version"]] = rows

    def fetch_prices(self, supplier, exclude_version):
        return self._prev


def test_version_is_content_addressed_and_order_independent():
    v1 = compute_catalog_version("eyetech", REAL_SHAPED)
    v2 = compute_catalog_version("eyetech", list(reversed(REAL_SHAPED)))
    v3 = compute_catalog_version("eyetech", REAL_SHAPED[:2])
    assert v1 == v2 != v3 and v1.startswith("eyetech-")


def test_sync_is_idempotent_and_labeled():
    bq = FakeBQ()
    now = dt.datetime(2026, 7, 12, 12, 0, tzinfo=dt.timezone.utc)
    r1 = run_sync(InMemorySource(REAL_SHAPED), "eyetech", bq, now=now)
    state = {t: dict(v) for t, v in bq.store.items()}
    r2 = run_sync(InMemorySource(REAL_SHAPED), "eyetech", bq, now=now)
    assert r1.catalog_version == r2.catalog_version
    assert bq.store == state
    assert all(l == {"tool": "szempont"} for l in bq.labels)
    loaded = bq.store["szempont.lens_catalog"][r1.catalog_version]
    assert len(loaded) == 3
    assert loaded[0]["catalog_version"] == r1.catalog_version
    assert "SHMC" in loaded[0]["name"]


def test_health_report_grammar_dormant_and_deltas():
    prev = {"ETLARS156SV-0200|000072SHMC": 3400.0,        # price change
            "ETLARS156SV-0999|000072SHMC": 3543.0}        # removed
    rep = build_health_report("eyetech-x", "eyetech", REAL_SHAPED, prev)
    assert rep["row_count"] == 3
    assert rep["rows_by_family"] == {"ETBIS": 2, "ETBLS": 1}
    assert rep["zero_power_pipe_skus"] == 1
    assert rep["dormant_count"] == 1
    assert rep["warning_count"] == 0        # pipe grammar is known, not a warning
    changes = {d["sku"]: d["change"] for d in rep["price_deltas"]}
    assert changes == {
        "ETLARS156SV-0200|000072SHMC": "price",
        "ETLARS156SV-0999|000072SHMC": "removed",
        "ETLARS156SV-0200-005072SHMC": "added",
        "ETSHIS156SV+0025-002572SHMC": "added",
    }


def test_bad_price_and_bad_charset_warned():
    rows = [row("ETLARS156SV-0100-005072SHMC", -1.0, -0.5, 0.0),
            row("BAD SKU WITH SPACES", -1.0, 0.0, 3543.0)]
    rep = build_health_report("v", "eyetech", rows, None)
    assert rep["warning_count"] == 2


def test_rows_to_snapshot_prices_real_sku_through_engine():
    import datetime as dt
    from app.catalog import rows_to_snapshot
    from pricing.engine import price_quote
    from pricing.models import QuoteRequest, SearchQuery
    from pricing.search import search
    from decimal import Decimal as D

    snap = rows_to_snapshot(REAL_SHAPED, "eyetech-test")
    q = price_quote(snap, QuoteRequest(sku="ETLARS156SV-0200-005072SHMC",
                                       quote_date="2026-07-12", quantity=2))
    assert q.total_retail_net == D("7086")          # 3543 * 2
    assert q.total_retail_gross == D("8999")        # * 1.27 rounded

    # exact-power resolution: sph -2.00 / cyl -0.50 -> exactly one SKU
    res = search(snap, SearchQuery(sph=D("-2"), cyl=D("-0.5")),
                 quote_date="2026-07-12")
    assert [r.lens.sku for r in res] == ["ETLARS156SV-0200-005072SHMC"]
