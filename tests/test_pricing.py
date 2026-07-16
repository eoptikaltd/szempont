"""M2 pricing engine tests — includes the quote-reproducibility acceptance
test (same catalog_version reprices identically) and Hungarian-diacritics
handling (hard rule 10)."""

from decimal import Decimal as D

import pytest

from pricing.engine import PricingError, price_quote
from pricing.models import (
    CatalogSnapshot, CoatingTier, LensDesign, LensProduct, PriceOverride,
    QuoteRequest, RxRange, SearchQuery, Surcharge,
)
from pricing.search import search


def snapshot(version="hoya-abc123def456", overrides=(), vat=D("0.27")):
    lenses = {
        "HOY-160-HMC-70": LensProduct(
            sku="HOY-160-HMC-70", supplier="hoya", supplier_code="H1234",
            name="Hoya Nulux 1.60 HMC", design=LensDesign.SINGLE_VISION,
            index=D("1.60"), diameter_mm=70, coating_tier=CoatingTier.HMC,
            photochromic=False,
            rx_range=RxRange(D("-8"), D("4"), D("0"), D("4")),
            base_retail_net=D("18000"), base_cost_net=D("7200"),
            available_surcharges=("photochromic", "tint_solid", "prizma"),
        ),
        "EYT-150-HARD-65": LensProduct(
            sku="EYT-150-HARD-65", supplier="eyetech", supplier_code="ET001",
            name="EyeTech Alap 1.50 kemény réteg",  # diacritics on purpose
            design=LensDesign.SINGLE_VISION,
            index=D("1.50"), diameter_mm=65, coating_tier=CoatingTier.HARD,
            photochromic=False,
            rx_range=RxRange(D("-6"), D("6"), D("0"), D("2")),
            base_retail_net=D("6900"), base_cost_net=D("1500"),
            available_surcharges=("tint_solid",),
        ),
        "XCE-167-PREM-70": LensProduct(
            sku="XCE-167-PREM-70", supplier="xcelens", supplier_code="X900",
            name="Xcelens Ultra 1.67 Premium AR", design=LensDesign.SINGLE_VISION,
            index=D("1.67"), diameter_mm=70, coating_tier=CoatingTier.PREMIUM,
            photochromic=True,
            rx_range=RxRange(D("-12"), D("8"), D("0"), D("6")),
            base_retail_net=D("42000"), base_cost_net=D("21000"),
            available_surcharges=("prizma",),
        ),
    }
    surcharges = {
        "photochromic": Surcharge("photochromic", "Fényre sötétedő",
                                  D("12000"), D("5000")),
        "tint_solid": Surcharge("tint_solid", "Színezés (egyszínű)",
                                D("3500"), D("900")),
        "prizma": Surcharge("prizma", "Prizma", D("6000"), D("2400")),
    }
    return CatalogSnapshot(
        catalog_version=version, lenses=lenses, surcharges=surcharges,
        overrides=tuple(overrides), vat_rate=vat,
    )


# ---------------------------------------------------------------- base math
def test_base_price_pair_with_vat():
    q = price_quote(snapshot(), QuoteRequest(
        sku="HOY-160-HMC-70", quote_date="2026-07-12"))
    assert q.quantity == 2
    assert q.unit_retail_net == D("18000")
    assert q.total_retail_net == D("36000")
    assert q.total_retail_gross == D("45720")           # 36000 * 1.27
    assert q.total_vat == D("9720")
    assert q.margin_net == D("36000") - D("14400")


def test_surcharges_add_to_retail_and_cost():
    q = price_quote(snapshot(), QuoteRequest(
        sku="HOY-160-HMC-70",
        option_codes=frozenset({"photochromic", "tint_solid"}),
        quote_date="2026-07-12", quantity=2))
    assert q.unit_retail_net == D("18000") + D("12000") + D("3500")
    assert q.unit_cost_net == D("7200") + D("5000") + D("900")
    assert [l.code for l in q.lines] == ["base", "photochromic", "tint_solid"]


