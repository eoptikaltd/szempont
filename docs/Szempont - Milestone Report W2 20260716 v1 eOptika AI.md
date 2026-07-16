# Szempont - Milestone Report W2 20260716 v1 eOptika AI

Wave 2 (M2 UI + M3, per spec §3.1 and the W2 build order in the Decisions Log
2026-07-16) is code-complete on `main`, adversarially reviewed, **not
deployed** — staging deploy is Sabie's laptop step after this review.
All 13 frozen rulings applied; **no deviations from the decisions log.**
Tests: **30 → 94**, all green locally. Commits are local to dev-box-2's clone
(sandbox holds no GitHub credentials) — see F-W2-08.

## 1. What shipped, per build-order item

**Item 1 — DDL v2 + quotes persistence** (`195eb52`, wave-gate fix included)
`infra/ddl/002_w2_rulings.sql`: quotes gain `offer_set_id`/`variant_label`
(D6), `discount_config_id` (D3), `revision`/`saved_at` (append-only revisions,
raw_orders QUALIFY dedup pattern), `lines.source` (discount provenance:
`config` | `override`); new `szempont.discount_configs` table (curated,
effective-dated, approval-gated). New `quotes/` package: pure record layer
(build from engine quotes + frame + services; D2 editable/auto-added/
soft-removed lines; D1 payer block + invoice-ready gate; D3 `apply_discount`;
D6 offer sets; draft→saved→printed→converted/expired machine; BQ serde) and
stores (in-memory + BQ batch-load, save-time invariants, discount audit
events). Totals always derived from lines; ROUND_HALF_UP whole-HUF gross at
the final step only (A1). Price-override deltas persist as auto-added
`source='override'` discount lines ("Akciós ár") so line sums always equal
engine totals.

**Item 2 — Finder/quote UI completion** (`2cc163a`, review fixes `0e4bfbb`)
Dormant SKUs: muted "alvó SKU" pill, per-eye (ruling 10); excluded from
customer-facing konzultáció tiers (confirmed as ruled). D5 choice groups:
one-of radio chip groups; families with unsatisfied mandatory groups list as
flagged from-prices via `representative_options` (cheapest member; engine's
exactly-one rule untouched). Frame line via Unas: `FrameSource` adapter
(hard rule 2) — demo source + read-only API v2 client, key via env/Secret
Manager, accent-insensitive search (rule 10). Curated discount configs on the
quote page; gated discounts audited with `auto_approved_pre_m5` marker on the
POST apply path only (never on render). Quote page renders through the item-1
record path.

**Item 3 — M3 on the IRIS contract** (`7b00d79`, review fixes `8bf9e16`)
`iris/` package: `PersonDirectory` over the two frozen views —
contract-faithful fixture + thin BQ adapter with env-configurable view names
(**publishing the views is a config change: `SZEMPONT_IRIS=bq` +
`IRIS_SEARCH_VIEW`/`IRIS_LOOKUP_VIEW`**). Normalizers per contract/rule 10
(accent-strip, payroll-prefix strip, digits-only phone, lowercase email).
Z1 walk-ins: `Z1-<uuid>` tokens (never person ids, rule 4), append-only
`walkin_persons`, read-time re-attribution through `walkin_resolutions` —
original rows never rewritten. `/ugyfel` search + walk-in capture (consent
flags persisted) that never blocks a sale; person chip threads finder → quote.
`current_operator()` is the single actor source everywhere (M5 seam).

**Item 4 — M2C W2-light + print routes** (`6f508de`)
Konzultáció per benchmark §4 W2-light only: tier selection, always-visible
sticky basket priced through the same record path as /quote, tint swatches
from the Szín catalog (hidden when the live snapshot carries no tints), honest
thickness bars; no questionnaire, no camera. Print routes wire the two
design-frozen sheets without layout changes; CSS placeholder stripes replaced
with real inline-SVG barcodes (python-barcode): Code-128 (order, lens SKUs),
EAN-13 (frame GTIN, check digit always recomputed). Exam sheet is pure
pass-through (hard rule 5), `?demo=1` for layout checks.

**Item 5 — this review + report** (wave-close commit).

## 2. Adversarial review findings (F-W2-nn)

