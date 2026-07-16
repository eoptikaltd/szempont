# Szempont — eOptika in-store POS

Replaces ClearVis.io at Teréz körút 50. Read `CLAUDE.md` first; authoritative
scope: Szempont Execution Spec v2 + Handover Brief (project files).

## Wave 1 (this state)
- `/ingest` — M1 rev 2 (ruling 2026-07-12): NO FS6 parsing here. `CatalogSource` adapter reads the sf6-converter's BigQuery output (`sf6_catalog_converter.pl_items_enriched`, 1,111 EyeTech per-power SKUs) → `szempont.lens_catalog`, content-addressed version, idempotent, health report (family counts, price deltas, dormant share, SKU-grammar checks).
- `/pricing` — M2 pure pricing engine + parametric search. No I/O, no clock: quote reproducibility by construction.
- `/tests` — 20 tests: pricing math, overrides, effective dating, VAT rounding, reproducibility, idempotency, health-report deltas, Hungarian diacritics.
- `/infra` — BQ DDL, ingest Dockerfile, staging deploy script.
- `/contracts` — assumed FS6 contract + pricing semantics table (reconcile vs spec v2).
- `/app` — W2 head start: Atlas-shell Flask app (list_monitor lens finder + detail_view quote) on the M2 engine; `SZEMPONT_CATALOG=demo` (fixture) or `bq` (live EyeTech data). Staging only.

## Dev
```
pip install -e ".[dev]" && pytest
```
