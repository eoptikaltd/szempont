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


# ------------------------------------------------------------ W2 item 4 (M2C)
def test_konzultacio_basket_always_visible_with_tier_and_frame():
    b = c().get("/konzultacio?od_sph=-2&os_sph=-2").data.decode()
    assert "Az Ön kosara" in b
    assert "Szemüvegkészítés munkadíj" in b     # basket through the record path
    assert "Ezt nézzük meg" in b                # tier select links
    with_frame = c().get("/konzultacio?od_sph=-2&os_sph=-2&tier=Alap"
                         "&frame=FRM-EO-CLASS-01").data.decode()
    assert "eOptika Classic 01 acél keret" in with_frame
    assert "a kosárban" in with_frame           # Alap marked selected
    # Alap tier = EYT-ALAP 6900/eye: 2x6900 + 14900 frame + 4500 munkadíj
    # = 33200 net -> 42164 gross
    assert "42 164 Ft" in with_frame


def test_konzultacio_tint_swatches_from_szin_catalog():
    b = c().get("/konzultacio?od_sph=-2&os_sph=-2").data.decode()
    assert "Színminták a Szín katalógusból" in b and "Barna" in b
    tinted = c().get("/konzultacio?od_sph=-2&os_sph=-2&tint=Barna").data.decode()
    assert "Színezés (egyszínű)" in tinted      # tint option lands in basket
    # snapshot without tint surcharges -> section hidden (live-catalog guard)
    from app.catalog import tint_swatches
    from tests.test_pricing import snapshot
    import dataclasses
    snap = snapshot()
    bare = dataclasses.replace(snap, surcharges={})
    assert tint_swatches(bare) == {}


def test_print_munkalap_wires_data_and_real_barcodes():
    b = c().get("/print/munkalap?sku_r=HOY-NLX-160-HMC-70"
                "&sku_l=HOY-NLX-150-HMC-70&od_sph=0.75&od_cyl=-0.25&od_ax=100"
                "&frame=FRM-RB-5228&person=P-1001&order=SO-1604869D"
                "&due=2026-07-18").data.decode()
    assert "Hoya Nulux 1.60 HMC" in b and "Hoya Nulux 1.50 HMC" in b
    assert "+0,75" in b and "−0,25" in b and "100°" in b
    assert "Kovács Éva" in b and "SO-1604869D" in b
    assert "07. 18." in b and "szombat" in b
    assert b.count("<svg") >= 4                 # order + frame + 2 lens codes
    from app.barcodes import ean13_fullcode
    assert ean13_fullcode("599811241152") in b  # frame EAN-13, true check digit
    body = b.split("</style>")[1]
    assert 'class="ean"' not in body            # CSS placeholder stripes gone
    assert 'class="sobar"' not in body
    assert c().get("/print/munkalap?sku_r=NOPE").status_code == 404


def test_print_latasvizsgalat_pass_through_only():
    # values render when passed, nothing stored, blank otherwise
    b = c().get("/print/latasvizsgalat?name=Kovács Éva&ar_j_sph=−6.75"
                "&pd_j=29.5").data.decode()
    assert "Kovács Éva" in b and "−6.75" in b and "29.5" in b
    blank = c().get("/print/latasvizsgalat").data.decode()
    assert "Minta Anna" not in blank            # no demo leakage
    demo = c().get("/print/latasvizsgalat?demo=1").data.decode()
    assert "Minta Anna" in demo and "JJ OATP" in demo
    prefilled = c().get("/print/latasvizsgalat?person=P-1001").data.decode()
    assert "Kovács Éva" in prefilled and "P-1001" in prefilled


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
