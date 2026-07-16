# M2 pricing semantics — assumptions pending Execution Spec v2 reconciliation

The Execution Spec v2 docx was NOT in this build's inputs. These assumptions
are implemented and tested; each is a one-line change if spec says otherwise.

| # | Assumption | Where |
|---|---|---|
| A1 | Catalog prices stored NET HUF; VAT 27% applied at quote; gross rounded to whole HUF, ROUND_HALF_UP, at final step only | engine.py |
| A2 | Combo override = exact (sku, option-set) match; REPLACES computed net retail; cost never overridden | engine.py |
| A3 | If several overrides active on quote date, most recent valid_from wins | engine.py `_resolve_override` |
| A4 | valid_from/valid_to inclusive on both ends | models.PriceOverride |
| A5 | Default quantity = 2 (pair) | models.QuoteRequest |
| A6 | Search results sorted by unit margin desc, sku tiebreak | search.py |
| A7 | catalog_version content-addressed: supplier + sha256[:12] of ZIP | job.py |
| A8 | VAT rate stored per CatalogSnapshot so historical quotes survive VAT changes | models.CatalogSnapshot |
