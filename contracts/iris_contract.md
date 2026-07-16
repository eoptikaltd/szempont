# IRIS ↔ Szempont Contract v1 — APPROVED 2026-07-16

Grounded in live crm_core objects (verified: person / v_person_canonical /
v_person_identifiers with grade + in_zone_fulfilment; person.ep_member_hint).
Interface columns below are FROZEN; IRIS owns the implementation behind them.

## Read side (M3) — the only IRIS objects Szempont queries

### 1. crm_core.v_person_search  (to be published by IRIS)
| column | type | note |
|---|---|---|
| person_id | STRING | canonical (post-merge) id |
| id_kind | STRING | name \| phone \| email |
| search_key | STRING | normalized: accent-stripped lowercase name / digits-only phone / lowercase email |
| birth_date | DATE | nullable, disambiguation |

Population rule: A-grade, fulfilment zone only —
`grade = 'A' AND in_zone_fulfilment`, person_ids mapped through
v_person_canonical (merged ids never surface).

### 2. crm_core.v_person_lookup_a  (to be published by IRIS)
| column | type |
|---|---|
| person_id | STRING |
| display_name | STRING |
| phone_e164 | STRING |
| email | STRING |
| birth_date | DATE |
| ep_member_hint | BOOL |
| dm_blocked | BOOL |
| gdpr_signed | BOOL |
| last_activity_at | TIMESTAMP |

Attribute survivorship (person_attribute_history × survivorship_rules) stays
IRIS-internal; only these columns are contractual.

Szempont query pattern: search → v_person_search (search_key prefix/equality),
render card → v_person_lookup_a by person_id. Nothing else is read from crm_*.

## Write side — Z1 walk-in fallback (Szempont-owned tables)

Szempont NEVER mints person IDs. Walk-ins that don't resolve get a
`Z1-<uuid>` token in `szempont.walkin_persons`; IRIS ingests nightly,
resolves-or-mints, and writes `szempont.walkin_resolutions`
(z1_token → person_id). Szempont attributes quotes/orders through the mapping;
original rows are never rewritten. DDL in infra/ddl (§walkin).

## SLOs
- v_person_search freshness: ≤ 24h behind spine runs (nightly acceptable).
- walkin resolution: nightly batch; unresolved > 7 days surfaces on the IRIS
  merge_review_queue, not Szempont's problem.
