"""Pair (OD/OS) lens finding — research-driven addition, 2026-07-12.

Competitor research (Glasson Lens Finder, ClearVis ajánlat flow, US optical
POS) converges on one pattern: the entry form mirrors the paper prescription
pad — a right-eye row and a left-eye row. With a per-power SKU catalog, a
"pair" is therefore usually TWO DIFFERENT SKUs of the same lens family.

find_pair_options groups per-power SKUs into families (supplier + famcode +
index + diameter + coating + blue/photochromic) and returns every family in
which BOTH eyes' exact powers exist, priced as R-SKU + L-SKU (qty 1 each),
margin-sorted. Pure function over the snapshot — reproducibility preserved.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .engine import PricingError, price_quote
from .models import CatalogSnapshot, LensProduct, QuoteRequest


@dataclass(frozen=True)
class EyeRx:
    sph: Decimal
    cyl: Decimal = Decimal("0")
    add: Decimal = Decimal("0")


@dataclass(frozen=True)
class PairOption:
    family_key: str
    family_name: str          # display: family portion of the lens name
    supplier: str
    index: Decimal
    diameter_mm: int
    right: LensProduct
    left: LensProduct
    pair_retail_net: Decimal
    pair_retail_gross: Decimal
    rank_score: Decimal
    right_dormant: bool = False
    left_dormant: bool = False


def _family_key(l: LensProduct) -> str:
    return "|".join([l.supplier, l.supplier_code, str(l.index),
                     str(l.diameter_mm), l.coating_tier.value,
                     str(l.photochromic)])


def _covers(l: LensProduct, rx: EyeRx) -> bool:
    return l.rx_range.covers(rx.sph, rx.cyl, rx.add)


def find_pair_options(
    snapshot: CatalogSnapshot,
    od: EyeRx,                      # right eye
    os_: EyeRx,                     # left eye
    quote_date: str,
    option_codes: frozenset[str] = frozenset(),
) -> list[PairOption]:
    families: dict[str, dict[str, LensProduct]] = {}
    for lens in snapshot.lenses.values():
        if option_codes and not option_codes <= set(lens.available_surcharges):
            continue
        fam = families.setdefault(_family_key(lens), {})
        if _covers(lens, od) and "R" not in fam:
            fam["R"] = lens
        # same SKU may cover both eyes (identical Rx) — that's fine
        if _covers(lens, os_) and "L" not in fam:
            fam["L"] = lens

    out: list[PairOption] = []
    for key, fam in families.items():
        if "R" not in fam or "L" not in fam:
            continue
        r, l = fam["R"], fam["L"]
        try:
            qr = price_quote(snapshot, QuoteRequest(
                sku=r.sku, option_codes=option_codes,
                quote_date=quote_date, quantity=1))
            ql = price_quote(snapshot, QuoteRequest(
                sku=l.sku, option_codes=option_codes,
                quote_date=quote_date, quantity=1))
        except PricingError:
            # D5: a family whose mandatory choice group is unsatisfied by the
            # selected options cannot be priced — it is not a candidate.
            continue
        out.append(PairOption(
            family_key=key,
            family_name=r.name.split(", SPH")[0] if ", SPH" in r.name else r.name,
            supplier=r.supplier, index=r.index, diameter_mm=r.diameter_mm,
            right=r, left=l,
            pair_retail_net=qr.total_retail_net + ql.total_retail_net,
            pair_retail_gross=qr.total_retail_gross + ql.total_retail_gross,
            rank_score=max(r.rank_score, l.rank_score),
            right_dormant=r.is_dormant, left_dormant=l.is_dormant,
        ))

    out.sort(key=lambda p: (-p.rank_score, p.pair_retail_net, p.right.sku))
    return out
