"""Pair (OD/OS) finding tests — real-shaped EyeTech per-power SKUs."""

from decimal import Decimal as D

from ingest.source import CatalogRow
from app.catalog import rows_to_snapshot
from pricing.pair import EyeRx, find_pair_options


def row(sku, sph, cyl, price, fam="ETBIS", dia=72.0, idx=1.56, blue=False):
    return CatalogRow(sku=sku, supplier="eyetech", famcode=fam,
                      name=f"EyeTech Biolar, S{idx}, SV, SPH: {sph:+.2f}, CYL: {cyl:.2f}, DIA: {int(dia)}, SHMC",
                      sph=sph, cyl=cyl, add_power=0.0, diameter_mm=dia,
                      refractive_index=idx, design="spheric",
                      coating_code="HMC", blue_filter=blue,
                      retail_net_huf=price, rank_score=0.0,
                      is_dormant=False)


ROWS = [
    # ETBIS family, dia 72: covers OD -2.00/-0.50 and OS -1.75/0.00
    row("ETBIS-R", -2.0, -0.5, 3543.0),
    row("ETBIS-L", -1.75, 0.0, 3543.0),
    # ETBLS family (blue): only OD power exists -> must NOT appear
    row("ETBLS-R", -2.0, -0.5, 5906.0, fam="ETBLS", blue=True),
    # ETBIA 1.67 family: both powers exist, pricier
    row("ETBIA-R", -2.0, -0.5, 6299.0, fam="ETBIA", idx=1.67, dia=75.0),
    row("ETBIA-L", -1.75, 0.0, 6299.0, fam="ETBIA", idx=1.67, dia=75.0),
]


def test_pair_requires_both_eyes_in_same_family():
    snap = rows_to_snapshot(ROWS, "t")
    pairs = find_pair_options(snap, EyeRx(D("-2"), D("-0.5")),
                              EyeRx(D("-1.75")), quote_date="2026-07-12")
    fams = {p.right.supplier_code for p in pairs}
    assert fams == {"ETBIS", "ETBIA"}          # ETBLS excluded: no left SKU
    for p in pairs:
        assert p.right.sku != p.left.sku


def test_pair_pricing_sums_two_skus_and_orders_cheapest_first():
    snap = rows_to_snapshot(ROWS, "t")
    pairs = find_pair_options(snap, EyeRx(D("-2"), D("-0.5")),
                              EyeRx(D("-1.75")), quote_date="2026-07-12")
    assert pairs[0].right.supplier_code == "ETBIS"   # rank 0 -> price asc
    etbia = next(p for p in pairs if p.right.supplier_code == "ETBIA")
    assert etbia.pair_retail_net == D("12598")       # 6299 * 2
    assert etbia.pair_retail_gross == D("16000")     # 2 x round(6299*1.27)
    prices = [p.pair_retail_net for p in pairs]
    assert prices == sorted(prices)


def test_identical_rx_both_eyes_uses_same_sku_twice():
    snap = rows_to_snapshot(ROWS, "t")
    pairs = find_pair_options(snap, EyeRx(D("-2"), D("-0.5")),
                              EyeRx(D("-2"), D("-0.5")), quote_date="2026-07-12")
    p = next(x for x in pairs if x.right.supplier_code == "ETBIS")
    assert p.right.sku == p.left.sku == "ETBIS-R"
    assert p.pair_retail_net == D("7086")