| # | Seam | Finding | Resolution |
|---|---|---|---|
| F-W2-01 | Money path unity | Konzultáció basket rounded each line's gross independently — sum could drift from the once-rounded A1 total (proven: 3×10 Ft lines → naive 39 vs A1 38). | **Fixed.** `gross_line_allocation()` in `quotes/records.py` (largest-remainder, pro-rata by net) — every per-line-gross UI goes through it. Tests pin: allocation sums exactly to the A1 total (incl. discount + removed-line cases) and konzultáció total == quote page total for the same configuration. Quote/persistence/invoice already shared one path (`_preview_record` → `totals()`/`invoice_lines()`). |
| F-W2-02 | CSRF pre-M5 | `POST /quote/discount` and the walk-in POST were unprotected. IAP covers perimeter authN only — the IAP cookie rides along on cross-site POSTs; it stops neither CSRF nor XSS nor role checks (all M5). | **Fixed.** Same-origin guard on every POST (Origin/Referer netloc + `Sec-Fetch-Site: cross-site` → 403) plus one-time form tokens on both forms. Tests: hostile origin 403, same-origin 302, tokenless non-browser clients still work. |
| F-W2-03 | XSS via names | Reviewed all surfaces a name reaches (finder chip, quote, munkalap, exam sheet). Jinja autoescape is active on every template; the only `\|safe` usages are server-generated barcode SVGs. | **No defect.** Regression test pins it: a walk-in named `<script>alert(1)</script>Béla` renders escaped on all four surfaces. |
| F-W2-04 | Z1/GDPR — PII/health in logs & URLs | No PII in audit payloads (quote id, config id, amounts, operator only), none in app logs (no logging of user data anywhere; the one stdout write is the ingest health report — catalog counts). URLs carry only opaque Z1 tokens/person ids. BUT print routes took Rx via GET query — health data would land in Cloud Run request logs. `/ugyfel?q=` search terms in GET remain. | **Fixed** for the health-data path: both print routes accept POST (`request.values`); the future exam UI MUST POST — documented in the route docstring. Search-terms-in-GET is an **accepted risk** pre-M5 (IAP-gated, EU-resident logs); revisit with M5 logging config. Consent flags (`gdpr_signed`, `dm_ok`) verified flowing form → record → BQ row (tested). |
| F-W2-05 | Serialization drift | Column list in the serde test was hand-copied — silent drift possible. | **Fixed.** The test now parses `infra/ddl/001` + `002` (top-level columns AND the `lines` struct fields incl. `lines.source`) and compares against `to_bq_row` output; it fails when either side changes alone. |
| F-W2-06 | Secrets | Repo-wide grep: no key/token/password literals; `UNAS_API_KEY` read from env only (Secret Manager in staging); Unas error paths raise without echoing the key; BQ uses ADC. | **Verified, no defect.** |
| F-W2-07 | Idempotency on retry/refresh | PRG already covered discount re-render. Gaps found: double-POST of a gated discount emitted two audit events; walk-in double-submit minted two Z1 persons; re-saving an unchanged quote appended a duplicate revision; `BQWalkinStore.save` had no exists-check. | **Fixed.** Form tokens double as replay keys (discount: one audit event per applied discount, tested across double-POST; walk-in: replay returns the FIRST Z1 token, one row, tested); quote stores no-op on unchanged content (tested); BQ walk-in save refuses existing tokens. |
| F-W2-08 | CI green + nightly cron | Cannot verify runs from this sandbox: no valid GitHub credentials and the wave's commits are local-only (per the standing dev-box push flow). Static review: nightly cron IS scheduled in `ci.yml` (03:00 UTC); found and fixed in item 4 that `pip install -e ".[dev]"` lacked flask/python-barcode, so the UI test suite could never even import in CI — the pre-W2 green was partial. | **Deferred with a fix landed.** After push from dev-box: confirm the `ci` workflow is green on the head commit and that the scheduled run appears. |

## 3. Deviations from the decisions log

**None.** All 13 frozen rulings implemented as written. Two in-wave judgment
calls were surfaced and confirmed by wave-gate/item reviews: discount-line
provenance (`source` field) and dormant exclusion from konzultáció tiers.

## 4. Test evolution

30 (W1 baseline) → 55 (item 1 + wave-gate fix) → 69 (item 2 + review fixes)
→ 79 (item 3 + review fixes) → 86 (item 4) → **94 (wave close)**. Suites:
pricing/pair/search/thickness, ingest, quotes persistence, IRIS/Z1, frames,
barcodes, UI routes incl. security and money-path pins.

## 5. Open items for W3

1. **M5 auth**: replace `current_operator()`'s env-backed body with the
   session user; real approval flow for gated discounts (removes the
   `auto_approved_pre_m5` shim); revisit CSRF/roles properly.
2. **M4 order write**: quote → order conversion (Unas push behind operator
   confirmation, hard rule 7), SKU promotion on first sale, munkalap job
   numbers from a real sequence.
3. **Discount UI polish** + BQ-backed `discount_configs` loader (schema and
   signature already in place).
4. **IRIS views go-live**: config flip only (`SZEMPONT_IRIS=bq` + view-name
   envs) once IRIS publishes; keep fixture for tests.
5. **Staging deploy** (Sabie, from laptop): Cloud Run `szempont-*-staging`,
   run DDL 001+002, Secret Manager entries (`UNAS_API_KEY`), nightly catalog
   sync scheduler (stub already in the deploy script comment).
6. **Push + CI verification** from dev-box (F-W2-08).
7. Carried notes: exam UI must POST to the print route (F-W2-04); search-in-GET
   log exposure accepted pre-M5; munkadíj amount is a demo constant until the
   M2C service price list.