def test_vat_rounds_to_whole_huf_half_up():
    # net 333 * 1.27 = 422.91 -> 423
    snap = snapshot()
    lens = snap.lenses["HOY-160-HMC-70"]
    odd = CatalogSnapshot(
        catalog_version="v", vat_rate=D("0.27"),
        lenses={"S": LensProduct(
            sku="S", supplier="x", supplier_code="x", name="x",
            design=LensDesign.SINGLE_VISION, index=D("1.5"), diameter_mm=65,
            coating_tier=CoatingTier.NONE, photochromic=False,
            rx_range=lens.rx_range,
            base_retail_net=D("333"), base_cost_net=D("100"))},
        surcharges={},
    )
    q = price_quote(odd, QuoteRequest(sku="S", quote_date="2026-07-12",
                                      quantity=1))
    assert q.total_retail_gross == D("423")


# ----------------------------------------------------------------- overrides
def override(retail, valid_from, valid_to=None, oid="OV1",
             opts=frozenset({"photochromic"})):
    return PriceOverride(sku="HOY-160-HMC-70", option_codes=opts,
                         retail_net=D(retail), valid_from=valid_from,
                         valid_to=valid_to, override_id=oid)


def test_override_wins_over_list_price_for_exact_combo():
    snap = snapshot(overrides=[override("25000", "2026-07-01")])
    q = price_quote(snap, QuoteRequest(
        sku="HOY-160-HMC-70", option_codes=frozenset({"photochromic"}),
        quote_date="2026-07-12"))
    assert q.override_applied == "OV1"
    assert q.unit_retail_net == D("25000")               # not 30000 list
    assert q.unit_cost_net == D("12200")                 # cost NOT overridden


def test_override_does_not_leak_to_other_combos():
    snap = snapshot(overrides=[override("25000", "2026-07-01")])
    q = price_quote(snap, QuoteRequest(                  # no options
        sku="HOY-160-HMC-70", quote_date="2026-07-12"))
    assert q.override_applied is None
    assert q.unit_retail_net == D("18000")


def test_override_effective_dating():
    snap = snapshot(overrides=[override("25000", "2026-07-01", "2026-07-10")])
    active = price_quote(snap, QuoteRequest(
        sku="HOY-160-HMC-70", option_codes=frozenset({"photochromic"}),
        quote_date="2026-07-10"))
    expired = price_quote(snap, QuoteRequest(
        sku="HOY-160-HMC-70", option_codes=frozenset({"photochromic"}),
        quote_date="2026-07-11"))
    assert active.override_applied == "OV1"
    assert expired.override_applied is None


def test_most_recent_active_override_wins():
    snap = snapshot(overrides=[
        override("25000", "2026-06-01", oid="OLD"),
        override("23000", "2026-07-01", oid="NEW"),
    ])
    q = price_quote(snap, QuoteRequest(
        sku="HOY-160-HMC-70", option_codes=frozenset({"photochromic"}),
        quote_date="2026-07-12"))
    assert q.override_applied == "NEW"
    assert q.unit_retail_net == D("23000")


# ------------------------------------------------------------ reproducibility
def test_quote_reproducibility_same_catalog_version():
    """Acceptance criterion: repricing on an old catalog_version yields an
    identical Quote, field for field."""
    req = QuoteRequest(sku="HOY-160-HMC-70",
                       option_codes=frozenset({"tint_solid", "photochromic"}),
                       quote_date="2026-07-12")
    q1 = price_quote(snapshot(overrides=[override("25000", "2026-07-01",
                                                  opts=frozenset())]), req)
    q2 = price_quote(snapshot(overrides=[override("25000", "2026-07-01",
                                                  opts=frozenset())]), req)
    assert q1 == q2  # frozen dataclasses: full structural equality


def test_new_catalog_version_can_differ_but_old_stays_stable():
    old = snapshot(version="hoya-old")
    new_lenses = dict(old.lenses)
    import dataclasses
    lp = new_lenses["HOY-160-HMC-70"]
    new_lenses["HOY-160-HMC-70"] = dataclasses.replace(
        lp, base_retail_net=D("19500"))
    new = CatalogSnapshot(catalog_version="hoya-new", lenses=new_lenses,
                          surcharges=old.surcharges, vat_rate=old.vat_rate)
    req = QuoteRequest(sku="HOY-160-HMC-70", quote_date="2026-07-12")
    assert price_quote(old, req).unit_retail_net == D("18000")
    assert price_quote(new, req).unit_retail_net == D("19500")
    assert price_quote(old, req) == price_quote(old, req)


