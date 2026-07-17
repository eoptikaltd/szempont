-- Szempont W2 DDL v3 (2026-07-17) — schema migration per Sabie's frozen rulings.
-- Fresh dataset: run 001 then 002. Existing staging dataset: run 002 only.
-- Run from laptop as named user; tool=szempont.
--
-- v3 rewrite: v2 tried `ALTER TABLE ... ADD COLUMN IF NOT EXISTS lines.source`,
-- which is not valid BigQuery — ADD COLUMN cannot address a field inside an
-- existing STRUCT, and ALTER COLUMN ... SET DATA TYPE cannot add struct fields
-- either. The quotes migration is therefore a drop-and-recreate carrying the
-- full final schema, guarded so it can never destroy data.

-- ============================================================================
-- !! DESTRUCTIVE PATH — ONLY VALID WHILE `szempont.quotes` IS EMPTY !!
-- (true pre-launch: staging has never stored a quote). The guard below aborts
-- the whole script if any row exists. The moment real quotes land, this file
-- is dead: a further schema change must be a copy-and-swap migration
-- (CREATE new + INSERT ... SELECT + swap), never a rerun of this DROP.
-- ============================================================================
IF EXISTS (SELECT 1 FROM `szempont.quotes` LIMIT 1) THEN
  RAISE USING MESSAGE =
    'szempont.quotes is NOT empty — refusing drop-and-recreate. '
    || 'Write a copy-and-swap migration instead of rerunning 002.';
END IF;

DROP TABLE IF EXISTS `szempont.quotes`;

-- Full final W2 schema = 001 base plus:
--   lines.source          — wave-gate fix 2026-07-16 (discount provenance)
--   discount_config_id    — Ruling 7 (D3 curated discounts)
--   offer_set_id, variant_label — Ruling 8 (D6 offer variants)
--   revision, saved_at    — D2 append-only quote revisions
CREATE TABLE `szempont.quotes` (
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
    removed BOOL,                       -- ...but optician may edit/remove any line
    -- Wave-gate fix (2026-07-16): discount lines declare their provenance —
    -- 'config'   = D3 curated discount (quote.discount_config_id required);
    -- 'override' = lens_price_overrides akciós ár (lines.sku = override_id).
    source STRING>>,
  -- D1 (2026-07-16): egeszsegpenztar / payer support
  payer_type STRING,                    -- person|health_fund
  payer_name STRING,                    -- e.g. 'OTP Egeszsegpenztar'
  payer_member_name STRING,
  payer_member_id STRING,
  payer_billing_address STRING,
  vat_rate NUMERIC NOT NULL,
  total_retail_net NUMERIC, total_retail_gross NUMERIC,
  discount_net NUMERIC, discount_approved_by STRING,   -- permission gating (M2/M5)
  -- Ruling 7 (D3): a quote's discount always references the curated config
  -- that produced it — free-form discounts are not representable.
  discount_config_id STRING,
  -- Ruling 8 (D6): variants shown in the quote carousel share one
  -- offer_set_id; each variant is a full, independently reproducible quote row.
  offer_set_id STRING,
  variant_label STRING,                 -- 'Alap' | 'Ajánlott' | 'Prémium' | custom
  -- Editable quotes (D2) are stored as append-only revisions — the house
  -- pattern (cf. unas_data.raw_orders). Readers MUST dedup:
  --   QUALIFY ROW_NUMBER() OVER (
  --       PARTITION BY quote_id ORDER BY IFNULL(revision, 0) DESC) = 1
  -- revision is NULL on pre-v2 rows (= revision 0); created_at stays the first
  -- save, saved_at is the write time of each revision.
  revision INT64,
  saved_at TIMESTAMP,
  created_by STRING, created_at TIMESTAMP NOT NULL,
  converted_order_id STRING
) PARTITION BY quote_date
  OPTIONS (labels = [("tool", "szempont")]);

-- Ruling 7 (D3): curated structured discount configs — the ONLY source of
-- discounts in Szempont. Effective-dated; approval-gated configs require
-- discount_approved_by on the quote and land in szempont.audit_log.
-- UI wiring is W2 item 2; schema + engine application land in item 1.
CREATE TABLE IF NOT EXISTS `szempont.discount_configs` (
  config_id STRING NOT NULL,
  name STRING NOT NULL,                 -- display, e.g. 'Törzsvásárlói 10%'
  kind STRING NOT NULL,                 -- percent | amount_net
  value NUMERIC NOT NULL,               -- percent: 0–100; amount_net: HUF (net)
  applies_to_line_types ARRAY<STRING>,  -- empty/NULL = whole basket (frame|lens|option|service)
  requires_approval BOOL NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE,                        -- NULL = open-ended (effective-dated)
  active BOOL NOT NULL,
  created_by STRING, created_at TIMESTAMP NOT NULL
) OPTIONS (labels = [("tool", "szempont")]);
