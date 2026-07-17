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
    # M5/MVP: a bare gated-discount URL does NOT price in — approval needed
    gated = c().get("/quote?sku=HOY-NLX-160-HMC-70&discount=DOLG25").data.decode()
    assert "jóváhagyás szükséges" in gated
    assert "Jóváhagyta" not in gated
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
    data = {"ftok": tok, "sku_r": "HOY-NLX-160-HMC-70", "discount": "DOLG25",
            "approver": "bozo.klaudia"}
    r1 = c().post("/quote/discount", data=data)
    r2 = c().post("/quote/discount", data=data)
    assert r1.status_code == 302 and r2.status_code == 302
    assert r1.headers["Location"] == r2.headers["Location"]  # same appr ref
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


def test_order_outbox_seam_no_tharanis_surface():
    # MVP override: orders queue as sync_status='pending'; no send route.
    from app.app import ORDERS
    oid = _create_order().headers["Location"].rsplit("/", 1)[-1]
    assert ORDERS.load(oid).sync_status == "pending"
    b = c().get(f"/megrendeles/{oid}").data.decode()
    assert "függőben" in b and "semmit nem küldünk" in b
    assert c().post(f"/megrendeles/{oid}/tharanis").status_code == 404


def test_order_deposit_and_payment_summary_not_invoice():
    from app.app import ORDERS
    oid = _create_order().headers["Location"].rsplit("/", 1)[-1]
    # validation: bad method / over total / junk amount
    assert c().post(f"/megrendeles/{oid}/eloleg",
                    data={"amount": "20000", "method": "bitcoin"})\
        .status_code == 400
    assert c().post(f"/megrendeles/{oid}/eloleg",
                    data={"amount": "9999999", "method": "keszpenz"})\
        .status_code == 400
    assert c().post(f"/megrendeles/{oid}/eloleg",
                    data={"amount": "húszezer", "method": "keszpenz"})\
        .status_code == 400
    assert c().post(f"/megrendeles/{oid}/eloleg",
                    data={"amount": "20000", "method": "keszpenz"})\
        .status_code == 302
    o = ORDERS.load(oid)
    assert str(o.deposit_gross) == "20000" and o.deposit_method == "keszpenz"
    detail = c().get(f"/megrendeles/{oid}").data.decode()
    assert "Előleg rögzítve" in detail          # eseménynapló row
    summary = c().get(f"/print/fizetesi-osszesito?order={oid}").data.decode()
    assert "NEM SZÁMLA" in summary
    assert "Fizetendő átvételkor" in summary
    # 93 980 gross - 20 000 deposit = 73 980 remaining
    assert "73 980 Ft" in summary
    assert c().get("/print/fizetesi-osszesito?order=SZP-0000-0000")\
        .status_code == 404


def test_order_munkalap_pdf_generated_and_served():
    import shutil
    if shutil.which("wkhtmltopdf") is None:
        import pytest
        pytest.skip("wkhtmltopdf not installed")
    import os as _os
    import tempfile
    from app.app import ORDERS
    oid = _create_order().headers["Location"].rsplit("/", 1)[-1]
    with tempfile.TemporaryDirectory() as tmp:
        _os.environ["SZEMPONT_DOCS_DIR"] = tmp
        try:
            assert c().post(f"/megrendeles/{oid}/munkalap-pdf")\
                .status_code == 302
        finally:
            _os.environ.pop("SZEMPONT_DOCS_DIR", None)
        o = ORDERS.load(oid)
        assert o.munkalap_gcs_uri and o.munkalap_gcs_uri.endswith(
            f"{oid}.pdf")
        assert "/munkalap/" in o.munkalap_gcs_uri   # R11 path shape
        pdf = c().get(f"/megrendeles/{oid}/munkalap.pdf")
        assert pdf.status_code == 200
        assert pdf.data[:5] == b"%PDF-"


def test_kezdolap_queues_pickups_and_unsigned_walkins():
    from app.app import ORDERS, WALKINS
    from iris import new_walkin
    ORDERS._revs.clear(); ORDERS._events.clear()
    oid = _create_order().headers["Location"].rsplit("/", 1)[-1]
    c().post(f"/megrendeles/{oid}/status", data={"target": "megrendelve"})
    c().post(f"/megrendeles/{oid}/status", data={"target": "beerkezett"})
    c().post(f"/megrendeles/{oid}/status", data={"target": "kesz"})
    WALKINS.save(new_walkin(display_name="Aláíratlan Aladár",
                            created_by="t", token_fn=lambda: "Z1-nosig",
                            now_fn=lambda: "2026-07-18T09:00:00"))
    home = c().get("/").data.decode()
    assert oid in home and "értesítendő" in home
    assert "Aláíratlan Aladár" in home and "GDPR hiányzik" in home
    # mark notified -> flag flips, event logged
    assert c().post(f"/megrendeles/{oid}/ertesitve",
                    data={"next": "/"}).status_code == 302
    home2 = c().get("/").data.decode()
    assert "értesítve" in home2
    assert any("értesítve" in e.note.lower()
               for e in ORDERS.events(oid) if e.event_type == "note")
    # átadva closes the loop and clears the queue
    c().post(f"/megrendeles/{oid}/status", data={"target": "atadva"})
    home3 = c().get("/").data.decode()
    assert oid not in home3


