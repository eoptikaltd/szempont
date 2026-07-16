"""Barcode rendering tests (W2 item 4b) — real EAN-13/Code-128 inline SVG."""

import pytest

from app.barcodes import code128_svg, ean13_fullcode, ean13_svg


def test_ean13_svg_is_inline_and_check_digit_recomputed():
    svg = ean13_svg("599811230091")
    assert svg.startswith("<svg")           # XML prolog + doctype stripped
    assert "<?xml" not in svg and "DOCTYPE" not in svg
    assert "5998112300918" in svg           # true check digit rendered
    # a wrong 13th digit can never print: it is recomputed from the first 12
    assert ean13_fullcode("5998112300917") == "5998112300918"
    assert '<rect' in svg


def test_ean13_accepts_formatted_input_and_rejects_short():
    assert "5998112300918" in ean13_svg("5 998112 30091 7")
    with pytest.raises(ValueError):
        ean13_svg("12345")


def test_code128_svg_renders_sku_text():
    svg = code128_svg("HOY-NLX-160-HMC-70")
    assert svg.startswith("<svg") and "HOY-NLX-160-HMC-70" in svg
    silent = code128_svg("SO-1604869D", write_text=False)
    assert silent.startswith("<svg") and "SO-1604869D" not in silent
    with pytest.raises(ValueError):
        code128_svg("   ")
