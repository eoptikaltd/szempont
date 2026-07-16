"""M3 tests — IRIS contract read side, Z1 walk-in flow, re-attribution join
(contracts/iris_contract.md, frozen columns), and the /ugyfel UI.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from iris import (
    FixturePersonDirectory, InMemoryWalkinStore, attributed_person_id,
    is_z1, new_walkin, walkin_to_bq_row,
)
from iris.directory import normalize_query


# -------------------------------------------------------------- normalization
def test_normalize_query_kinds_match_contract_keys():
    # name: payroll prefix stripped, accent-stripped, lowercase (rule 10)
    assert normalize_query("123 Kovács Éva") == ("name", "kovacs eva")
    assert normalize_query("  SZABÓ   Ágnes ") == ("name", "szabo agnes")
    # phone: digits only, formatting ignored
    assert normalize_query("+36 (30) 123-4567") == ("phone", "36301234567")
    assert normalize_query("06301234567") == ("phone", "06301234567")
    # email: lowercase equality key
    assert normalize_query("Kovacs.Eva@Example.com") == (
        "email", "kovacs.eva@example.com")
    # short digit runs are more likely a name fragment than a phone
    assert normalize_query("42")[0] == "name"


# ------------------------------------------------------------------ directory
def test_search_prefix_and_equality_semantics():
    d = FixturePersonDirectory()
    assert [c.person_id for c in d.search("kov")] == ["P-1001"]      # prefix
    assert [c.person_id for c in d.search("Kovács Éva")] == ["P-1001"]
    assert [c.person_id for c in d.search("kovacs eva")] == ["P-1001"]  # rule 10
    assert [c.person_id for c in d.search("+36 30 123 4567")] == ["P-1001"]
    assert [c.person_id for c in d.search("nagy.peter@example.com")] == ["P-1002"]
    assert d.search("nemletezo") == []
    assert d.search("   ") == []


def test_lookup_card_carries_contract_columns():
    d = FixturePersonDirectory()
    c = d.lookup("P-1001")
    assert c.display_name == "Kovács Éva"
    assert c.ep_member_hint is True          # D1 payer tie-in
    assert c.birth_date == "1985-04-12"
    assert d.lookup("P-9999") is None


# -------------------------------------------------------------------- walk-ins
def test_new_walkin_mints_z1_token_never_person_id():
    w = new_walkin(display_name="Betérő Béla", created_by="anna",
                   token_fn=lambda: "Z1-fixed", now_fn=lambda: "T0")
    assert w.z1_token == "Z1-fixed" and is_z1(w.z1_token)
    assert not is_z1("P-1001") and not is_z1(None)
    real = new_walkin(display_name="X", created_by="anna")
    assert real.z1_token.startswith("Z1-") and len(real.z1_token) == 39
    with pytest.raises(ValueError):
        new_walkin(display_name="   ", created_by="anna")


def test_walkin_row_matches_walkin_persons_ddl():
    w = new_walkin(display_name="Betérő Béla", created_by="anna",
                   phone_raw="+36 70 111 2222", ep_member=True,
                   ep_fund_name="OTP Egészségpénztár", ep_member_id="EP-7",
                   gdpr_signed=True,
                   token_fn=lambda: "Z1-fixed", now_fn=lambda: "T0")
    row = walkin_to_bq_row(w)
    assert set(row) == {
        "z1_token", "display_name", "phone_raw", "email_raw", "birth_date",
        "ep_member", "ep_fund_name", "ep_member_id", "gdpr_signed", "dm_ok",
        "created_by", "created_at",
    }
    assert row["ep_fund_name"] == "OTP Egészségpénztár"


def test_walkin_store_append_only_and_resolution_join():
    store = InMemoryWalkinStore()
    w = new_walkin(display_name="Betérő Béla", created_by="anna",
                   token_fn=lambda: "Z1-abc", now_fn=lambda: "T0")
    store.save(w)
    with pytest.raises(ValueError):
        store.save(w)                        # rows are never rewritten
    # unresolved: token passes through
    assert attributed_person_id("Z1-abc", store) == "Z1-abc"
    # IRIS resolves overnight -> join re-attributes at read time
    store.add_resolution("Z1-abc", "P-1001")
    assert attributed_person_id("Z1-abc", store) == "P-1001"
    # non-Z1 ids never touch the store
    assert attributed_person_id("P-1002", store) == "P-1002"
    assert attributed_person_id(None, store) is None


def test_quote_under_z1_reattributes_without_rewriting_the_record():
    from decimal import Decimal as D
    from quotes import ServiceLine, build_quote_record
    store = InMemoryWalkinStore()
    store.save(new_walkin(display_name="Betérő Béla", created_by="anna",
                          token_fn=lambda: "Z1-abc", now_fn=lambda: "T0"))
    rec = build_quote_record(
        quote_id="Q1", quote_date="2026-07-16", created_by="anna",
        created_at="T0", services=[ServiceLine("Javítás", D("1000"))],
        person_id="Z1-abc", catalog_version="v", vat_rate=D("0.27"))
    store.add_resolution("Z1-abc", "P-1001")
    assert rec.person_id == "Z1-abc"                       # stored row untouched
    assert attributed_person_id(rec.person_id, store) == "P-1001"


# -------------------------------------------------------------------------- UI
def ui():
    from app.app import app
    return app.test_client()


def test_ugyfel_search_renders_cards_and_flags():
    b = ui().get("/ugyfel?q=kov").data.decode()
    assert "Kovács Éva" in b and "P-1001" in b
    assert "EP-tag?" in b                    # D1 hint pill
    b2 = ui().get("/ugyfel?q=nagy").data.decode()
    assert "Nagy Péter" in b2 and "DM tiltva" in b2
    empty = ui().get("/ugyfel?q=senkisem").data.decode()
    assert "rögzítsd betérőként" in empty


def test_walkin_post_mints_z1_and_starts_sale():
    r = ui().post("/ugyfel/walkin", data={
        "name": "Betérő Béla", "phone": "+36 70 111 2222",
        "ep_member": "1", "ep_fund_name": "OTP Egészségpénztár",
        "ep_member_id": "EP-7", "gdpr_signed": "1"})
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["Location"]).query)
    token = q["person"][0]
    assert token.startswith("Z1-")
    from app.app import WALKINS
    saved = WALKINS.get(token)
    assert saved.display_name == "Betérő Béla" and saved.ep_member is True
    assert ui().post("/ugyfel/walkin", data={"name": "  "}).status_code == 400


def test_person_threads_from_finder_to_quote_and_resolves():
    from app.app import WALKINS
    # A-grade person chip on finder + carried into quote links
    b = ui().get("/?od_sph=-2&os_sph=-2&person=P-1001").data.decode()
    assert "Kovács Éva" in b and "person=P-1001" in b
    # Z1 walk-in on the quote: pending, then resolved via the join
    WALKINS.save(new_walkin(display_name="Betérő Béla", created_by="t",
                            token_fn=lambda: "Z1-ui-test", now_fn=lambda: "T0"))
    pending = ui().get(
        "/quote?sku=HOY-NLX-160-HMC-70&person=Z1-ui-test").data.decode()
    assert "Betérő Béla" in pending and "IRIS-feloldásra vár" in pending
    WALKINS.add_resolution("Z1-ui-test", "P-1001")
    resolved = ui().get(
        "/quote?sku=HOY-NLX-160-HMC-70&person=Z1-ui-test").data.decode()
    assert "azonosítva" in resolved and "P-1001" in resolved
    assert "Kovács Éva" in resolved         # card render via lookup_a
