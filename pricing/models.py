"""Szempont M2 pricing engine — domain models.

All models are frozen (immutable) dataclasses. The engine is pure: given the
same CatalogSnapshot (identified by catalog_version) and the same QuoteRequest,
it MUST produce an identical Quote. This is the quote-reproducibility
acceptance criterion (spec §3.1 W1).

Money convention (ASSUMPTION pending Execution Spec v2 reconciliation):
  - All catalog prices are stored NET (VAT-exclusive) in HUF.
  - Decimal throughout; rounding to whole HUF (ROUND_HALF_UP) happens only at
    the final gross figure, never on intermediate values.
  - Costs are net supplier cost in HUF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Mapping


class CoatingTier(StrEnum):
    NONE = "none"
    HARD = "hard"
    HMC = "hmc"          # hard multi-coat / standard AR
    PREMIUM = "premium"  # top-tier AR (BlueControl, Hi-Vision class)


class LensDesign(StrEnum):
    SINGLE_VISION = "single_vision"
    BIFOCAL = "bifocal"
    PROGRESSIVE = "progressive"
    OFFICE = "office"       # computer / degressive
    LENTICULAR = "lenticular"


@dataclass(frozen=True, slots=True)
class RxRange:
    """Sphere/cylinder envelope a lens geometry can be made in."""
    sph_min: Decimal
    sph_max: Decimal
    cyl_min: Decimal = Decimal("0")
    cyl_max: Decimal = Decimal("0")
    add_min: Decimal = Decimal("0")
    add_max: Decimal = Decimal("0")

    def covers(self, sph: Decimal, cyl: Decimal = Decimal("0"),
               add: Decimal = Decimal("0")) -> bool:
        return (self.sph_min <= sph <= self.sph_max
                and self.cyl_min <= cyl <= self.cyl_max
                and self.add_min <= add <= self.add_max)


@dataclass(frozen=True, slots=True)
class Surcharge:
    """A priced option on top of a base lens (coating upgrade, tint,
    photochromic, prism, oversize diameter, ...).

    choice_group (D5, 2026-07-16): non-None marks a "Választandó Szolgáltatás" —
    when a lens offers surcharges from group G, a quote MUST select exactly one
    of them (ClearVis mandatory-choice chips, e.g. Crizal Sun vs e-mirror colors).
    """
    code: str
    name: str
    retail_net: Decimal
    cost_net: Decimal
    choice_group: str | None = None


@dataclass(frozen=True, slots=True)
class LensProduct:
    """One real, orderable lens variation. Hard rule 9: every variation gets
    its own real SKU — no generic SKUs."""
    sku: str
    supplier: str            # "hoya", "eyetech", "xcelens", ...
    supplier_code: str       # supplier's own article code from FS6
    name: str
    design: LensDesign
    index: Decimal           # refractive index, e.g. Decimal("1.60")
    diameter_mm: int
    coating_tier: CoatingTier
    photochromic: bool
    rx_range: RxRange
    base_retail_net: Decimal
    base_cost_net: Decimal
    available_surcharges: tuple[str, ...] = ()  # surcharge codes valid for this lens
    rank_score: Decimal = Decimal("0")  # precomputed recommendation rank (ruling
                                        # 2026-07-16: NO COGS/margin in Szempont;
                                        # ranking computed outside, higher = first
    is_dormant: bool = False            # ruling 10: still sellable, muted pill in UI


@dataclass(frozen=True, slots=True)
class PriceOverride:
    """Effective-dated combo override (szempont.lens_price_overrides).

    Matches a (sku, sorted-option-combo) pair. When active on the quote date,
    its retail_net REPLACES the computed list retail (base + surcharges).
    Cost is never overridden. ASSUMPTION pending spec v2: replace semantics,
    most-recently-effective override wins if several are active.
    """
    sku: str
    option_codes: frozenset[str]
    retail_net: Decimal
    valid_from: str   # ISO date, inclusive
    valid_to: str | None = None  # ISO date, inclusive; None = open-ended
    override_id: str = ""

    def active_on(self, quote_date: str) -> bool:
        if quote_date < self.valid_from:
            return False
        return self.valid_to is None or quote_date <= self.valid_to


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    """Immutable pricing universe for one catalog_version.

    The engine only ever sees this object — never a live table — which is what
    makes historical quotes reproducible: re-load the same catalog_version,
    re-run, get the identical Quote.
    """
    catalog_version: str
    lenses: Mapping[str, LensProduct]        # by sku
    surcharges: Mapping[str, Surcharge]      # by code
    overrides: tuple[PriceOverride, ...] = ()
    vat_rate: Decimal = Decimal("0.27")      # HU standard rate; per-snapshot so
                                             # historical quotes survive VAT changes


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    sku: str
    option_codes: frozenset[str] = frozenset()
    quote_date: str = ""      # ISO date; required for override resolution
    quantity: int = 2         # lenses come in pairs by default


@dataclass(frozen=True, slots=True)
class QuoteLine:
    code: str
    name: str
    retail_net: Decimal


@dataclass(frozen=True, slots=True)
class Quote:
    catalog_version: str
    sku: str
    quote_date: str
    quantity: int
    lines: tuple[QuoteLine, ...]
    override_applied: str | None      # override_id or None
    unit_retail_net: Decimal
    unit_cost_net: Decimal
    vat_rate: Decimal
    total_retail_net: Decimal
    total_vat: Decimal
    total_retail_gross: Decimal       # rounded to whole HUF
    total_cost_net: Decimal
    margin_net: Decimal               # total_retail_net - total_cost_net


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Parametric lens search (kickoff task 3)."""
    sph: Decimal
    cyl: Decimal = Decimal("0")
    add: Decimal = Decimal("0")
    design: LensDesign | None = None
    index_min: Decimal | None = None
    index_max: Decimal | None = None
    coating_tier: CoatingTier | None = None
    photochromic: bool | None = None
    diameter_mm: int | None = None
    suppliers: frozenset[str] = frozenset()   # empty = all


@dataclass(frozen=True, slots=True)
class SearchResult:
    lens: LensProduct
    quote: Quote
