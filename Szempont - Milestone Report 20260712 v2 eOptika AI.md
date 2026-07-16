# Szempont - Milestone Report 20260712 v2 eOptika AI

**Supersedes v1.** Covers the M1 rework after today's ruling plus the Atlas UI integration.

## Ruling applied (2026-07-12)

Szempont never parses FS6/SF6. The sf6-converter project (`eoptikaltd/sf6-converter`, package `sf6gen` — per the "FS6 converter" chat: two-way BQ↔SF6 6.10.x, validated on 8 real catalogues) owns the format; Szempont consumes its BigQuery output. CLAUDE.md hard rule 8 rewritten accordingly; FS6 adapter/wrapper code deleted from this repo. The uploaded sample catalogues (EOP--HU-HU-20260712-1 + 6 manufacturer files) are converter-project fixtures, not Szempont inputs.

## Verified live against BigQuery (read-only, tool=szempont)

`sf6_catalog_converter.pl_items_enriched`: 1,111 EyeTech SKUs — ETBIA 354 / ETBIS 229 / ETBLA 292 / ETBLS 236; one row per real power SKU (sph/cyl/dia on the row — hard rule 9 holds by construction); 2 quarantined ETBLA rows excluded at source; 352 dormant flagged. Data facts encoded in tests: `|0000` zero-power SKU grammar (counted, not warned), SHMC-in-SKU vs HMC-in-coating_code label split, negative-cylinder convention.

## What shipped (rev 2)

1. **M1 = catalog sync**: `CatalogSource` protocol; `BQEyeTechSource` over the converter view; `run_sync` → flat `szempont.lens_catalog`, content-addressed `catalog_version` (hash of canonical row set — order-independent), idempotent delete-then-batch-load; health report: per-family counts, price deltas vs previous version, dormant share, price/charset warnings.
2. **Finder resolves Rx → exact SKUs**: per-power rows map to degenerate Rx ranges; a prescription returns exactly the orderable SKUs.
3. **App live mode**: `SZEMPONT_CATALOG=bq` reads latest synced version (falls back to the converter view pre-first-sync); demo fixture retained for local dev. Margin/cost render as "–" while `cost_net_huf`=0 — no fake 100% margins.
4. **Atlas UI** (from v2 package): finder = list_monitor, quote = detail_view, contract classes only.
5. **Tests: 23/23** — sync idempotency, order-independent versioning, health-report semantics on live-shaped fixtures, real-SKU pricing through the engine (3 543 Ft × 2 × 1.27 = 8 999 Ft gross), exact-power search, UI routes, diacritics.

## Decisions for Sabie

1. **COGS for margin** — `cost_net_huf` is 0. (a) Join per-SKU COGS from `new_kpi_system` in the sync job — recommended (b) family-level standard cost (c) leave margin blank at launch.
2. **Dormant SKUs in finder** — currently included, no marking. (a) Include with a muted "dormant" pill — recommended (b) exclude (c) include silently.
3. **SHMC vs HMC label** (open since converter sprint) — affects Szempont display only; converter owns the data fix.
4. **Sync cadence** — (a) nightly Cloud Scheduler after converter refresh — recommended (b) manual until parallel-run.

## Outstanding

Third-party (Hoya etc.) catalogues: converter imports them to BQ first; Szempont then adds a CatalogSource — no Szempont work until that lands. Surcharges/options for PL lenses: none priced in BQ yet; engine supports them when they exist.
