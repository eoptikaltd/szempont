"""Frame adapter tests (W2 item 2) — demo source semantics + Unas wire format.

The UnasFrameSource network client itself is staging-only; what is tested
here is everything it delegates to: accent handling (hard rule 10), the
request XML build, and the product-response parse.
"""

from decimal import Decimal as D

from vendors.unas_frames import (
    DemoFrameSource, Frame, build_search_xml, parse_products_xml,
)


def test_demo_search_is_accent_insensitive_both_directions():
    src = DemoFrameSource()
    accented = src.search("Könnyű")
    stripped = src.search("konnyu")
    assert [f.sku for f in accented] == ["FRM-EO-KONNYU-02"]
    assert accented == stripped                     # hard rule 10
    assert src.search("ray-ban") and all(
        "Ray-Ban" in f.name for f in src.search("ray-ban"))
    assert src.search("") == []
    assert src.search("nincs-ilyen") == []


def test_demo_get_by_sku():
    src = DemoFrameSource()
    f = src.get("FRM-RB-5228")
    assert f is not None and f.retail_net == D("39000")
    assert src.get("NOPE") is None


def test_build_search_xml_carries_token_query_limit():
    xml = build_search_xml("TOK123", "Ray-Ban", limit=5)
    assert "<AuthCode>TOK123</AuthCode>" in xml
    assert "<Search>Ray-Ban</Search>" in xml
    assert "<LimitNum>5</LimitNum>" in xml


def test_parse_products_xml_maps_normal_net_price_and_skips_unpriced():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Products>
      <Product>
        <Sku>FRM-X-1</Sku><Name>Próba Keret Zöld</Name>
        <Prices><Price><Type>normal</Type><Net>12500</Net><Gross>15875</Gross></Price></Prices>
      </Product>
      <Product>
        <Sku>FRM-X-2</Sku><Name>Ártalan keret</Name>
      </Product>
      <Product>
        <Sku>FRM-X-3</Sku><Name>Akciós keret</Name>
        <Prices>
          <Price><Type>sale</Type><Net>900</Net></Price>
          <Price><Type>normal</Type><Net>9900</Net></Price>
        </Prices>
      </Product>
    </Products>"""
    frames = parse_products_xml(xml)
    assert frames == [
        Frame("FRM-X-1", "Próba Keret Zöld", D("12500")),
        Frame("FRM-X-3", "Akciós keret", D("9900")),   # normal price, not sale
    ]
