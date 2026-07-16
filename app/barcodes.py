"""Inline SVG barcodes for the print sheets (W2 item 4b).

python-barcode renders real, scanner-valid EAN-13 / Code-128 symbols; the
XML prolog is stripped so the fragment embeds inline in the design-frozen
print templates. Sizes are chosen to sit inside the boxes the CSS placeholder
stripes used to occupy — the layout itself is untouched.
"""

from __future__ import annotations

import re
from io import BytesIO

import barcode
from barcode.writer import SVGWriter

_DIGITS = re.compile(r"\D")


def _inline(symbol, options: dict) -> str:
    buf = BytesIO()
    symbol.write(buf, options=options)
    s = buf.getvalue().decode("utf-8")
    return s[s.index("<svg"):]


def ean13_svg(code: str, *, module_width: float = 0.2,
              module_height: float = 4.0, font_size: int = 6) -> str:
    """code: 12 or 13 digits (formatting ignored); the check digit is always
    recomputed by the library, so a wrong 13th digit can never print."""
    digits = _DIGITS.sub("", code)
    if len(digits) < 12:
        raise ValueError(f"EAN-13 needs 12+ digits, got {code!r}")
    sym = barcode.get("ean13", digits[:12], writer=SVGWriter())
    return _inline(sym, {
        "module_width": module_width, "module_height": module_height,
        "font_size": font_size, "text_distance": 1.0, "quiet_zone": 1.0,
    })


def code128_svg(text: str, *, module_width: float = 0.15,
                module_height: float = 4.0, font_size: int = 6,
                write_text: bool = True) -> str:
    if not text.strip():
        raise ValueError("Code-128 needs a non-empty value")
    sym = barcode.get("code128", text, writer=SVGWriter())
    return _inline(sym, {
        "module_width": module_width, "module_height": module_height,
        "font_size": font_size, "text_distance": 1.0, "quiet_zone": 1.0,
        "write_text": write_text,
    })


def ean13_fullcode(code: str) -> str:
    """13 digits with the true check digit (for human-readable display)."""
    return barcode.get("ean13", _DIGITS.sub("", code)[:12],
                       writer=SVGWriter()).get_fullcode()
