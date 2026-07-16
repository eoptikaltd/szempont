-- Szempont W2 DDL v2 (2026-07-16) — schema migration per Sabie's frozen rulings.
-- Fresh dataset: run 001 then 002. Existing staging dataset: run 002 only.
-- Every statement is idempotent. Run from laptop as named user; tool=szempont.

-- Ruling 8 (D6 offer variants): variants shown in the quote carousel share one
-- offer_set_id; each variant is a full, independently reproducible quote row.
ALTER TABLE `szempont.quotes`
  ADD COLUMN IF NOT EXISTS offer_set_id STRING;
ALTER TABLE `szempont.quotes`
  ADD COLUMN IF NOT EXISTS variant_label STRING;   -- 'Alap' | 'Ajánlott' | 'Prémium' | custom

-- Ruling 7 (D3 discounts): a quote's discount always references the curated
-- config that produced it — free-form discounts are not representable.
ALTER TABLE `szempont.quotes`
  ADD COLUMN IF NOT EXISTS discount_config_id STRING;

-- Editable quotes (D2: every line optician-editable) are stored as append-only
-- revisions — the house pattern (cf. unas_data.raw_orders). Readers MUST dedup:
--   QUALIFY ROW_NUMBER() OVER (
--       PARTITION BY quote_id ORDER BY IFNULL(revision, 0) DESC) = 1
-- revision is NULL on pre-v2 rows (= revision 0); created_at stays the first
-- save, saved_at is the write time of each revision.
ALTER TABLE `szempont.quotes`
  ADD COLUMN IF NOT EXISTS revision INT64;
ALTER TABLE `szempont.quotes`
  ADD COLUMN IF NOT EXISTS saved_at TIMESTAMP;

-- Wave-gate fix (2026-07-16): discount lines declare their provenance —
-- 'config'   = D3 curated discount (quote.discount_config_id required);
-- 'override' = lens_price_overrides akciós ár (lines.sku = override_id).
ALTER TABLE `szempont.quotes`
  ADD COLUMN IF NOT EXISTS lines.source STRING;

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
