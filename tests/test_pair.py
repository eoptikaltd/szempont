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


def choice_group_snapshot():
    """test_pricing snapshot with the Hoya lens carrying a mandatory choice
    group of two mirror colors, gold cheaper than blue."""
    import dataclasses
    from pricing.models import CatalogSnapshot, Surcharge
    from tests.test_pricing import snapshot
    base = snapshot()
    sc = dict(base.surcharges)
    sc["mirror_blue"] = Surcharge("mirror_blue", "e-mirror Kék", D("9000"),
                                  D("3000"), choice_group="sun")
    sc["mirror_gold"] = Surcharge("mirror_gold", "e-mirror Arany", D("8000"),
                                  D("3000"), choice_group="sun")
    lenses = dict(base.lenses)
    lenses["HOY-160-HMC-70"] = dataclasses.replace(
        lenses["HOY-160-HMC-70"],
        available_surcharges=("mirror_blue", "mirror_gold"))
    return CatalogSnapshot(catalog_version="cg", lenses=lenses, surcharges=sc,
                           vat_rate=D("0.27"))


def test_choice_group_family_listed_as_from_price():
    # D5 review fix (2026-07-16): with no group member selected the family
    # still appears, priced by the CHEAPEST member and flagged.
    snap = choice_group_snapshot()
    rx = EyeRx(D("-2"))
    pairs = find_pair_options(snap, rx, rx, quote_date="2026-07-12")
    hoya = next(p for p in pairs if p.right.sku == "HOY-160-HMC-70")
    assert hoya.needs_configuration is True
    assert hoya.representative_codes == frozenset({"mirror_gold"})  # cheapest
    assert hoya.pair_retail_net == D("52000")          # 2 x (18000 + 8000)
    others = [p for p in pairs if p.right.sku != "HOY-160-HMC-70"]
    assert others and all(not p.needs_configuration for p in others)


def test_choice_group_family_priced_exactly_when_member_selected():
    snap = choice_group_snapshot()
    rx = EyeRx(D("-2"))
    picked = find_pair_options(snap, rx, rx, quote_date="2026-07-12",
                               option_codes=frozenset({"mirror_blue"}))
    assert [p.right.sku for p in picked] == ["HOY-160-HMC-70"]
    assert picked[0].needs_configuration is False
    assert picked[0].representative_codes == frozenset()
    assert picked[0].pair_retail_net == D("54000")     # 2 x (18000 + 9000)


def test_search_lists_choice_group_family_as_from_price():
    from pricing.models import SearchQuery
    from pricing.search import search
    snap = choice_group_snapshot()
    results = search(snap, SearchQuery(sph=D("-2")), quote_date="2026-07-12")
    hoya = next(r for r in results if r.lens.sku == "HOY-160-HMC-70")
    assert hoya.needs_configuration is True
    assert hoya.quote.unit_retail_net == D("26000")    # 18000 + cheapest 8000
    assert all(not r.needs_configuration for r in results
               if r.lens.sku != "HOY-160-HMC-70")
