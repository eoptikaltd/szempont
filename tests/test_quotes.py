"""M2 quotes persistence tests — W2 item 1 (rulings 2026-07-16, frozen).

Covers: record building from engine quotes (pair + frame + services),
D1 payer block, D2 editable/auto-added/soft-removed lines, D3 curated
discounts + audit, D6 offer variant sets, A1 final-gross rounding,
append-only revisions, and BQ (de)serialization against the DDL columns.
"""

from decimal import Decimal as D

import pytest

from pricing.engine import price_quote
from pricing.models import QuoteRequest
from quotes import (
    DiscountConfig, InMemoryQuoteStore, PayerInfo, QuoteError, QuoteRecord,
    QuoteStatus, ServiceLine, add_service_line, apply_discount,
    assign_offer_set, build_quote_record, edit_line, from_bq_row,
    invoice_lines, remove_line, restore_line, to_bq_row, totals, transition,
)
from quotes.records import clear_discount, payer_invoice_ready
from quotes.store import validate_for_save
from tests.test_pricing import override, snapshot

DAY = "2026-07-16"
TS = "2026-07-16T10:00:00+00:00"


def eng(sku="HOY-160-HMC-70", opts=frozenset(), overrides=()):
    return price_quote(snapshot(overrides=overrides),
                       QuoteRequest(sku=sku, option_codes=opts,
                                    quote_date=DAY, quantity=1))


def rec(**kw):
    args = dict(
        quote_id="Q1", quote_date=DAY, created_by="anna", created_at=TS,
        engine_quotes=[("OD", eng()), ("OS", eng("EYT-150-HARD-65"))],
        frame=("FRM-RB-5228", "Ray-Ban RB5228 keret", D("39000")),
        auto_services=[ServiceLine("Szemüvegkészítés munkadíj", D("4500"))],
    )
    args.update(kw)
    return build_quote_record(**args)


def counter_clock():
    n = 0
    def now():
        nonlocal n
        n += 1
        return f"2026-07-16T10:00:0{n}+00:00"
    return now


# ------------------------------------------------------------------- building
def test_pair_frame_service_totals_and_vat():
    r = rec()
    t = totals(r)
    # 18000 (OD lens) + 6900 (OS lens) + 39000 frame + 4500 munkadíj
    assert t.basket_net == D("68400")
    assert t.total_retail_net == D("68400")
    assert t.total_retail_gross == D("86868")          # 68400 * 1.27, whole HUF
    assert [l.line_type for l in r.lines] == ["lens", "lens", "frame", "service"]
    assert r.lines[3].auto_added is True               # D2 munkadíj flag
    assert r.status is QuoteStatus.DRAFT
    assert r.catalog_version == "hoya-abc123def456"    # engine anchor kept


def test_final_gross_rounds_half_up_only_at_the_end():
    # 333 net * 1.27 = 422.91 -> 423 (A1, frozen)
    r = rec(engine_quotes=[], frame=None, auto_services=[],
            services=[ServiceLine("Javítás", D("333"))],
            catalog_version="v", vat_rate=D("0.27"))
    assert totals(r).total_retail_gross == D("423")


def test_option_lines_carry_eye_prefix_and_qty():
    q = eng(opts=frozenset({"photochromic"}))
    r = rec(engine_quotes=[("OD", q)], frame=None, auto_services=[])
    assert [l.line_type for l in r.lines] == ["lens", "option"]
    assert r.lines[1].name == "OD · Fényre sötétedő"
    assert totals(r).basket_net == q.total_retail_net


def test_price_override_lands_as_akcios_ar_line_and_sums_match():
    ov = override("25000", "2026-07-01")               # list would be 30000
    q = eng(opts=frozenset({"photochromic"}), overrides=[ov])
    r = rec(engine_quotes=[("OD", q)], frame=None, auto_services=[])
    akcio = r.lines[-1]
    assert akcio.line_type == "discount" and akcio.auto_added
    assert akcio.source == "override"
    assert akcio.sku == "OV1"                          # override_id, structured
    assert akcio.unit_retail_net == D("-5000")
    assert totals(r).basket_net == q.total_retail_net == D("25000")


def test_mixed_snapshot_versions_rejected():
    other = price_quote(snapshot(version="other-cat"),
                        QuoteRequest(sku="HOY-160-HMC-70", quote_date=DAY,
                                     quantity=1))
    with pytest.raises(QuoteError):
        rec(engine_quotes=[("OD", eng()), ("OS", other)])


