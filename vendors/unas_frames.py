"""Frame search — Unas webshop is the frame catalog master (W2 item 2).

Hard rule 2: the vendor sits behind the FrameSource adapter — the quote UI
only ever sees Frame objects. Hard rule 7: this module is READ-ONLY against
Unas (product search); no writes of any kind.

DemoFrameSource backs local dev and tests. UnasFrameSource speaks the Unas
API v2 (XML over HTTPS): login with the API key -> token, then getProduct
filtered on the search string. The XML build/parse steps are pure module
functions so the wire format is unit-testable without network or creds.

Config (staging): UNAS_API_KEY from Secret Manager via env — zero
credentials in the repo.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from xml.etree import ElementTree

UNAS_API_URL = "https://api.unas.eu/shop"


@dataclass(frozen=True)
class Frame:
    """One sellable frame as the quote's frame line consumes it (net HUF,
    consistent with the lens catalog money convention A1). ean: 12/13-digit
    GTIN when the shop carries one — the munkalap prints it as EAN-13."""
    sku: str
    name: str
    retail_net: Decimal
    ean: str | None = None


class FrameSource(Protocol):
    def search(self, query: str) -> list[Frame]: ...

    def get(self, sku: str) -> Frame | None: ...


def _norm(s: str) -> str:
    """Accent-stripped lowercase (hard rule 10: accent-stripped forms are
    equivalent to canonical ones)."""
    decomposed = unicodedata.normalize("NFD", s.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


class DemoFrameSource:
    """Fixture-backed source for dev/tests; accent-insensitive substring
    match on sku and name, deterministic order."""

    def __init__(self, frames: tuple[Frame, ...] = ()):
        self._frames = frames or DEMO_FRAMES

    def search(self, query: str) -> list[Frame]:
        q = _norm(query.strip())
        if not q:
            return []
        return [f for f in self._frames
                if q in _norm(f.sku) or q in _norm(f.name)]

    def get(self, sku: str) -> Frame | None:
        return next((f for f in self._frames if f.sku == sku), None)


DEMO_FRAMES = (
    Frame("FRM-RB-5228", "Ray-Ban RB5228 fekete keret", Decimal("39000"),
          ean="599811241152"),
    Frame("FRM-RB-7047", "Ray-Ban RB7047 matt kék keret", Decimal("34500"),
          ean="599811270474"),
    Frame("FRM-OAK-8156", "Oakley OX8156 Holbrook RX keret", Decimal("42900"),
          ean="599811281563"),
    Frame("FRM-EO-CLASS-01", "eOptika Classic 01 acél keret", Decimal("14900")),
    Frame("FRM-EO-KONNYU-02", "eOptika Könnyű 02 titán keret", Decimal("19900")),
)


# ------------------------------------------------------- Unas wire format
def build_search_xml(token: str, query: str, limit: int = 20) -> str:
    """getProduct request filtered on the search string (name/SKU)."""
    root = ElementTree.Element("Params")
    ElementTree.SubElement(root, "AuthCode").text = token
    ElementTree.SubElement(root, "Search").text = query
    ElementTree.SubElement(root, "LimitNum").text = str(limit)
    ElementTree.SubElement(root, "ContentType").text = "minimal"
    return ElementTree.tostring(root, encoding="unicode")


def parse_products_xml(xml_text: str) -> list[Frame]:
    """<Products><Product><Sku>..<Name>..<Prices><Price><Type>normal</Type>
    <Net>..</Net>... -> Frames. Products without a normal net price are
    skipped (not quotable)."""
    out: list[Frame] = []
    root = ElementTree.fromstring(xml_text)
    for prod in root.iter("Product"):
        sku = prod.findtext("Sku")
        name = prod.findtext("Name")
        net = None
        for price in prod.iter("Price"):
            if (price.findtext("Type") or "normal") == "normal":
                net = price.findtext("Net")
                break
        if not sku or not name or net is None:
            continue
        out.append(Frame(sku=sku, name=name, retail_net=Decimal(net),
                         ean=(prod.findtext("Ean") or None)))
    return out


class UnasFrameSource:  # pragma: no cover — needs UNAS_API_KEY, staging only
    """Read-only Unas API v2 client. Token fetched lazily per instance."""

    def __init__(self, api_key: str, api_url: str = UNAS_API_URL):
        self._api_key = api_key
        self._api_url = api_url
        self._token: str | None = None

    def _post(self, endpoint: str, xml: str) -> str:
        import urllib.request
        req = urllib.request.Request(
            f"{self._api_url}/{endpoint}", data=xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")

    def _login(self) -> str:
        if self._token is None:
            body = (f"<Params><ApiKey>{self._api_key}</ApiKey>"
                    f"<WebshopInfo>false</WebshopInfo></Params>")
            root = ElementTree.fromstring(self._post("login", body))
            token = root.findtext("Token")
            if not token:
                raise RuntimeError("Unas login failed: no token in response")
            self._token = token
        return self._token

    def search(self, query: str) -> list[Frame]:
        return parse_products_xml(
            self._post("getProduct", build_search_xml(self._login(), query)))

    def get(self, sku: str) -> Frame | None:
        hits = [f for f in self.search(sku) if f.sku == sku]
        return hits[0] if hits else None
