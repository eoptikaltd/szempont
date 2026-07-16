from decimal import Decimal as D

from pricing.thickness import compare_indices, estimate_thickness


def test_minus_lens_edge_decreases_with_index():
    res = compare_indices(D("-6.00"), D("0"), D("50"))
    edges = [r.edge_mm for r in res]
    assert edges == sorted(edges, reverse=True)      # 1.50 thickest → 1.74 thinnest
    assert res[0].edge_mm > D("4")                   # -6.00 in CR-39 is chunky
    assert res[-1].edge_mm < res[0].edge_mm * D("0.80")


def test_plus_lens_center_drives():
    r = estimate_thickness(D("+4.00"), D("0"), D("1.50"), D("50"))
    assert r.center_mm > r.edge_mm


def test_cyl_worst_meridian_counts():
    no_cyl = estimate_thickness(D("-4.00"), D("0"), D("1.60"), D("50"))
    with_cyl = estimate_thickness(D("-4.00"), D("-2.00"), D("1.60"), D("50"))
    assert with_cyl.edge_mm > no_cyl.edge_mm


def test_smaller_frame_beats_index_upgrade_sometimes():
    big_hi = estimate_thickness(D("-5.00"), D("0"), D("1.67"), D("56"))
    small_lo = estimate_thickness(D("-5.00"), D("0"), D("1.60"), D("46"))
    assert small_lo.edge_mm <= big_hi.edge_mm        # the honest-advice case