# ---------------------------------------------------------------- edits (D2)
def test_every_line_is_editable_including_auto_added():
    r = rec()
    r = edit_line(r, 3, unit_retail_net=D("6000"), name="Munkadíj (extra)")
    assert r.lines[3].unit_retail_net == D("6000")
    assert totals(r).basket_net == D("69900")
    with pytest.raises(QuoteError):
        edit_line(r, 3, qty=0)
    with pytest.raises(QuoteError):
        edit_line(r, 99, qty=1)


def test_removed_line_kept_but_excluded_from_totals_and_invoice():
    r = remove_line(rec(), 3)                          # optician drops munkadíj
    assert r.lines[3].removed is True                  # soft delete, row kept
    assert totals(r).basket_net == D("63900")
    assert [l.line_type for l in invoice_lines(r)] == ["lens", "lens", "frame"]
    r = restore_line(r, 3)
    assert totals(r).basket_net == D("68400")


def test_add_service_line_after_build():
    r = add_service_line(rec(), ServiceLine("Vékonyítás extra", D("2000")))
    assert r.lines[-1].line_type == "service"
    assert totals(r).basket_net == D("70400")


def test_no_edits_once_converted():
    r = transition(transition(rec(), QuoteStatus.SAVED),
                   QuoteStatus.CONVERTED, order_id="ORD-1")
    with pytest.raises(QuoteError):
        remove_line(r, 0)
    with pytest.raises(QuoteError):
        add_service_line(r, ServiceLine("x", D("1")))


# ---------------------------------------------------------------- payer (D1)
def test_health_fund_payer_required_fields():
    payer = PayerInfo(payer_type="health_fund", payer_name="OTP Egészségpénztár",
                      payer_member_id="EP-12345")
    r = rec(payer=payer)
    assert r.payer.payer_name == "OTP Egészségpénztár"
    with pytest.raises(QuoteError):
        rec(payer=PayerInfo(payer_type="health_fund"))
    with pytest.raises(QuoteError):
        rec(payer=PayerInfo(payer_type="szomszéd"))


def test_payer_invoice_ready_needs_full_d1_block():
    partial = PayerInfo(payer_type="health_fund", payer_name="OTP EP",
                        payer_member_id="EP-1")
    assert not payer_invoice_ready(partial)
    full = PayerInfo(payer_type="health_fund", payer_name="OTP EP",
                     payer_member_name="Kovács Éva", payer_member_id="EP-1",
                     payer_billing_address="1066 Budapest, Teréz krt. 50.")
    assert payer_invoice_ready(full)
    assert payer_invoice_ready(PayerInfo())            # person: always ready


# ------------------------------------------------------------- discounts (D3)
def cfg(**kw):
    args = dict(config_id="TORZS10", name="Törzsvásárlói 10%", kind="percent",
                value=D("10"), valid_from="2026-07-01")
    args.update(kw)
    return DiscountConfig(**args)


def test_percent_discount_reduces_net_before_vat():
    r = apply_discount(rec(), cfg())
    t = totals(r)
    assert t.discount_net == D("6840")
    assert t.total_retail_net == D("61560")
    assert t.total_retail_gross == D("78181")          # 61560*1.27 = 78181.2
    assert r.discount_config_id == "TORZS10"


def test_discount_scope_limits_to_line_types():
    c = cfg(config_id="LENS5", value=D("50"),
            applies_to_line_types=frozenset({"lens"}))
    r = apply_discount(rec(), c)
    assert r.discount_net == D("12450")                # 50% of 18000+6900


def test_amount_discount_clamped_to_basket():
    c = cfg(config_id="KUPON", kind="amount_net", value=D("999999"))
    r = apply_discount(rec(), c)
    assert r.discount_net == totals(rec()).basket_net
    assert totals(r).total_retail_net == D("0")


def test_approval_gate_and_effective_dating():
    gated = cfg(config_id="VIP20", value=D("20"), requires_approval=True)
    with pytest.raises(QuoteError):
        apply_discount(rec(), gated)
    r = apply_discount(rec(), gated, approved_by="sabie")
    assert r.discount_approved_by == "sabie"
    with pytest.raises(QuoteError):
        apply_discount(rec(), cfg(valid_from="2026-08-01"))
    with pytest.raises(QuoteError):
        apply_discount(rec(), cfg(active=False))


def test_free_form_discount_cannot_be_saved():
    import dataclasses
    r = dataclasses.replace(rec(), discount_net=D("1000"))  # no config id
    with pytest.raises(QuoteError):
        validate_for_save(r)
    assert validate_for_save(apply_discount(rec(), cfg())) is None
    r2 = clear_discount(apply_discount(rec(), cfg()))
    assert r2.discount_net == D("0") and r2.discount_config_id is None


