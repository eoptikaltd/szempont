# CLAUDE.md — Szempont (eOptika in-store POS)

## What this project is
Szempont replaces ClearVis.io as the in-store sales/order platform at eOptika's Teréz körút 50 store. Authoritative scope: `Szempont Execution Spec 20260712 v2 eOptika AI.docx` (modules M1–M12; build MIN = M1–M5 first). Context: `Szempont Handover Brief 20260712 v1 eOptika AI.md`. Read both before writing code.

## Environment
- GCP project: `natural-caster-496309-j3`, region `europe-west1`, EU data residency, HUF.
- Build machine: dev-box-2. Infra/gcloud from the operator's laptop under her named user.
- Repo: `eoptikaltd/szempont` (primary). Personal `eoptika2` account = scratch only.
- BigQuery: create only within `szempont*` namespace. Label EVERY job/scheduled query `tool=szempont`.
- Cloud Run: deploy to `szempont-*-staging` freely; production deploys require Sabie's wave sign-off.

## Hard rules
1. NO n8n. Cloud Run jobs / direct integrations / Unas API push / scheduled scripts only.
2. Every external vendor behind an adapter interface (Szamlazz.hu, suppliers, ClearVis). Never hardcode.
3. `unas_data.raw_orders` reads MUST dedup: `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_key ORDER BY _ingested_at DESC) = 1`.
4. Never mint person IDs — IRIS owns identity. Read A-grade zone; unresolved walk-ins go through the Z1 fallback contract.
5. No Rx/health data stored in this codebase or dataset — IRIS owns it; Szempont reads via contract (M6 stub until IRIS ships).
6. No customer messaging from this codebase — emit events to the GC communications module (M9). No SMTP/SMS credentials here.
7. No live writes to Unas/Tharanis (orders, products, stock) without explicit operator confirmation in the session; sandbox/test-flagged calls OK.
8. M1 (ruling 2026-07-12): Szempont NEVER parses FS6/SF6. Catalog data is consumed from BigQuery (`sf6_catalog_converter.pl_items_enriched` and successors), produced by the separate `eoptikaltd/sf6-converter` project. New suppliers = new CatalogSource adapter, never a parser here.
9. Every lens variation gets its own real SKU (no generic SKUs). Full catalog lives in BQ; SKUs are promoted to Unas/ERP on first sale (M4 promotion service).
10. Hungarian text/encoding: expect diacritics everywhere; accent-stripped names are equivalent to canonical forms; strip leading `^\d+\s+` from payroll-style names.

## UI
Atlas design system (kit in project files): cream `#FBF7EE` / gold `#C9A961` / ink `#1A1A1A`; Cormorant Garamond (display) + DM Sans (body); Atlas page archetypes and central nav.json; 3-tier density. Match existing Atlas tools' look exactly.

## Code standards
- Python 3.12 on Cloud Run (jobs + services); pure-function pricing engine with pytest suite before any UI.
- Idempotent ingest jobs; effective-dated tables; versioned catalogs (quote reproducibility is an acceptance criterion).
- Structured audit logging to `szempont.audit_log` for discounts, cancellations, SKU promotions.
- Config via env vars + Secret Manager; zero credentials in repo.
- Conventional commits; PR per module; CI must pass tests before merge.

## Workflow
- Wave plan per spec §3.1 (W1: M1+M2 engine; W2: M2 UI + M3; W3: M4+M5). End every wave with an adversarial self-review pass, then a short milestone report: `Szempont - Milestone Report YYYYMMDD vN eOptika AI.md`.
- User manual increment: for every screen frozen this wave, add task-recipe chapters (Hungarian, task-oriented "Hogyan..." format) to `docs/manual/`, with screenshots captured from the locally running app via wkhtmltoimage; the manual increment is reviewed at the same wave gate as the milestone report; pilot reader is a floor colleague, not the founder.
- Decisions for Sabie: numbered menu, recommended option marked.
- When blocked on external items (IRIS views, comms contract, credentials): stub against the documented contract and continue; batch questions.
