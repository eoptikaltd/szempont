-- Szempont W3 DDL 004 (2026-07-18) — M5 staff/PIN table (R6/R7).
-- Fresh dataset: run 001..004. Existing staging: run 004 only.
-- Run from laptop as named user; every job labeled tool=szempont.
--
-- Append-only revisions like quotes/orders. Reads MUST use:
--   QUALIFY ROW_NUMBER() OVER (PARTITION BY operator_id
--                              ORDER BY IFNULL(revision,0) DESC) = 1
--
-- PIN storage: PBKDF2-SHA256(200k) hex + per-member salt. PINs are
-- presence proof at the IAP-protected shared terminal, NOT passwords —
-- the app rate-limits attempts (5 misses -> 15 min lock). No plaintext
-- PIN ever lands anywhere.
--
-- Seeding (R7): the app seeds the eight members in code; staging runs the
-- INSERT below once so BQStaffStore sees the same roster.

CREATE TABLE IF NOT EXISTS `szempont.staff` (
  operator_id STRING NOT NULL,          -- 'bozo.klaudia' — audit actor id
  display_name STRING NOT NULL,
  roles ARRAY<STRING>,                  -- R7 vocabulary verbatim
  pin_hash STRING,                      -- NULL until first PIN set
  pin_salt STRING,
  active BOOL NOT NULL,
  revision INT64 NOT NULL,
  updated_at TIMESTAMP,
  updated_by STRING
) OPTIONS (labels = [("tool", "szempont")]);

-- R7 seed — run ONCE on an empty table.
INSERT INTO `szempont.staff`
  (operator_id, display_name, roles, active, revision, updated_at, updated_by)
SELECT * FROM UNNEST([
  STRUCT('valner.szabolcs' AS operator_id, 'Valner Szabolcs' AS display_name,
         ['Cégvezető'] AS roles, TRUE AS active, 0 AS revision,
         CURRENT_TIMESTAMP() AS updated_at, 'seed' AS updated_by),
  ('bozo.klaudia', 'Bozó Klaudia', ['Üzletvezető'], TRUE, 0,
   CURRENT_TIMESTAMP(), 'seed'),
  ('benyo.krisztina', 'Benyó Krisztina', ['Optometrista', 'Kontaktológus'],
   TRUE, 0, CURRENT_TIMESTAMP(), 'seed'),
  ('tall.krisztina', 'Táll Krisztina', ['Optometrista', 'Kontaktológus'],
   TRUE, 0, CURRENT_TIMESTAMP(), 'seed'),
  ('vithalm.zsofia', 'Vithalm Zsófia', ['Optikus'], TRUE, 0,
   CURRENT_TIMESTAMP(), 'seed'),
  ('almadi-bartha.mariann', 'Almádi-Bartha Mariann', ['Látszerész'], TRUE, 0,
   CURRENT_TIMESTAMP(), 'seed'),
  ('szabo.greti', 'Szabó Gréti', ['Látszerész'], TRUE, 0,
   CURRENT_TIMESTAMP(), 'seed'),
  ('varga.orsolya', 'Varga Orsolya', ['Bolti eladó'], TRUE, 0,
   CURRENT_TIMESTAMP(), 'seed')
])
WHERE NOT EXISTS (SELECT 1 FROM `szempont.staff` LIMIT 1);