def test_override_discount_line_saves_without_config_id():
    # Wave-gate fix (a): an override-sourced akciós ár line is NOT a D3
    # discount — it must save with no discount_config_id on the quote.
    q = eng(opts=frozenset({"photochromic"}),
            overrides=[override("25000", "2026-07-01")])
    r = rec(engine_quotes=[("OD", q)], frame=None, auto_services=[])
    saved = InMemoryQuoteStore(now_fn=counter_clock()).save(r)
    assert saved.discount_config_id is None
    assert saved.lines[-1].source == "override" and saved.lines[-1].sku == "OV1"


def test_config_discount_line_without_config_id_refuses_to_save():
    # Wave-gate fix (b): a config-sourced discount line still demands the
    # curated config id; an unsourced discount line is refused outright.
    import dataclasses
    from quotes.records import QuoteLineRec
    base = rec()
    kedvezmeny = QuoteLineRec("discount", None, "Kedvezmény", 1, D("-1000"),
                              source="config")
    orphan = dataclasses.replace(base, lines=base.lines + (kedvezmeny,))
    with pytest.raises(QuoteError):
        validate_for_save(orphan)
    ok = dataclasses.replace(orphan, discount_net=D("1000"),
                             discount_config_id="TORZS10")
    assert validate_for_save(ok) is None
    unsourced = dataclasses.replace(base, lines=base.lines + (
        QuoteLineRec("discount", None, "Kedvezmény", 1, D("-1000")),))
    with pytest.raises(QuoteError):
        validate_for_save(unsourced)


def test_discount_save_emits_one_audit_event():
    store = InMemoryQuoteStore(now_fn=counter_clock(), id_fn=lambda: "EV1")
    saved = store.save(apply_discount(rec(), cfg()))
    store.save(saved)                                  # unchanged re-save
    assert len(store.audit_events) == 1
    ev = store.audit_events[0]
    assert ev["event_type"] == "discount"
    assert '"discount_config_id": "TORZS10"' in ev["payload"]
    store.save(apply_discount(saved, cfg(config_id="VIP20", value=D("20"),
                                         requires_approval=True),
                              approved_by="sabie"))
    assert len(store.audit_events) == 2


# ---------------------------------------------------------- offer variants (D6)
def test_offer_set_shares_id_distinct_quotes():
    variants = assign_offer_set(
        [rec(quote_id=f"Q{i}") for i in (1, 2, 3)],
        offer_set_id="OS1", labels=["Alap", "Ajánlott", "Prémium"])
    assert {v.offer_set_id for v in variants} == {"OS1"}
    assert [v.variant_label for v in variants] == ["Alap", "Ajánlott", "Prémium"]
    with pytest.raises(QuoteError):
        assign_offer_set([rec(), rec()], "OS2", ["a", "b"])  # same quote_id


def test_store_load_offer_set_returns_latest_revisions():
    store = InMemoryQuoteStore(now_fn=counter_clock())
    for v in assign_offer_set([rec(quote_id=f"Q{i}") for i in (1, 2)],
                              "OS1", ["Alap", "Prémium"]):
        store.save(v)
    q1 = store.load("Q1")
    store.save(remove_line(q1, 3))                     # edit -> revision 1
    got = {v.quote_id: v for v in store.load_offer_set("OS1")}
    assert set(got) == {"Q1", "Q2"}
    assert got["Q1"].revision == 1 and got["Q2"].revision == 0


# ------------------------------------------------------------------- lifecycle
def test_status_flow_and_terminal_states():
    r = rec()
    r = transition(r, QuoteStatus.SAVED)
    r = transition(r, QuoteStatus.PRINTED)
    with pytest.raises(QuoteError):
        transition(r, QuoteStatus.CONVERTED)           # order_id required
    r = transition(r, QuoteStatus.CONVERTED, order_id="ORD-9")
    assert r.converted_order_id == "ORD-9"
    with pytest.raises(QuoteError):
        transition(r, QuoteStatus.EXPIRED)             # converted is terminal
    with pytest.raises(QuoteError):
        transition(rec(), QuoteStatus.CONVERTED, order_id="X")  # draft can't


def test_append_only_revisions():
    store = InMemoryQuoteStore(now_fn=counter_clock())
    r0 = store.save(rec())
    r1 = store.save(edit_line(r0, 3, unit_retail_net=D("5000")))
    assert (r0.revision, r1.revision) == (0, 1)
    assert r0.saved_at != r1.saved_at
    assert store.load("Q1").lines[3].unit_retail_net == D("5000")
    assert len(store.revisions("Q1")) == 2             # history intact
    assert store.revisions("Q1")[0].lines[3].unit_retail_net == D("4500")


