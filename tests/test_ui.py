"""UI route tests — pair-first finder + pair quote."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.app import app


def c():
    return app.test_client()


def test_finder_pair_results_render():
    r = c().get("/lencsekereso?od_sph=-2&od_cyl=0&os_sph=-1.5&os_cyl=0")
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
    b = c().get("/lencsekereso?od_sph=-2&os_sph=-2").data.decode()
    assert "HOY-NLX-174-PREM-70" in b        # dormant family still offered...
    assert "alvó SKU" in b                   # ...with the muted pill (ruling 10)
    assert "Tükrös bevonat" in b and 'name="cg_0"' in b  # D5 chips render
    # review fix: unconfigured sun lens listed as a flagged from-price
    assert "EYT-SUN-150-HMC-65" in b
    assert "ártól — opció választandó" in b
    assert "opt=mirror_blue" in b            # rep pick carried into quote link


def test_finder_choice_group_selection_prices_sun_lens():
    b = c().get("/lencsekereso?od_sph=-2&os_sph=-2&cg_0=mirror_blue").data.decode()
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


# --------------------------------------------------- wave-close review (item 5)
def _ftok(path):
    """Fetch a page and pull the one-time form token out of it."""
    import re
    body = c().get(path).data.decode()
    return re.search(r'name="ftok" value="([0-9a-f]+)"', body).group(1)


def test_cross_site_post_rejected_same_origin_allowed():
    # F-W2-02: IAP authenticates the browser but does NOT stop CSRF.
    data = {"sku_r": "HOY-NLX-160-HMC-70", "discount": "TORZS10"}
    evil = c().post("/quote/discount", data=data,
                    headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    evil2 = c().post("/ugyfel/walkin", data={"name": "X"},
                     headers={"Sec-Fetch-Site": "cross-site"})
    assert evil2.status_code == 403
    ok = c().post("/quote/discount", data=data,
                  headers={"Origin": "http://localhost"})
    assert ok.status_code == 302
    assert c().post("/quote/discount", data=data).status_code == 302  # no hdr


def test_walkin_double_submit_replays_first_z1():
    # F-W2-07: double click / retry must not mint a second Z1 person.
    from urllib.parse import parse_qs, urlparse
    tok = _ftok("/ugyfel")
    data = {"ftok": tok, "name": "Dupla Dénes"}
    first = c().post("/ugyfel/walkin", data=data)
    second = c().post("/ugyfel/walkin", data=data)
    z1 = parse_qs(urlparse(first.headers["Location"]).query)["person"][0]
    z2 = parse_qs(urlparse(second.headers["Location"]).query)["person"][0]
    assert z1 == z2 and z1.startswith("Z1-")
    from app.app import WALKINS
    assert sum(1 for w in WALKINS._walkins.values()
               if w.display_name == "Dupla Dénes") == 1


def test_gated_discount_double_post_emits_one_audit_event():
    from app.app import AUDIT_EVENTS
    AUDIT_EVENTS.clear()
    tok = _ftok("/quote?sku=HOY-NLX-160-HMC-70")
    data = {"ftok": tok, "sku_r": "HOY-NLX-160-HMC-70", "discount": "DOLG25"}
    assert c().post("/quote/discount", data=data).status_code == 302
    assert c().post("/quote/discount", data=data).status_code == 302
    assert len(AUDIT_EVENTS) == 1


def test_hostile_names_escaped_everywhere():
    # F-W2-03: autoescape must hold on every surface a name reaches.
    from app.app import WALKINS
    from iris import new_walkin
    WALKINS.save(new_walkin(display_name="<script>alert(1)</script>Béla",
                            created_by="t", token_fn=lambda: "Z1-xss",
                            now_fn=lambda: "T0"))
    for path in ("/lencsekereso?person=Z1-xss",
                 "/quote?sku=HOY-NLX-160-HMC-70&person=Z1-xss",
                 "/print/munkalap?sku_r=HOY-NLX-160-HMC-70&person=Z1-xss",
                 "/print/latasvizsgalat?name=%3Cscript%3Ealert(1)%3C/script%3E"):
        body = c().get(path).data.decode()
        assert "<script>alert" not in body, path
        assert "&lt;script&gt;" in body, path


def test_konzultacio_basket_equals_quote_page_total():
    # F-W2-01: one money path — the customer screen and the operator quote
    # show the same gross for the same configuration.
    konz = c().get("/konzultacio?od_sph=-2&os_sph=-2&tier=Alap"
                   "&frame=FRM-EO-CLASS-01").data.decode()
    quote = c().get("/quote?sku_r=EYT-ALAP-150-HARD-65"
                    "&sku_l=EYT-ALAP-150-HARD-65"
                    "&frame=FRM-EO-CLASS-01").data.decode()
    total = "42 164 Ft"     # huf() uses narrow no-break spaces
    assert total in konz and total in quote


def test_print_routes_accept_post_for_sensitive_data():
    # F-W2-04: Rx/health values POSTed stay out of request logs.
    r = c().post("/print/latasvizsgalat",
                 data={"name": "Kovács Éva", "ar_j_sph": "−6.75"},
                 headers={"Origin": "http://localhost"})
    assert r.status_code == 200
    b = r.data.decode()
    assert "Kovács Éva" in b and "−6.75" in b


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


# ------------------------------------------------------------- shell (W2 close)
def test_kezdolap_is_landing_and_legacy_finder_links_redirect():
    r = c().get("/")
    assert r.status_code == 200
    b = r.data.decode()
    assert "Ügyfélkeresés" in b and 'action="/ugyfel"' in b
    assert "Készlet-ellenőrzés" in b            # present but disabled (W3)
    assert "Aláírásra váró nyilatkozatok" in b and "Mai átvételek" in b
    legacy = c().get("/?od_sph=-2&os_sph=-2")   # pre-shell finder bookmark
    assert legacy.status_code == 302
    assert "/lencsekereso" in legacy.headers["Location"]


def test_left_rail_renders_all_ia_map_items():
    b = c().get("/").data.decode()
    for label in ("Kezdőlap", "Ügyfelek", "Lencsekereső", "Konzultáció",
                  "Ajánlat", "Megrendelések", "Eladások", "Készlet",
                  "Kimutatások", "Adminisztráció"):
        assert label in b, label
    assert b.count('aria-disabled="true"') == 4  # W3 items (Megrendelések live)
    for href in ('href="/lencsekereso"', 'href="/ugyfel"',
                 'href="/konzultacio"', 'href="/quote"'):
        assert href in b, href


def test_finder_subtitle_says_ajanlott_elol():
    b = c().get("/lencsekereso?od_sph=-2&os_sph=-2").data.decode()
    assert "ajánlott elöl" in b
    assert "best margin first" not in b


def test_quote_without_sku_is_friendly_empty_state_not_404():
    r = c().get("/quote")
    assert r.status_code == 200
    assert "Nincs kiválasztott lencsepár" in r.data.decode()


# ---------------------------------------------------------- W3-1 (M4 orders)
def _create_order(**extra):
    data = {"sku_r": "HOY-NLX-160-HMC-70", "sku_l": "HOY-NLX-150-HMC-70",
            "frame": "FRM-RB-5228", "person": "P-1001",
            "lens_source": "rendeles", "due": "2099-01-10"}
    data.update(extra)
    return c().post("/megrendeles/uj", data=data)


def test_order_created_from_quote_with_szp_id_and_events():
    r = _create_order()
    assert r.status_code == 302
    oid = r.headers["Location"].rsplit("/", 1)[-1]
    assert oid.startswith("SZP-")
    b = c().get(f"/megrendeles/{oid}").data.decode()
    assert "Felvett" in b and "Kovács Éva" in b
    assert "Megrendelés felvéve" in b            # eseménynapló created row
    assert "Hoya Nulux" in b and "Ray-Ban" in b
    assert "2099-01-10" in b
    # quote trail persisted and converted
    from app.app import QUOTE_STORE
    quotes = [q for revs in QUOTE_STORE._revs.values() for q in revs]
    assert any(q.converted_order_id == oid for q in quotes)


def test_order_double_submit_replays_first_szp_id():
    body = c().get("/quote?sku_r=HOY-NLX-160-HMC-70").data.decode()
    import re
    tok = re.search(r'name="ftok" value="([0-9a-f]+)"', body).group(1)
    first = _create_order(ftok=tok)
    second = _create_order(ftok=tok)
    assert first.headers["Location"] == second.headers["Location"]


def test_order_status_flow_and_cancel_audited():
    oid = _create_order().headers["Location"].rsplit("/", 1)[-1]
    assert c().post(f"/megrendeles/{oid}/status",
                    data={"target": "megrendelve"}).status_code == 302
    b = c().get(f"/megrendeles/{oid}").data.decode()
    assert "Megrendelve" in b
    # backwards / illegal transition -> 400
    assert c().post(f"/megrendeles/{oid}/status",
                    data={"target": "felvett"}).status_code == 400
    # cancel: any staff, reason mandatory, audited with actor (R7)
    assert c().post(f"/megrendeles/{oid}/lemond",
                    data={"reason": ""}).status_code == 400
    assert c().post(f"/megrendeles/{oid}/lemond",
                    data={"reason": "ügyfél visszalépett"}).status_code == 302
    from app.app import ORDERS, current_operator
    audit = [a for a in ORDERS.audit_events
             if a["event_type"] == "order_cancel" and oid in a["payload"]]
    assert len(audit) == 1 and audit[0]["actor"] == current_operator()
    b = c().get(f"/megrendeles/{oid}").data.decode()
    assert "Lemondva" in b and "ügyfél visszalépett" in b
    # terminal: no cancel card, no status buttons
    assert "Megrendelés lemondása" not in b


def test_order_list_quick_filters_and_period():
    from app.app import ORDERS
    ORDERS._revs.clear(); ORDERS._events.clear()
    oid1 = _create_order().headers["Location"].rsplit("/", 1)[-1]
    oid2 = _create_order(lens_source="keszlet").headers["Location"]\
        .rsplit("/", 1)[-1]
    c().post(f"/megrendeles/{oid2}/status", data={"target": "beerkezett"})
    c().post(f"/megrendeles/{oid2}/status", data={"target": "kesz"})
    mind = c().get("/megrendelesek").data.decode()
    assert oid1 in mind and oid2 in mind
    assert "Lencsék szállítótól megrendelendőek" in mind   # audited chip text
    rendel = c().get("/megrendelesek?szuro=megrendelendo").data.decode()
    assert oid1 in rendel and oid2 not in rendel
    kiadhato = c().get("/megrendelesek?szuro=kiadhato").data.decode()
    assert oid2 in kiadhato and oid1 not in kiadhato
    keso = c().get("/megrendelesek?szuro=keso").data.decode()
    assert oid1 not in keso and oid2 not in keso           # future due dates
    assert c().get("/megrendelesek?szuro=nonsense&napok=zzz").status_code == 200


def test_order_tharanis_dry_run_writes_event_never_sends():
    import app.app as A
    from vendors.tharanis import TharanisOrderSink
    oid = _create_order().headers["Location"].rsplit("/", 1)[-1]
    old = A.THARANIS
    try:
        A.THARANIS = TharanisOrderSink(mode="dry_run")
        assert c().post(f"/megrendeles/{oid}/tharanis").status_code == 302
    finally:
        A.THARANIS = old
    b = c().get(f"/megrendeles/{oid}").data.decode()
    assert "dry-run" in b and "berak" in b
    assert "&lt;berak&gt;" in b                  # XML escaped into the page
    ev = [e for e in A.ORDERS.events(oid) if e.event_type == "tharanis_dry_run"]
    assert len(ev) == 1 and "<berak>" in ev[0].payload
    # default sink (off) records the refusal as a note event
    assert c().post(f"/megrendeles/{oid}/tharanis").status_code == 302
    notes = [e for e in A.ORDERS.events(oid) if e.event_type == "note"]
    assert any("elutasítva" in e.note for e in notes)


def test_order_promotion_registered_on_first_sale_only():
    from app.app import ORDERS, PROMOTIONS
    ORDERS._revs.clear(); ORDERS._events.clear()
    PROMOTIONS._rows.clear()
    oid1 = _create_order().headers["Location"].rsplit("/", 1)[-1]
    ev1 = [e for e in ORDERS.events(oid1) if e.event_type == "promotion"]
    assert len(ev1) == 1 and "HOY-NLX-160-HMC-70" in ev1[0].note
    oid2 = _create_order().headers["Location"].rsplit("/", 1)[-1]
    assert [e for e in ORDERS.events(oid2)
            if e.event_type == "promotion"] == []          # already known
    assert {r.sku for r in PROMOTIONS.pending()} == \
        {"HOY-NLX-160-HMC-70", "HOY-NLX-150-HMC-70"}


def test_megrendelesek_nav_item_is_live():
    b = c().get("/").data.decode()
    assert 'href="/megrendelesek"' in b
    assert b.count('aria-disabled="true"') == 4  # W3 badge came off one item


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
