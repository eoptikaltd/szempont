"""Pair (OD/OS) finding tests — real-shaped EyeTech per-power SKUs."""

from decimal import Decimal as D

from ingest.source import CatalogRow
from app.catalog import rows_to_snapshot
from pricing.pair import EyeRx, find_pair_options


def row(sku, sph, cyl, price, fam="ETBIS", dia=72.0, idx=1.56, blue=False,
        dormant=False):
    return CatalogRow(sku=sku, supplier="eyetech", famcode=fam,
                      name=f"EyeTech Biolar, S{idx}, SV, SPH: {sph:+.2f}, CYL: {cyl:.2f}, DIA: {int(dia)}, SHMC",
                      sph=sph, cyl=cyl, add_power=0.0, diameter_mm=dia,
                      refractive_index=idx, design="spheric",
                      coating_code="HMC", blue_filter=blue,
                      retail_net_huf=price, rank_score=0.0,
                      is_dormant=dormant)


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


def test_dormant_flags_propagate_per_eye():
    # Ruling 10: dormant SKUs stay sellable; the UI needs per-eye flags.
    rows = [row("ETBIS-R", -2.0, -0.5, 3543.0, dormant=True),
            row("ETBIS-L", -1.75, 0.0, 3543.0)]
    snap = rows_to_snapshot(rows, "t")
    p, = find_pair_options(snap, EyeRx(D("-2"), D("-0.5")),
                           EyeRx(D("-1.75")), quote_date="2026-07-12")
    assert p.right_dormant is True and p.left_dormant is False


def test_family_with_unsatisfied_choice_group_is_skipped_not_crashed():
    # D5: a family whose mandatory choice group has no selection cannot be
    # priced — the pair finder must skip it, not raise.
    import dataclasses
    from pricing.models import CatalogSnapshot, Surcharge
    from tests.test_pricing import snapshot
    base = snapshot()
    sc = dict(base.surcharges)
    sc["mirror_blue"] = Surcharge("mirror_blue", "e-mirror Kék", D("9000"),
                                  D("3000"), choice_group="sun")
    sc["mirror_gold"] = Surcharge("mirror_gold", "e-mirror Arany", D("9000"),
                                  D("3000"), choice_group="sun")
    lenses = dict(base.lenses)
    lenses["HOY-160-HMC-70"] = dataclasses.replace(
        lenses["HOY-160-HMC-70"],
        available_surcharges=("mirror_blue", "mirror_gold"))
    snap = CatalogSnapshot(catalog_version="cg", lenses=lenses, surcharges=sc,
                           vat_rate=D("0.27"))
    rx = EyeRx(D("-2"))
    no_pick = find_pair_options(snap, rx, rx, quote_date="2026-07-12")
    assert no_pick and not any(
        p.right.sku == "HOY-160-HMC-70" for p in no_pick)
    picked = find_pair_options(snap, rx, rx, quote_date="2026-07-12",
                               option_codes=frozenset({"mirror_blue"}))
    assert [p.right.sku for p in picked] == ["HOY-160-HMC-70"]
    assert picked[0].pair_retail_net == D("54000")     # 2 x (18000 + 9000)
