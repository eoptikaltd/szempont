"""Tharanis adapter tests — dry-run only, live hard-blocked (R1/F-W3-01)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tests.test_orders import order
from vendors.tharanis import (TharanisOrderSink, TharanisWriteBlocked,
                              build_berak_order_xml, fmt_date_dot)


def test_berak_xml_carries_order_and_escapes():
    import dataclasses
    from quotes.records import QuoteLineRec
    from decimal import Decimal as D
    o = order()
    o = dataclasses.replace(o, lines=o.lines + (
        QuoteLineRec("service", None, 'Vésés <"különleges" & éles>', 1,
                     D("1000")),))
    xml = build_berak_order_xml(o, customer_name="Kovács & Fia",
                                customer_email="k@example.com")
    assert "<hivszam>SZP-2607-0001</hivszam>" in xml
    assert "<kelt>2026.07.18</kelt>" in xml
    assert "<kert_telj>2026.07.21</kert_telj>" in xml
    assert "<cikksz>HOY-NLX-160-HMC-70</cikksz>" in xml
    assert "Kovács &amp; Fia" in xml              # entity-escaped, F-W3-01
    assert 'Vésés &lt;"különleges" &amp; éles&gt;' in xml
    assert "CDATA" not in xml                     # values escaped, never CDATA
    from xml.etree import ElementTree
    ElementTree.fromstring(xml)                   # well-formed despite hostiles


def test_dry_run_returns_xml_never_sends():
    sink = TharanisOrderSink(mode="dry_run")
    out = sink.send(order())
    assert out["sent"] is False and out["mode"] == "dry_run"
    assert "<berak>" in out["xml"]


def test_off_and_live_both_refuse():
    with pytest.raises(TharanisWriteBlocked):
        TharanisOrderSink(mode="off").send(order())
    with pytest.raises(TharanisWriteBlocked, match="F-W3-01"):
        TharanisOrderSink(mode="live").send(order())
    with pytest.raises(ValueError):
        TharanisOrderSink(mode="yolo")


def test_discount_and_removed_lines_stay_out_of_tetelek():
    import dataclasses
    from decimal import Decimal as D
    from quotes.records import QuoteLineRec
    o = order()
    o = dataclasses.replace(o, lines=o.lines + (
        QuoteLineRec("discount", "TORZS10", "Törzsvásárlói 10%", 1,
                     D("-1000"), source="config"),
        QuoteLineRec("service", None, "Törölt tétel", 1, D("500"),
                     removed=True)))
    xml = build_berak_order_xml(o)
    assert "Törzsvásárlói" not in xml             # discounts ride in totals
    assert "Törölt tétel" not in xml


def test_fmt_date_dot():
    assert fmt_date_dot("2026-07-18") == "2026.07.18"