# ------------------------------------------------------------------ BQ serde
def ddl_quotes_columns():
    """Parse the ACTUAL DDL files (F-W2-05): this test fails when either the
    DDL or the serializer changes without the other."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    field = re.compile(r"\b([a-z_][a-z0-9_]*)\s+"
                       r"(?:STRING|INT64|NUMERIC|BOOL|DATE|TIMESTAMP|JSON|"
                       r"FLOAT64)\b")
    ddl1 = (root / "infra/ddl/001_szempont_dataset.sql").read_text()
    block = re.search(
        r"CREATE TABLE IF NOT EXISTS `szempont\.quotes` \((.*?)\n\)",
        ddl1, re.S).group(1)
    cols, struct = set(), set()
    depth = 0
    for raw in block.splitlines():
        line = raw.split("--")[0].strip()
        if not line:
            continue
        names = set(field.findall(line))
        if depth == 0:
            cols |= names
            m = re.match(r"([a-z_]+)\s+ARRAY<", line)
            if m:
                cols.add(m.group(1))
        else:
            struct |= names
        depth += line.count("<") - line.count(">")
    ddl2 = (root / "infra/ddl/002_w2_rulings.sql").read_text()
    for name in re.findall(
            r"ALTER TABLE `szempont\.quotes`\s+"
            r"ADD COLUMN IF NOT EXISTS\s+([a-z_.]+)", ddl2):
        if "." in name:
            struct.add(name.split(".", 1)[1])
        else:
            cols.add(name)
    return cols, struct


def test_bq_row_matches_ddl_and_roundtrips():
    store = InMemoryQuoteStore(now_fn=counter_clock())
    r = store.save(apply_discount(
        rec(person_id="Z1-0d1f", payer=PayerInfo(
            payer_type="health_fund", payer_name="OTP Egészségpénztár",
            payer_member_id="EP-1")), cfg()))
    row = to_bq_row(r)
    ddl_cols, ddl_struct = ddl_quotes_columns()
    assert set(row) == ddl_cols                        # F-W2-05: no drift
    assert set(row["lines"][0]) == ddl_struct
    assert row["total_retail_net"] == "61560"          # NUMERIC as string
    assert row["lines"][3]["name"] == "Szemüvegkészítés munkadíj"  # diacritics
    assert from_bq_row(row) == r                       # lossless roundtrip


# ------------------------------------------------- wave-close review additions
def test_gross_line_allocation_sums_exactly_to_a1_total():
    # F-W2-01: naive per-line rounding drifts from the once-rounded total.
    from quotes import gross_line_allocation
    from decimal import ROUND_HALF_UP
    r = rec(engine_quotes=[], frame=None, auto_services=[],
            services=[ServiceLine("Igazítás", D("10")),
                      ServiceLine("Tisztítás", D("10")),
                      ServiceLine("Vésés", D("10"))],
            catalog_version="v", vat_rate=D("0.27"))
    t = totals(r)
    assert t.total_retail_gross == D("38")             # 30 * 1.27 = 38.1 -> 38
    naive = sum((l.net * D("1.27")).quantize(D("1"), rounding=ROUND_HALF_UP)
                for l in r.lines)
    assert naive == D("39")                            # the drift being fixed
    alloc = gross_line_allocation(r)
    assert sum(g for _, g in alloc) == t.total_retail_gross
    # holds with a discount and with removed lines too
    r2 = apply_discount(rec(), cfg())
    assert sum(g for _, g in gross_line_allocation(r2)) == \
        totals(r2).total_retail_gross
    r3 = remove_line(rec(), 3)
    alloc3 = gross_line_allocation(r3)
    assert all(l.name != "Szemüvegkészítés munkadíj" for l, _ in alloc3)
    assert sum(g for _, g in alloc3) == totals(r3).total_retail_gross


def test_resave_unchanged_quote_is_noop():
    # F-W2-07: refresh/retry of an unchanged save appends nothing.
    store = InMemoryQuoteStore(now_fn=counter_clock())
    r0 = store.save(rec())
    assert store.save(r0) is r0                        # same object back
    assert store.save(rec()).revision == 0             # rebuilt, same content
    assert len(store.revisions("Q1")) == 1
    r1 = store.save(edit_line(r0, 3, unit_retail_net=D("5000")))
    assert r1.revision == 1 and len(store.revisions("Q1")) == 2


def test_persisted_quote_is_reproducible():
    assert rec() == rec()                              # pure builder
    clock_a, clock_b = counter_clock(), counter_clock()
    a = InMemoryQuoteStore(now_fn=clock_a, id_fn=lambda: "E")
    b = InMemoryQuoteStore(now_fn=clock_b, id_fn=lambda: "E")
    assert to_bq_row(a.save(rec())) == to_bq_row(b.save(rec()))
