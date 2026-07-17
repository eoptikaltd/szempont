"""M4 order tests — records, SZP ids, store/eseménynapló, promotions (W3-1)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime as dt
from decimal import Decimal as D

import pytest

from orders.ids import format_order_id, month_bucket, next_order_id
from orders.promotions import (InMemoryPromotionRegistry, daily_digest,
                               register_first_sale)
from orders.records import (LENS_SOURCES, OrderError, OrderRecord, OrderStatus,
                            STATUS_HU, allowed_next, build_order_from_quote,
                            cancel_order, from_bq_row, order_totals, to_bq_row,
                            transition_order)
from orders.store import InMemoryOrderStore, order_cancel_audit_event
from quotes.records import (PayerInfo, QuoteLineRec, QuoteRecord, QuoteStatus,
                            ServiceLine, build_quote_record, totals)


def counter_clock():
    n = [0]
    def now():
        n[0] += 1
        return f"2026-07-18T10:00:{n[0]:02d}+00:00"
    return now


def quote(**kw):
    """A saved-shape quote with lens + frame + munkadíj lines."""
    defaults = dict(
        quote_id="q-1", quote_date="2026-07-18", created_by="t.operator",
        created_at="2026-07-18T09:00:00+00:00",
        frame=("FRM-1", "Teszt keret", D("14900")),
        auto_services=[ServiceLine("Szemüvegkészítés munkadíj", D("4500"))],
        catalog_version="cat-v7", vat_rate=D("0.27"),
    )
    defaults.update(kw)
    rec = build_quote_record(**defaults)
    lens = QuoteLineRec("lens", "HOY-NLX-160-HMC-70", "OD · Hoya Nulux",
                        1, D("18000"))
    lens2 = QuoteLineRec("lens", "HOY-NLX-150-HMC-70", "OS · Hoya Nulux",
                         1, D("12500"))
    import dataclasses
    return dataclasses.replace(rec, lines=(lens, lens2) + rec.lines)


def order(**kw):
    defaults = dict(order_id="SZP-2607-0001", created_by="t.operator",
                    created_at="2026-07-18T10:00:00+00:00",
                    order_date="2026-07-18", due_date="2026-07-21")
    defaults.update(kw)
    return build_order_from_quote(quote(), **defaults)


# ------------------------------------------------------------------- ids (R4)
def test_szp_id_sequence_per_month():
    day = dt.date(2026, 7, 18)
    assert month_bucket(day) == "2607"
    assert next_order_id([], day) == "SZP-2607-0001"
    assert next_order_id(["SZP-2607-0001", "SZP-2607-0007"], day) == \
        "SZP-2607-0008"
    # other months / legacy SO- ids / junk never advance the sequence
    assert next_order_id(["SZP-2606-0042", "SO-1604869D", "junk"],
                         day) == "SZP-2607-0001"
    with pytest.raises(ValueError):
        format_order_id("2607", 0)


# ---------------------------------------------------------------- conversion
def test_build_order_copies_quote_content():
    o = order()
    assert o.status is OrderStatus.FELVETT
    assert o.quote_id == "q-1" and o.catalog_version == "cat-v7"
    assert [l.line_type for l in o.lines] == ["lens", "lens", "frame",
                                              "service"]
    # same money path as quotes (A1)
    assert order_totals(o).total_retail_gross == \
        totals(quote()).total_retail_gross


def test_build_order_drops_removed_lines_and_validates():
    import dataclasses
    q = quote()
    q = dataclasses.replace(q, lines=tuple(
        dataclasses.replace(l, removed=(l.line_type == "service"))
        for l in q.lines))
    o = build_order_from_quote(q, order_id="SZP-2607-0002",
                               created_by="t", created_at="T0",
                               order_date="2026-07-18", due_date="2026-07-21")
    assert all(l.line_type != "service" for l in o.lines)
    with pytest.raises(OrderError):        # non-SZP id refused (R4)
        build_order_from_quote(q, order_id="SO-123", created_by="t",
                               created_at="T0", order_date="2026-07-18",
                               due_date="2026-07-21")
    with pytest.raises(OrderError):        # due before order date
        build_order_from_quote(q, order_id="SZP-2607-0003", created_by="t",
                               created_at="T0", order_date="2026-07-18",
                               due_date="2026-07-17")
    with pytest.raises(OrderError):        # unknown lens source
        build_order_from_quote(q, order_id="SZP-2607-0003", created_by="t",
                               created_at="T0", order_date="2026-07-18",
                               due_date="2026-07-21", lens_source="varazslat")


# ------------------------------------------------------------- status machine
def test_status_machine_full_path_and_stock_shortcut():
    o = order()
    for target in (OrderStatus.MEGRENDELVE, OrderStatus.BEERKEZETT,
                   OrderStatus.CSISZOLAS, OrderStatus.KESZ,
                   OrderStatus.QC_KESZ, OrderStatus.ATADVA):
        o = transition_order(o, target)
    assert o.status is OrderStatus.ATADVA
    assert allowed_next(o) == ()
    # stock lens skips the supplier leg
    o2 = order(order_id="SZP-2607-0002", lens_source="keszlet")
    o2 = transition_order(o2, OrderStatus.BEERKEZETT)
    assert o2.status is OrderStatus.BEERKEZETT
    with pytest.raises(OrderError):        # no backwards moves
        transition_order(o2, OrderStatus.FELVETT)
    with pytest.raises(OrderError):        # cancel must go through cancel_order
        transition_order(o2, OrderStatus.LEMONDVA)


def test_cancel_any_nonterminal_needs_reason_r7():
    o = transition_order(order(), OrderStatus.MEGRENDELVE)
    c = cancel_order(o, reason="Ügyfél visszalépett")
    assert c.status is OrderStatus.LEMONDVA
    assert c.cancel_reason == "Ügyfél visszalépett"
    with pytest.raises(OrderError):
        cancel_order(c, reason="még egyszer")     # terminal
    with pytest.raises(OrderError):
        cancel_order(o, reason="   ")             # empty reason


# ---------------------------------------------------------------------- store
def test_store_events_and_cancel_audit():
    store = InMemoryOrderStore(now_fn=counter_clock(),
                               id_fn=iter(f"ev{i}" for i in range(99)).__next__)
    o = store.save(order(), actor="valner.szabolcs")
    assert o.revision == 0
    assert [e.event_type for e in store.events(o.order_id)] == ["created"]
    # unchanged save is a no-op (no new revision, no event)
    assert store.save(o, actor="valner.szabolcs") is o
    assert len(store.events(o.order_id)) == 1
    # status advance -> status event, no audit
    o2 = store.save(transition_order(o, OrderStatus.MEGRENDELVE),
                    actor="bozo.klaudia")
    assert o2.revision == 1
    ev = store.events(o.order_id)[-1]
    assert ev.event_type == "status" and "Megrendelve" in ev.note
    assert store.audit_events == []
    # cancel -> cancel event AND audit_log row with the ACTOR (R7)
    o3 = store.save(cancel_order(o2, reason="rossz PD"),
                    actor="varga.orsolya")
    assert store.events(o.order_id)[-1].event_type == "cancel"
    assert len(store.audit_events) == 1
    audit = store.audit_events[0]
    assert audit["event_type"] == "order_cancel"
    assert audit["actor"] == "varga.orsolya"      # any staff, but named
    assert "rossz PD" in audit["payload"]
    assert store.load(o.order_id).status is OrderStatus.LEMONDVA
    assert o3.cancel_reason == "rossz PD"


def test_store_id_collision_fails_loud_not_merge():
    # F-W3-02: the ids.py sequence race must surface as an error, never as
    # two orders sharing one revision chain.
    store = InMemoryOrderStore()
    store.save(order(), actor="a", expect_new=True)
    other = order(order_id="SZP-2607-0001")   # same id, fresh content
    import dataclasses
    other = dataclasses.replace(other, due_date="2026-07-25")
    with pytest.raises(OrderError, match="already exists"):
        store.save(other, actor="b", expect_new=True)
    assert len(store._revs["SZP-2607-0001"]) == 1


def test_store_refuses_cancel_without_reason_row():
    import dataclasses
    store = InMemoryOrderStore()
    bad = dataclasses.replace(order(), status=OrderStatus.LEMONDVA,
                              cancel_reason=None)
    with pytest.raises(OrderError):
        store.save(bad, actor="x")


# ----------------------------------------------------------- promotions (R13)
def test_first_sale_registers_once_and_digest_lists_pending():
    reg = InMemoryPromotionRegistry(now_fn=counter_clock())
    o = order()
    new = register_first_sale(reg, o)
    assert [r.sku for r in new] == ["HOY-NLX-160-HMC-70",
                                    "HOY-NLX-150-HMC-70"]
    assert all(r.status == "pending" and r.tharanis_cikksz is None
               for r in new)
    # second sale of the same SKUs: nothing new (idempotent)
    assert register_first_sale(reg, order(order_id="SZP-2607-0002")) == []
    digest = daily_digest(reg.rows(), "2026-07-18")
    assert "HOY-NLX-160-HMC-70" in digest and "SZP-2607-0001" in digest
    assert "F-W3-01" in digest                    # auto-create blocked note
    assert "Nincs függőben" in daily_digest([], "2026-07-18")


# ------------------------------------------------------------------ BQ serde
def ddl_orders_columns():
    """Parse DDL 003 (same F-W2-05 discipline as quotes): fails when the DDL
    or the serializer changes without the other."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    field = re.compile(r"\b([a-z_][a-z0-9_]*)\s+"
                       r"(?:STRING|INT64|NUMERIC|BOOL|DATE|TIMESTAMP|JSON|"
                       r"FLOAT64)\b")
    ddl = (root / "infra/ddl/003_w3_orders.sql").read_text()
    block = re.search(r"CREATE TABLE `szempont\.orders` \((.*?)\n\)",
                      ddl, re.S).group(1)
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
    return cols, struct


def test_order_bq_row_matches_ddl_and_roundtrips():
    o = cancel_order(order(), reason="teszt lemondás")
    row = to_bq_row(o)
    cols, struct = ddl_orders_columns()
    assert set(row) == cols
    assert set(row["lines"][0]) == struct
    assert row["total_retail_gross"] == str(
        order_totals(o).total_retail_gross)
    assert from_bq_row(row) == o                  # lossless roundtrip


def test_status_hu_covers_every_status():
    assert set(STATUS_HU) == set(OrderStatus)
    assert set(LENS_SOURCES) == {"rendeles", "keszlet"}
