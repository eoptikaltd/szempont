# Catalog source contract (rev 2 — ruling 2026-07-12)

Szempont never parses FS6/SF6. The sf6-converter project (eoptikaltd/sf6-converter,
package sf6gen) owns both directions of the SF6 format; its BigQuery output is
Szempont's input.

Production source: `sf6_catalog_converter.pl_items_enriched`
(EyeTech PL, 1,111 SKUs; one row = one real power SKU; view adds famcode,
price_huf = COALESCE(median 12m, latest), is_quarantined = price < 1000,
is_dormant = no 12m sales).

Szempont side: `ingest.source.CatalogSource` protocol → `run_sync` →
`szempont.lens_catalog` (flat, content-addressed catalog_version, idempotent).
Third-party catalogues (Hoya HHU-HUN etc.) arrive later the same way: the
converter imports them to BQ, Szempont adds a CatalogSource.

Known data facts (verified live 2026-07-12):
- SKU grammar uses `|0000` for ±0.00 powers where signed powers use +/-
  (e.g. ETLARS156SV-0200|000072SHMC). Counted in health report, not warned.
- coating_code = HMC while SKU/name embed SHMC — label decision open (Sabie).
- cost_net_huf is 0 pending COGS join — margin displayed as "–" until then.
- 2 quarantined ETBLA rows (price < 1000 HUF) are excluded at source.