# -------------------------------------------------------------------- errors
def test_unknown_sku_and_invalid_option():
    with pytest.raises(PricingError):
        price_quote(snapshot(), QuoteRequest(sku="NOPE",
                                             quote_date="2026-07-12"))
    with pytest.raises(PricingError):
        price_quote(snapshot(), QuoteRequest(
            sku="EYT-150-HARD-65", option_codes=frozenset({"prizma"}),
            quote_date="2026-07-12"))
    with pytest.raises(PricingError):
        price_quote(snapshot(), QuoteRequest(sku="HOY-160-HMC-70",
                                             quote_date=""))


# ------------------------------------------------------------------ encoding
def test_hungarian_diacritics_survive_quote_lines():
    q = price_quote(snapshot(), QuoteRequest(
        sku="EYT-150-HARD-65", option_codes=frozenset({"tint_solid"}),
        quote_date="2026-07-12"))
    names = " ".join(l.name for l in q.lines)
    assert "kemény réteg" in names
    assert "Színezés" in names


# -------------------------------------------------------------------- search
def test_parametric_search_rank_then_price_ordered():
    results = search(snapshot(), SearchQuery(sph=D("-4"), cyl=D("1")),
                     quote_date="2026-07-12")
    skus = [r.lens.sku for r in results]
    assert set(skus) == {"HOY-160-HMC-70", "EYT-150-HARD-65",
                         "XCE-167-PREM-70"}
    # all rank 0 in this fixture -> retail ascending, sku tiebreak
    prices = [r.quote.total_retail_net for r in results]
    assert prices == sorted(prices)


def test_search_filters_rx_envelope_and_attributes():
    # sph -10 excludes Hoya (-8 min) and EyeTech (-6 min)
    r = search(snapshot(), SearchQuery(sph=D("-10")), quote_date="2026-07-12")
    assert [x.lens.sku for x in r] == ["XCE-167-PREM-70"]

    r = search(snapshot(), SearchQuery(sph=D("-2"),
                                       coating_tier=CoatingTier.HMC),
               quote_date="2026-07-12")
    assert [x.lens.sku for x in r] == ["HOY-160-HMC-70"]

    r = search(snapshot(), SearchQuery(sph=D("-2"), index_min=D("1.60")),
               quote_date="2026-07-12")
    assert {x.lens.sku for x in r} == {"HOY-160-HMC-70", "XCE-167-PREM-70"}


def test_search_skips_lenses_that_cannot_take_requested_options():
    r = search(snapshot(), SearchQuery(sph=D("-2")), quote_date="2026-07-12",
               option_codes=frozenset({"photochromic"}))
    assert [x.lens.sku for x in r] == ["HOY-160-HMC-70"]


# ---------------------------------------------------------- choice groups (D5)
def test_choice_group_requires_exactly_one():
    snap = snapshot()
    cg = dict(snap.surcharges)
    cg["mirror_blue"] = Surcharge("mirror_blue", "e-mirror Kék", D("9000"),
                                  D("3000"), choice_group="sun_coat")
    cg["mirror_gold"] = Surcharge("mirror_gold", "e-mirror Arany", D("9000"),
                                  D("3000"), choice_group="sun_coat")
    lenses = dict(snap.lenses)
    import dataclasses
    lenses["HOY-160-HMC-70"] = dataclasses.replace(
        lenses["HOY-160-HMC-70"],
        available_surcharges=("mirror_blue", "mirror_gold", "tint_solid"))
    snap2 = CatalogSnapshot(catalog_version="cg", lenses=lenses, surcharges=cg,
                            vat_rate=D("0.27"))
    # none picked -> error
    with pytest.raises(PricingError):
        price_quote(snap2, QuoteRequest(sku="HOY-160-HMC-70",
                                        quote_date="2026-07-12"))
    # two picked -> error
    with pytest.raises(PricingError):
        price_quote(snap2, QuoteRequest(
            sku="HOY-160-HMC-70",
            option_codes=frozenset({"mirror_blue", "mirror_gold"}),
            quote_date="2026-07-12"))
    # exactly one -> priced, and free optional still combinable
    q = price_quote(snap2, QuoteRequest(
        sku="HOY-160-HMC-70",
        option_codes=frozenset({"mirror_gold", "tint_solid"}),
        quote_date="2026-07-12"))
    assert q.unit_retail_net == D("18000") + D("9000") + D("3500")
