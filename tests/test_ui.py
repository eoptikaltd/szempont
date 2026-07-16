"""UI route tests — pair-first finder + pair quote."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.app import app


def c():
    return app.test_client()


def test_finder_pair_results_render():
    r = c().get("/?od_sph=-2&od_cyl=0&os_sph=-1.5&os_cyl=0")
    assert r.status_code == 200
    b = r.data.decode()
    assert "OD" in b and "OS" in b and "tnum" in b


def test_pair_quote_two_skus():
    r = c().get("/quote?sku_r=HOY-NLX-160-HMC-70&sku_l=HOY-NLX-150-HMC-70")
    assert r.status_code == 200
    b = r.data.decode()
    assert "HOY-NLX-160-HMC-70" in b and "HOY-NLX-150-HMC-70" in b


def test_quote_single_sku_backcompat_and_404():
    assert c().get("/quote?sku=HOY-NLX-160-HMC-70").status_code == 200
    assert c().get("/quote?sku_r=NOPE").status_code == 404


# ---------------------------------------------------------- W2 item 2 additions
def test_finder_dormant_pill_and_choice_group_chips():
    b = c().get("/?od_sph=-2&os_sph=-2").data.decode()
    assert "HOY-NLX-174-PREM-70" in b        # dormant family still offered...
    assert "alvó SKU" in b                   # ...with the muted pill (ruling 10)
    assert "Tükrös bevonat" in b and 'name="cg_0"' in b  # D5 chips render
    # review fix: unconfigured sun lens listed as a flagged from-price
    assert "EYT-SUN-150-HMC-65" in b
    assert "ártól — opció választandó" in b
    assert "opt=mirror_blue" in b            # rep pick carried into quote link


def test_finder_choice_group_selection_prices_sun_lens():
    b = c().get("/?od_sph=-2&os_sph=-2&cg_0=mirror_blue").data.decode()
    assert "EYT-SUN-150-HMC-65" in b
    assert "ártól — opció választandó" not in b   # configured -> exact price
    # 2 x (9900 + 9000) = 37800 net -> 48006 gross
    assert "48 006" in b


def test_quote_auto_munkadij_and_frame_line():
    b = c().get("/quote?sku_r=HOY-NLX-160-HMC-70&sku_l=HOY-NLX-150-HMC-70"
                "&frame=FRM-RB-5228").data.decode()
    assert "Szemüvegkészítés munkadíj" in b and "automatikus" in b
    assert "Ray-Ban RB5228 fekete keret" in b
    # 18000 + 12500 + 39000 + 4500 = 74000 net -> 93980 gross
    assert "93 980 Ft" in b


def test_quote_frame_search_lists_unas_hits():
    b = c().get("/quote?sku=HOY-NLX-160-HMC-70&qf=konnyu").data.decode()
    assert "FRM-EO-KONNYU-02" in b and "Hozzáadás" in b


def test_quote_curated_discount_applied_and_gated():
    # basket 2x18000 + 4500 = 40500; Törzs 10% = 4050 -> net 36450 -> gross 46292
    b = c().get("/quote?sku=HOY-NLX-160-HMC-70&discount=TORZS10").data.decode()
    assert "Törzsvásárlói 10%" in b
    assert "4 050 Ft" in b and "46 292 Ft" in b
    gated = c().get("/quote?sku=HOY-NLX-160-HMC-70&discount=DOLG25").data.decode()
    assert "Jóváhagyta" in gated             # approval noted on-page (M5: real gate)
    unknown = c().get("/quote?sku=HOY-NLX-160-HMC-70&discount=NOPE").data.decode()
    assert "ismeretlen kedvezmény" in unknown


def test_auto_approved_gated_discount_audited_on_apply_never_on_render():
    # Review rulings (2026-07-16): pre-M5 auto-approvals audited with marker,
    # exactly ONE event per applied discount — POST/apply path only, GET
    # renders never write audit.
    from app.app import AUDIT_EVENTS, current_operator
    AUDIT_EVENTS.clear()
    r = c().post("/quote/discount", data={
        "sku_r": "HOY-NLX-160-HMC-70", "discount": "DOLG25"})
    assert r.status_code == 302 and "discount=DOLG25" in r.headers["Location"]
    assert len(AUDIT_EVENTS) == 1
    ev = AUDIT_EVENTS[0]
    assert ev["event_type"] == "discount"
    assert ev["actor"] == current_operator()   # no literal operator names
    assert '"marker": "auto_approved_pre_m5"' in ev["payload"]
    assert '"discount_config_id": "DOLG25"' in ev["payload"]
    # repeated renders of the applied discount: still exactly one event
    for _ in range(3):
        assert c().get("/quote?sku=HOY-NLX-160-HMC-70"
                       "&discount=DOLG25").status_code == 200
    assert len(AUDIT_EVENTS) == 1
    AUDIT_EVENTS.clear()
    c().post("/quote/discount", data={
        "sku_r": "HOY-NLX-160-HMC-70", "discount": "TORZS10"})  # not gated
    c().get("/quote?sku=HOY-NLX-160-HMC-70&discount=TORZS10")
    assert AUDIT_EVENTS == []
