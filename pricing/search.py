"""Szempont M2 — parametric lens search.

search(snapshot, query, quote_date, option_codes=...) returns candidate
lenses across suppliers whose Rx envelope covers the requested prescription
and whose attributes match the filters, each priced through the engine and
sorted by descending unit margin (kickoff task 3: "margin-sorted").

Lenses that cannot take one of the requested option codes are silently
skipped (they are not candidates for this configuration).
"""

from __future__ import annotations

from .engine import PricingError, price_quote, representative_options
from .models import (
    CatalogSnapshot,
    LensProduct,
    QuoteRequest,
    SearchQuery,
    SearchResult,
)


def _matches(lens: LensProduct, q: SearchQuery) -> bool:
    if not lens.rx_range.covers(q.sph, q.cyl, q.add):
        return False
    if q.design is not None and lens.design != q.design:
        return False
    if q.index_min is not None and lens.index < q.index_min:
        return False
    if q.index_max is not None and lens.index > q.index_max:
        return False
    if q.coating_tier is not None and lens.coating_tier != q.coating_tier:
        return False
    if q.photochromic is not None and lens.photochromic != q.photochromic:
        return False
    if q.diameter_mm is not None and lens.diameter_mm != q.diameter_mm:
        return False
    if q.suppliers and lens.supplier not in q.suppliers:
        return False
    return True


def search(
    snapshot: CatalogSnapshot,
    query: SearchQuery,
    quote_date: str,
    option_codes: frozenset[str] = frozenset(),
    quantity: int = 2,
) -> list[SearchResult]:
    results: list[SearchResult] = []
    for lens in snapshot.lenses.values():
        if not _matches(lens, query):
            continue
        if not option_codes <= set(lens.available_surcharges):
            continue  # can't be configured as requested
        # D5 (review fix 2026-07-16): unsatisfied mandatory groups priced by
        # their cheapest member -> candidate listed as a flagged from-price.
        rep_opts, rep = representative_options(snapshot, lens, option_codes)
        try:
            quote = price_quote(
                snapshot,
                QuoteRequest(
                    sku=lens.sku,
                    option_codes=rep_opts,
                    quote_date=quote_date,
                    quantity=quantity,
                ),
            )
        except PricingError:
            # backstop (e.g. two members of one group selected upstream)
            continue
        results.append(SearchResult(lens=lens, quote=quote,
                                    needs_configuration=rep))

    # Ordering (ruling 2026-07-16): precomputed rank_score desc (no margin data
    # in Szempont), then retail asc, then sku for determinism.
    results.sort(key=lambda r: (-r.lens.rank_score, r.quote.total_retail_net,
                                r.lens.sku))
    return results
