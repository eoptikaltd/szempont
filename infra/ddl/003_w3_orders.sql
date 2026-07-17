-- Szempont W3 DDL 003 (2026-07-18) — M4 orders per Mega Review rulings.
-- Fresh dataset: run 001, 002, 003. Existing staging: run 003 only.
-- Run from laptop as named user; every job labeled tool=szempont.
--
-- Replaces the 001 stubs for `orders` (was a Unas-id mirror — terminology
-- ruling 2026-07-18: Unas is webshop-only, NOT in the store-order loop; the
-- ERP is Tharanis) and `sku_promotions` (unas_product_id -> tharanis_cikksz,
-- R13). Adds `order_events` (eseménynapló).

-- ============================================================================
-- !! DESTRUCTIVE PATH — ONLY VALID WHILE BOTH TABLES ARE EMPTY !!
-- (true pre-launch: staging has never stored an order or a promotion row).
-- Guarded like 002: aborts if any row exists. Once real orders land, this
-- file is dead — further changes must be copy-and-swap migrations.
-- ============================================================================
IF EXISTS (SELECT 1 FROM `szempont.orders` LIMIT 1) THEN
  RAISE USING MESSAGE =
    'szempont.orders is NOT empty — refusing drop-and-recreate. '
    || 'Write a copy-and-swap migration instead of rerunning 003.';
END IF;
IF EXISTS (SELECT 1 FROM `szempont.sku_promotions` LIMIT 1) THEN
  RAISE USING MESSAGE =
    'szempont.sku_promotions is NOT empty — refusing drop-and-recreate.';
END IF;

DROP TABLE IF EXISTS `szempont.orders`;
DROP TABLE IF EXISTS `szempont.sku_promotions`;

-- Orders: append-only revisions like quotes (readers QUALIFY latest).
-- Reads MUST use:
--   QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id
--                              ORDER BY IFNULL(revision,0) DESC) = 1
CREATE TABLE `szempont.orders` (
  order_id STRING NOT NULL,             -- SZP-YYMM-NNNN (R4, Szempont mints)
  legacy_order_id STRING,               -- R18: migrated ClearVisio SO- id
  quote_id STRING NOT NULL,             -- the converted quote (reproducibility)
  catalog_version STRING NOT NULL,      -- carried from the quote
  order_date DATE NOT NULL,
  person_id STRING,                     -- IRIS id or Z1 token (rule 4)
  status STRING NOT NULL,               -- felvett|megrendelve|beerkezett|
                                        -- csiszolas|kesz|qc_kesz (R10)|
                                        -- atadva|lemondva (R7: audited)
  lines ARRAY<STRUCT<                   -- copy of the quote's non-removed lines
    line_type STRING,                   -- frame|lens|option|service|discount
    sku STRING, name STRING,
    qty INT64, unit_retail_net NUMERIC,
    auto_added BOOL, removed BOOL,
    source STRING>>,
  payer_type STRING,                    -- D1 payer block, copied from quote
  payer_name STRING,
  payer_member_name STRING,
  payer_member_id STRING,
  payer_billing_address STRING,
  vat_rate NUMERIC NOT NULL,
  total_retail_net NUMERIC, total_retail_gross NUMERIC,
  discount_net NUMERIC, discount_config_id STRING, discount_approved_by STRING,
  lens_source STRING NOT NULL,          -- rendeles|keszlet (parity checklist)
  due_date DATE NOT NULL,               -- vállalt határidő (munkalap)
  channel STRING NOT NULL,              -- 'store-terez50'
  munkalap_gcs_uri STRING,              -- R11 (W3-3, gs://szempont-docs)
  tharanis_sorszam STRING,              -- set ONLY by a verified live berak
                                        -- (F-W3-01 follow-up + tripwire)
  cancel_reason STRING,                 -- R7: mandatory when lemondva
  revision INT64 NOT NULL,
  saved_at TIMESTAMP,
  created_by STRING NOT NULL,           -- current_operator() (M5 seam)
  created_at TIMESTAMP NOT NULL
) PARTITION BY order_date
  OPTIONS (labels = [("tool", "szempont")]);

-- Eseménynapló: append-only, one row per meaningful order event; the order
-- detail page renders this verbatim. Cancels ALSO write szempont.audit_log
-- (R7) — this table is the human-facing trail, audit_log is the control one.
CREATE TABLE IF NOT EXISTS `szempont.order_events` (
  event_id STRING NOT NULL,
  order_id STRING NOT NULL,
  event_type STRING NOT NULL,           -- created|status|cancel|
                                        -- tharanis_dry_run|promotion|note
  actor STRING NOT NULL,
  occurred_at TIMESTAMP NOT NULL,
  note STRING,                          -- Hungarian, UI-rendered
  payload STRING                        -- JSON detail (dry-run XML, from/to…)
) PARTITION BY DATE(occurred_at)
  OPTIONS (labels = [("tool", "szempont")]);

-- R13 first-sale promotion registry: rows are born 'pending' on first sale;
-- automated Tharanis article-create is OFF until F-W3-01's "berak verified"
-- follow-up — the daily digest surfaces pending rows for the manual path.
CREATE TABLE `szempont.sku_promotions` (
  sku STRING NOT NULL,
  catalog_version STRING NOT NULL,
  first_sale_order_id STRING NOT NULL,
  registered_at TIMESTAMP NOT NULL,
  status STRING NOT NULL,               -- pending|created|failed
  tharanis_cikksz STRING                -- set on verified article-create only
) OPTIONS (labels = [("tool", "szempont")]);