def test_order_create_with_gated_discount_requires_approval_ref():
    # no approval ref -> 400; with the ref from the audited POST -> applied
    r = _create_order(discount="DOLG25")
    assert r.status_code == 400
    tok = _ftok("/quote?sku=HOY-NLX-160-HMC-70")
    loc = c().post("/quote/discount", data={
        "ftok": tok, "sku_r": "HOY-NLX-160-HMC-70",
        "sku_l": "HOY-NLX-150-HMC-70", "frame": "FRM-RB-5228",
        "discount": "DOLG25", "approver": "bozo.klaudia"},
    ).headers["Location"]
    import re
    appr = re.search(r"appr=([0-9a-f]+)", loc).group(1)
    ok = _create_order(discount="DOLG25", appr=appr)
    assert ok.status_code == 302
    from app.app import ORDERS
    oid = ok.headers["Location"].rsplit("/", 1)[-1]
    o = ORDERS.load(oid)
    assert o.discount_config_id == "DOLG25"
    assert o.discount_approved_by == "bozo.klaudia"
    # non-approver rejected on the POST path (no audit, error code back)
    tok2 = _ftok("/quote?sku=HOY-NLX-160-HMC-70")
    loc2 = c().post("/quote/discount", data={
        "ftok": tok2, "sku_r": "HOY-NLX-160-HMC-70",
        "discount": "DOLG25", "approver": "varga.orsolya"},
    ).headers["Location"]
    assert "appr_err=szerep" in loc2


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


def test_order_create_rejects_unknown_discount():
    # F-W3-02: unknown discount must 400, not silently price without it.
    assert _create_order(discount="NOPE").status_code == 400
    assert _create_order(discount="TORZS10").status_code == 302


def test_megrendelesek_nav_item_is_live():
    b = c().get("/").data.decode()
    assert 'href="/megrendelesek"' in b
    assert b.count('aria-disabled="true"') == 4  # W3 badge came off one item


def test_gated_discount_approver_audited_on_apply_never_on_render():
    # M5/MVP: a named approver (Üzletvezető/Cégvezető) authorizes the gated
    # discount; exactly ONE audit event, on the POST path only. The old
    # auto_approved_pre_m5 shim is retired — its marker no longer appears.
    from app.app import AUDIT_EVENTS
    AUDIT_EVENTS.clear()
    # POST without an approver: no audit, error code redirected back
    r0 = c().post("/quote/discount", data={
        "sku_r": "HOY-NLX-160-HMC-70", "discount": "DOLG25"})
    assert r0.status_code == 302 and "appr_err=szerep" in r0.headers["Location"]
    assert AUDIT_EVENTS == []
    # POST with a proper approver: one event, actor = the approver
    r = c().post("/quote/discount", data={
        "sku_r": "HOY-NLX-160-HMC-70", "discount": "DOLG25",
        "approver": "bozo.klaudia"})
    assert r.status_code == 302 and "discount=DOLG25" in r.headers["Location"]
    assert "appr=" in r.headers["Location"]
    assert len(AUDIT_EVENTS) == 1
    ev = AUDIT_EVENTS[0]
    assert ev["event_type"] == "discount"
    assert ev["actor"] == "bozo.klaudia"
    assert '"marker": "m5_approver_no_pin"' in ev["payload"]
    assert "auto_approved_pre_m5" not in ev["payload"]
    assert '"discount_config_id": "DOLG25"' in ev["payload"]
    # repeated renders of the approved discount: no further events,
    # approver named on the page
    import re
    appr = re.search(r"appr=([0-9a-f]+)", r.headers["Location"]).group(1)
    for _ in range(3):
        page = c().get("/quote?sku=HOY-NLX-160-HMC-70"
                       f"&discount=DOLG25&appr={appr}")
        assert page.status_code == 200
    assert "Bozó Klaudia" in page.data.decode()
    assert len(AUDIT_EVENTS) == 1
    AUDIT_EVENTS.clear()
    c().post("/quote/discount", data={
        "sku_r": "HOY-NLX-160-HMC-70", "discount": "TORZS10"})  # not gated
    c().get("/quote?sku=HOY-NLX-160-HMC-70&discount=TORZS10")
    assert AUDIT_EVENTS == []
