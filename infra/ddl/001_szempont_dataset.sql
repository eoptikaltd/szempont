-- Szempont W1 DDL (rev 2, 2026-07-12). Run from laptop as named user.
-- RULING: Szempont consumes converted catalog data from BigQuery
-- (sf6_catalog_converter.*, produced by eoptikaltd/sf6-converter).
-- No FS6 parsing in this codebase.
-- bq mk --dataset --location=EU --label=tool:szempont natural-caster-496309-j3:szempont

CREATE TABLE IF NOT EXISTS `szempont.lens_catalog` (
  catalog_version  STRING NOT NULL,   -- "<supplier>-<sha256[:12]>" of canonical row set
  supplier         STRING NOT NULL,   -- 'eyetech' now; hoya/xcelens later via new CatalogSource
  sku              STRING NOT NULL,   -- real per-power SKU (hard rule 9)
  famcode          STRING,            -- ETBIS/ETBIA/ETBLS/ETBLA
  name             STRING,
  sph FLOAT64, cyl FLOAT64, add_power FLOAT64,
  diameter_mm FLOAT64, refractive_index FLOAT64,
  design STRING, coating_code STRING, blue_filter BOOL,
  retail_net_huf FLOAT64,
  rank_score     FLOAT64,             -- precomputed recommendation rank; NO COGS in this dataset (ruling 2026-07-16)
  is_dormant BOOL,
  effective_from DATE NOT NULL,
  _ingested_at   TIMESTAMP NOT NULL
) PARTITION BY DATE(_ingested_at)
  CLUSTER BY supplier, famcode, sku
  OPTIONS (labels = [("tool", "szempont")]);

CREATE TABLE IF NOT EXISTS `szempont.lens_price_overrides` (
  override_id STRING NOT NULL,
  sku STRING NOT NULL,
  option_codes ARRAY<STRING>,      -- exact combo; empty array = bare lens
  retail_net NUMERIC NOT NULL,     -- REPLACES computed list retail
  valid_from DATE NOT NULL,
  valid_to DATE,                   -- NULL = open-ended (effective-dated)
  created_by STRING, created_at TIMESTAMP NOT NULL
) OPTIONS (labels = [("tool", "szempont")]);

CREATE TABLE IF NOT EXISTS `szempont.audit_log` (
  event_id STRING NOT NULL, event_type STRING NOT NULL,  -- discount|cancel|sku_promotion|override
  actor STRING, payload JSON, occurred_at TIMESTAMP NOT NULL
) PARTITION BY DATE(occurred_at)
  OPTIONS (labels = [("tool", "szempont")]);

-- ---- Spec §6 tables (added on spec reconciliation, 2026-07-12) -------------

CREATE TABLE IF NOT EXISTS `szempont.quotes` (
  quote_id STRING NOT NULL,
  catalog_version STRING NOT NULL,      -- reproducibility anchor
  quote_date DATE NOT NULL,
  person_id STRING,                     -- IRIS A-grade id or Z1 fallback token
  status STRING NOT NULL,               -- draft|saved|printed|converted|expired
  lines ARRAY<STRUCT<
    line_type STRING,                   -- frame|lens|option|service|discount (D2)
    sku STRING, name STRING,
    qty INT64, unit_retail_net NUMERIC,
    auto_added BOOL,                    -- D2: munkadij auto-added to basket...
    removed BOOL>>,                     -- ...but optician may edit/remove any line
  -- D1 (2026-07-16): egeszsegpenztar / payer support
  payer_type STRING,                    -- person|health_fund
  payer_name STRING,                    -- e.g. 'OTP Egeszsegpenztar'
  payer_member_name STRING,
  payer_member_id STRING,
  payer_billing_address STRING,
  vat_rate NUMERIC NOT NULL,
  total_retail_net NUMERIC, total_retail_gross NUMERIC,
  discount_net NUMERIC, discount_approved_by STRING,   -- permission gating (M2/M5)
  created_by STRING, created_at TIMESTAMP NOT NULL,
  converted_order_id STRING
) PARTITION BY quote_date
  OPTIONS (labels = [("tool", "szempont")]);

CREATE TABLE IF NOT EXISTS `szempont.orders` (          -- mirror of Unas IDs (M4)
  order_id STRING NOT NULL,             -- szempont id
  unas_order_key STRING,                -- join key to unas_data.raw_orders (dedup rule!)
  quote_id STRING,
  person_id STRING,
  channel STRING NOT NULL,              -- 'store-terez50'
  status STRING NOT NULL,
  munkalap_gcs_uri STRING,
  payment_method STRING, deposit_net NUMERIC,
  created_by STRING, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at)
  OPTIONS (labels = [("tool", "szempont")]);

CREATE TABLE IF NOT EXISTS `szempont.sku_promotions` (  -- M4 first-sale promotion registry
  sku STRING NOT NULL,
  catalog_version STRING NOT NULL,
  promoted_at TIMESTAMP NOT NULL,
  unas_product_id STRING,
  order_id STRING,                      -- the sale that triggered promotion
  status STRING NOT NULL                -- pending|created|failed
) OPTIONS (labels = [("tool", "szempont")]);

CREATE TABLE IF NOT EXISTS `szempont.invoices` (        -- M8
  invoice_id STRING NOT NULL, order_id STRING NOT NULL,
  szamlazz_number STRING, kind STRING NOT NULL,         -- invoice|storno|deposit|final
  gross NUMERIC, issued_at TIMESTAMP, status STRING
) OPTIONS (labels = [("tool", "szempont")]);

CREATE TABLE IF NOT EXISTS `szempont.stock_movements` ( -- M10 journal (Tharanis = master)
  movement_id STRING NOT NULL, sku STRING NOT NULL,
  movement_type STRING NOT NULL,        -- receive|sale|transfer_in|transfer_out|stocktake_adj
  qty NUMERIC NOT NULL, tharanis_ref STRING,
  occurred_at TIMESTAMP NOT NULL, recorded_by STRING
) PARTITION BY DATE(occurred_at)
  OPTIONS (labels = [("tool", "szempont")]);

-- ---- IRIS Z1 walk-in contract (approved 2026-07-16) -------------------------
CREATE TABLE IF NOT EXISTS `szempont.walkin_persons` (
  z1_token STRING NOT NULL,            -- 'Z1-<uuid>' — explicitly NOT a person_id
  display_name STRING,
  phone_raw STRING, email_raw STRING, birth_date DATE,
  ep_member BOOL, ep_fund_name STRING, ep_member_id STRING,  -- D1 capture at desk
  gdpr_signed BOOL, dm_ok BOOL,
  created_by STRING, created_at TIMESTAMP NOT NULL
) OPTIONS (labels = [("tool", "szempont")]);

CREATE TABLE IF NOT EXISTS `szempont.walkin_resolutions` (  -- written by IRIS
  z1_token STRING NOT NULL,
  person_id STRING NOT NULL,           -- canonical IRIS id
  resolved_at TIMESTAMP NOT NULL,
  resolution_kind STRING               -- matched|minted
) OPTIONS (labels = [("tool", "szempont")]);
