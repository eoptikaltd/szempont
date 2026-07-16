"""Szempont M2 — pure pricing engine.

price_quote(snapshot, request) -> Quote

Resolution order (kickoff task 3):
  1. base lens retail (net)
  2. + each selected surcharge (net), validated against the lens's
     available_surcharges list
  3. combo override lookup: if an active override matches (sku, exact option
     combo) on quote_date, its retail_net REPLACES the computed net retail
  4. VAT applied at the snapshot's vat_rate; gross rounded to whole HUF
     (ROUND_HALF_UP) at the very end.

Cost = base cost + surcharge costs, never overridden.
Margin = total retail net - total cost net.

No I/O, no clock reads, no randomness: same snapshot + same request =
byte-identical Quote (reproducibility acceptance criterion).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import (
    CatalogSnapshot,
    PriceOverride,
    Quote,
    QuoteLine,
    QuoteRequest,
)


class PricingError(Exception):
    """Raised for unknown SKUs, invalid options, or missing quote_date."""


_HUF = Decimal("1")  # whole-forint rounding quantum


def _resolve_override(
    snapshot: CatalogSnapshot, sku: str, options: frozenset[str], quote_date: str
) -> PriceOverride | None:
    """Most-recently-effective active override for the exact combo wins."""
    candidates = [
        o for o in snapshot.overrides
        if o.sku == sku and o.option_codes == options and o.active_on(quote_date)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda o: (o.valid_from, o.override_id))


def representative_options(
    snapshot: CatalogSnapshot, lens, option_codes: frozenset[str]
) -> tuple[frozenset[str], bool]:
    """D5 finder helper (review fix 2026-07-16): a lens with mandatory choice
    groups must still be LISTABLE before configuration. For each offered
    group the selection does not satisfy, pick the cheapest member (code
    tiebreak) as a representative, so finders can show a from-price flagged
    as needs-configuration. The engine's exactly-one rule stays frozen —
    this only builds a representative selection for display pricing.

    Returns (augmented option set, needs_configuration).
    """
    groups: dict[str, list] = {}
    for code in lens.available_surcharges:
        sc = snapshot.surcharges.get(code)
        if sc is not None and sc.choice_group:
            groups.setdefault(sc.choice_group, []).append(sc)
    added: set[str] = set()
    for members in groups.values():
        if not any(m.code in option_codes for m in members):
            cheapest = min(members, key=lambda m: (m.retail_net, m.code))
            added.add(cheapest.code)
    return frozenset(option_codes) | added, bool(added)


def price_quote(snapshot: CatalogSnapshot, request: QuoteRequest) -> Quote:
    if not request.quote_date:
        raise PricingError("quote_date is required (ISO date)")
    if request.quantity < 1:
        raise PricingError("quantity must be >= 1")

    lens = snapshot.lenses.get(request.sku)
    if lens is None:
        raise PricingError(f"unknown SKU: {request.sku}")

    lines: list[QuoteLine] = [
        QuoteLine(code="base", name=lens.name, retail_net=lens.base_retail_net)
    ]
    unit_cost = lens.base_cost_net

    allowed = set(lens.available_surcharges)

    # D5 choice groups: if the lens offers any surcharge of group G, the quote
    # must select exactly one member of G.
    groups: dict[str, list[str]] = {}
    for code in lens.available_surcharges:
        sc = snapshot.surcharges.get(code)
        if sc is not None and sc.choice_group:
            groups.setdefault(sc.choice_group, []).append(code)
    for gname, members in groups.items():
        picked = [c for c in request.option_codes if c in members]
        if len(picked) != 1:
            raise PricingError(
                f"choice group {gname!r} requires exactly one of {sorted(members)}, "
                f"got {sorted(picked)}")

    for code in sorted(request.option_codes):  # sorted => deterministic lines
        if code not in allowed:
            raise PricingError(f"surcharge {code!r} not available for SKU {lens.sku}")
        s = snapshot.surcharges.get(code)
        if s is None:
            raise PricingError(f"surcharge {code!r} missing from catalog "
                               f"{snapshot.catalog_version}")
        lines.append(QuoteLine(code=s.code, name=s.name, retail_net=s.retail_net))
        unit_cost += s.cost_net

    list_retail_net = sum((l.retail_net for l in lines), Decimal("0"))

    override = _resolve_override(
        snapshot, request.sku, request.option_codes, request.quote_date
    )
    unit_retail_net = override.retail_net if override else list_retail_net

    qty = Decimal(request.quantity)
    total_retail_net = unit_retail_net * qty
    total_cost_net = unit_cost * qty
    total_gross = (total_retail_net * (1 + snapshot.vat_rate)).quantize(
        _HUF, rounding=ROUND_HALF_UP
    )
    total_vat = total_gross - total_retail_net

    return Quote(
        catalog_version=snapshot.catalog_version,
        sku=lens.sku,
        quote_date=request.quote_date,
        quantity=request.quantity,
        lines=tuple(lines),
        override_applied=override.override_id if override else None,
        unit_retail_net=unit_retail_net,
        unit_cost_net=unit_cost,
        vat_rate=snapshot.vat_rate,
        total_retail_net=total_retail_net,
        total_vat=total_vat,
        total_retail_gross=total_gross,
        total_cost_net=total_cost_net,
        margin_net=total_retail_net - total_cost_net,
    )
