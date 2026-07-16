# Szempont - Decisions Log 20260716 v1 eOptika AI

All W2-gating decisions ruled by Sabie 2026-07-16. Code/schema changes applied in package v17; tests 30/30.

## Rulings applied

| # | Ruling | Implementation |
|---|---|---|
| 1 | **NO COGS/margin data in Szempont** (challenge upheld) | `cost_net_huf` removed from CatalogRow + DDL; margin stripped from finder/quote/konzultáció UI; ordering = precomputed `rank_score` (opaque, computed outside Szempont — Moneyprint/BQ owns the intelligence), tiebreak retail asc. Konzultáció tiers now price-anchored (cheapest/middle/top), rank_score overrides the middle pick when published. Engine retains cost fields internally at 0 for structural compatibility; nothing ingests or displays cost. |
| 2 | D1 egészségpénztár: YES | `szempont.quotes` gained payer_type/payer_name/payer_member_name/payer_member_id/payer_billing_address; flows to orders/invoices in W2 build |
| 3 | D2 service lines: YES, all lines optician-editable; auto-add applies to basket only | line_type gains `service`; lines carry `auto_added` + `removed` flags — invoice renders only non-removed lines |
| 4 | D5 choice groups: YES | `Surcharge.choice_group`; engine enforces exactly-one-per-offered-group (3 new tests) |
| 5 | Rounding: ROUND_HALF_UP on final gross, whole HUF — CONFIRMED | frozen as A1 |
| 7 | D3 discounts: curated structured configs | W2 build item |
| 8 | D6 offer variants: YES | quotes schema keeps offer_set_id; carousel in W2 UI |
| 9 | M2C: W2-light + swivel tablet | prototype already in repo; productionize in W2 |
| 10 | Dormant SKUs: muted pill | W2 UI item |
| 12 | Sync: nightly Cloud Scheduler after converter refresh, staging | deploy script comment already stubs the scheduler command |
| 13 | EESZT: NOT in use | F18/D9 closed; no constraint on parallel-run |

## Environment

- `eoptikaltd/szempont` exists; collaborator access confirmed. This sandbox holds no GitHub credentials, so the **initial commit happens from dev-box**: unzip package v17 into the clone, `git add -A && git commit -m "feat: W1 + W2 head start (rulings 2026-07-16 applied)" && git push`.

## #6 — IRIS contract — **APPROVED 2026-07-16** (formalized in contracts/iris_contract.md; Z1 DDL added; grounded in live crm_core: grade/in_zone_fulfilment gates verified, person.ep_member_hint ties into D1)

**Read side (M3):** IRIS publishes two views, Szempont reads nothing else:
1. `iris.v_person_lookup_a` — person_id, canonical_name, phone_e164, email_lc, birth_date, gdpr_marketing_ok, dm_blocked, last_activity_at. A-grade fulfilment zone only.
2. `iris.v_person_search` — person_id + normalized keys: name_accent_stripped (per house rule), phone_digits, email_lc, birth_date. Szempont's customer search queries only this view; card render joins lookup_a.

**Z1 walk-in fallback (write side):** Szempont NEVER mints person IDs. Unresolved walk-ins are written to `szempont.walkin_persons` with a `Z1-<uuid>` temp token (prefix makes non-person status unmistakable) + captured contact fields + consent flags. IRIS ingests nightly, resolves or mints the real person_id, and writes the mapping to `szempont.walkin_resolutions` (z1_token → person_id, resolved_at). Szempont joins through the mapping; quotes/orders created under a Z1 token are re-attributed by the join, never rewritten.

**Rationale:** two read views keep IRIS free to refactor internals; the Z1 token in a szempont-owned table keeps the identity boundary clean (rule 4/6) while walk-ins never block a sale.

## W2 build order (proposed, starts on push)

1. Schema migration per rulings (DDL v2) + quotes persistence (M2, incl. offer variants + service lines + payer fields).
2. Finder/quote UI completion: dormant pills, choice-group chips, frame line via Unas search, discount configs.
3. M3 on the IRIS views above (pending your approval of the contract).
4. M2C productionization + munkalap/quote print routes with real EAN-13.
5. Wave close: adversarial review + milestone report.
