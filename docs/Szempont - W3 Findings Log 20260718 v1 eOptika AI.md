# Szempont - W3 Findings Log 20260718 v1 eOptika AI

Running adversarial-review + verification log for the W3+W4 continuous run
(authority: Mega Review Brief rulings R1–R30, frozen 2026-07-18, plus addenda
R3a–R3c, R5a, R9a received 2026-07-18). One numbered entry per finding;
per-item mini-reviews append here. Tripwire stops are recorded inline.

## Ruling addenda received 2026-07-18 (recorded verbatim for W4 reference)

- **R3a** Storno is IRREVERSIBLE in Szamlazz (no storno-of-storno) — M8 UI
  must confirm-with-consequence before storno and never offer undo; a
  mis-storno is corrected by issuing a new invoice.
- **R3b** Szamlazz testing: no sandbox key exists — use a SEPARATE dedicated
  test account (its Agent key in Secret Manager as `szamlazz-agent-key-test`);
  the live account key arrives only at T−10 and its first use is the tripwire.
- **R3c** NAV receipt(nyugta)-reporting obligation lands 2026-09-01 —
  Szamlazz handles it engine-side; verify the account setting at T−10 go-live.
- **R5a** Effective-dated fund master table (Gondoskodás rejects pre-2026-07
  names) with per-fund, per-purchase-type vevő profiles (OTP: fund as vevő;
  Prémium & Gondoskodás product purchases: MEMBER as vevő). Prémium
  card-paid-product vevő conflict stays OPEN — both profiles switchable,
  default per annex.
- **R9a** W4-end infra checklist gains: staging experiment on Workspace
  session-control vs IAP session length; JWT audience per the annex's
  direct-on-Cloud-Run format.

## Ruling addendum 2 received 2026-07-18 (supersedes where in conflict)

- **R31** Hard weekend flip: ClearVisio until Friday close, Szempont from
  Monday open. Open ClearVisio orders are closed IN CLEARVISIO over the
  following weeks; Szempont originates only new orders. NO operational-state
  migration.
- **R32** R18 VOID; M11 collapses to nothing-to-build. `legacy_order_id`
  stays in schema (harmless), no importer exists or will.
- **R33** ClearVisio retained post-cutover as read-only archive at Sabie's
  discretion; apiV2 probe REMOVED from W4; ClearVisio API creds dropped
  from R23 (leaving only the Szamlazz keys).
- **R34** W5 = M12 reports + config, production infra (szem-pont.hu
  LB/cert/IAP per R9/R9a, IAP group per R8), cutover checklist + go/no-go,
  compiled manual. Nothing else.
- **R35** First live Szempont invoice = cutover Monday (T−10 invoicing
  superseded); live Szamlazz key installed + Tesztüzem→live verified over
  the cutover weekend; Monday's first invoice stays the tripwire, fired on
  a small controlled sale. *Consistency note (flagged back, accepted): R19's
  parallel-run is thereby shadow/practice only — ClearVisio remains the
  legal record until Friday close; R3c's 2026-09-01 receipt-reporting date
  must be checked against the actual cutover Monday.*

---

## F-W3-01 — R1 verification: Tharanis connector order-create / article-create coverage

**Status: coverage NOT confirmed for writes — connector is read-only.
Dry-run-only adapter in Szempont until the doc + permission grants arrive.**

### Connector located

- **`eoptikaltd/erp-connector`** is the existing Tharanis SOAP connector
  (Cloud Run job `erp-connector-daily` + ad-hoc service, dataset
  `natural-caster-496309-j3.ERPData`, GCS `gs://erp_vibe`). This is also the
  BQ mirror R16 points at for W4 stock.
- `eoptikaltd/erp-tharanis` is an **empty stub** (a `.gitignore`, nothing
  else); `eoptikaltd/kb` is empty. No other candidate repos in the org (53
  repos listed 2026-07-18).

### What the connector actually covers (code evidence, clone @ HEAD 2026-07-18)

- **Transport**: hand-built SOAP 1.1 envelopes against `urn://apiv3` — Tharanis
  publishes **no WSDL**; per the client docstring the API doc specifies four
  procedures — `berak` (insert), `modos` (modify), `torol` (delete), `leker`
  (query) — all sharing the argument list
  `ugyfelkod, cegkod, apikulcs, forrascel, xml`.
- **Implemented surface: `leker` ONLY.** `TharanisClient` has one public call
  (`leker`), one SOAPAction (`"urn://apiv3#leker"`), one envelope builder.
  Repo-wide grep: **no `berak`/`modos`/`torol` code, envelope, or test
  anywhere** — the strings occur only in the docstring listing the four
  procedure names.
- **Read endpoints** (registry, live-verified notes 2026-06-25 → 06-30):
  `kimeno_szamla`, `bejovo_megrendeles`, `kimeno_megrendeles`, `beszerzes`,
  `partner`, `cikk`, `keszlet`, `ar`, `cikkcsoport` + 9 reference dims.
  Full read-side field schemas for `bejovo_megrendeles` (fej/tetelek: sorszam,
  hivszam, kelt, fiz_mod, szall_mod, szla_*/szall_* address blocks, netto/afa/
  brutto, tetel: azon/cikksz/raktar/menny/netto_ar/tmegjegy) and `cikk`
  (alap: megnev/hu, ean_kodok, meegys, gyarto, csoport, vtsz, afaszaz/HUN…)
  are proven in `parsers.py`.

### Verification against Tharanis SOAP docs

- The API doc itself is **not present in any accessible repo** (searched
  erp-connector, erp-tharanis, kb, org code search). The connector's own
  comments record that the doc is **unreliable even for reads** ("the API doc
  misstated several [record wrappers], so parsers are modelled on real
  responses, not the doc"). External web lookup was declined in-session.
- Therefore: **order-create (`berak`→`bejovo_megrendeles`) and article-create
  (`berak`→`cikk`) exist as documented procedure+forrascel combinations but
  their payload schemas are UNVERIFIED** — no code, no doc copy, no live
  probe. The read-side schemas above are strong candidates for the write
  shape but must not be trusted until checked against the doc.
- **Permission gating is real and per-forrás/cél**: `keszlet` reads worked
  only after Tharanis granted the "Raktárak" API permission; `vevocsoport`
  still fails `hiba=1 "nem engedélyezett forrás/cél"`. Write grants for
  `bejovo_megrendeles`/`cikk` are almost certainly a **Tharanis-side
  enablement** that must be requested (external dependency, batched for
  Sabie alongside the API doc request).

### What Szempont reuses (proven conventions)

Mirrored into `vendors/tharanis.py` (adapter per hard rule 2): CDATA-wrapped
inner XML; **entity-escaped** filter operators (CDATA-wrapped operators are
rejected HTTP 500 by the WAF); `<hiba>` semantics — anything other than
`"0"`/empty is an error, and the error MESSAGE may sit in `<hiba>` itself
rather than `hiba=1`+`<valasz>`; retry taxonomy (5xx/transport retried 3×
exponential, 4xx never); date format `éééé.hh.nn`; credentials already in
Secret Manager (`tharanis-ugyfelkod`, `tharanis-cegkod`, `tharanis-apikulcs`).

### Consequences applied (R1, R13)

1. Szempont's order sink ships **dry-run only**: it renders the candidate
   `<berak>` payload from the proven read schema, stores it on the order's
   eseménynapló, and never POSTs. Live mode requires (a) doc verification of
   the berak payload, (b) the permission grant, (c) the live-write tripwire
   clearance — all three recorded here when they happen.
2. **R13 confirmed on the article side: registry + daily digest only.**
   Automated `cikk` article-create stays OFF; it becomes a separate flagged
   commit only after this entry gains a "berak verified" follow-up.
3. Batched external asks (for Sabie): Tharanis apiv3 API doc (berak sections
   for bejovo_megrendeles + cikk); write permission grants for both.

## PRIORITY OVERRIDE received 2026-07-18 (Sabie) — resequence to store MVP

All rulings stay valid; deferred items move later. New objective: fully
self-contained store MVP for floor rehearsal, zero external writes/deps.
Applied: Tharanis surface removed from the app — orders carry
`sync_status='pending'` (queued outbox; `vendors/tharanis.py` + R1
verification PARKED); munkalap PDF local/GCS-optional (R11 path shape);
Kezdőlap queues live (Mai átvételek with értesítendő flag replacing
M9-lite for now; Aláírásra váró = unsigned-GDPR walk-ins); deposit as
amount+method + NEM SZÁMLA fizetési összesítő (M8 deferred); gated
discounts approved by named approver WITHOUT PIN (marker
`m5_approver_no_pin`; PIN+IAP infra parked in `auth/`, tests green).
DEFERRED by the override: R1 SOAP verification follow-up, M8 sandbox, M10,
M9-lite, per-line VAT (R2). HARD STOP after MVP-2 for floor-feedback
triage. Deploy checklist additions: wkhtmltopdf in the app image;
SZEMPONT_SECRET_KEY in Secret Manager (session cookie signing).

---

## F-W3-02 — W3-1 adversarial mini-review (M4 orders)

Attack surfaces: order-create POST, status/cancel/dry-run POSTs, sequence
minting, money path, XSS via reason/eseménynapló/XML payload, promotions.

| # | Seam | Finding | Resolution |
|---|---|---|---|
| a | SZP sequence race | `orders/ids.py` documented an id-uniqueness backstop in the store, but `save()` did NOT enforce it — a collided id would silently APPEND the second order as revision 1 of the first (silent merge, worst-case money corruption). | **Fixed.** `save(..., expect_new=True)` on the creation path raises loud on an existing id (both stores); regression test pins one-revision-after-collision. Race window itself stays accepted (single terminal; documented). |
| b | Discount provenance on order create | `POST /megrendeles/uj` silently ignored an unknown `discount` id — order priced without the discount the operator saw on screen. | **Fixed.** Unknown discount → 400 `ismeretlen kedvezmény`; test added. |
| c | Gated-discount audit on order create | Order create re-applies the discount and the QUOTE store's save emits the discount audit event (BQ path writes audit_log), but WITHOUT the `auto_approved_pre_m5` marker the UI apply-path attaches. | **Accepted with note.** Marker unification lands in W3-2 (M5) which retires the shim entirely; until then order-created discounts are audited, marker-less. |
| d | XSS | Cancel reason, event notes, dry-run XML all render through Jinja autoescape; test pins `&lt;berak&gt;` in the page and well-formed XML under hostile names. | **No defect.** |
| e | CSRF/idempotency | Global same-origin guard covers the four new POSTs; ftok replay on create (first SZP id returned), status, cancel, dry-run. Tokenless double status-POST hits the transition guard (400), no double event. | **No defect** (tests). |
| f | N+1 person lookups | `/megrendelesek` resolves the person chip per row — fixture-cheap, but the BQ directory would pay one lookup per order row. | **Accepted pre-staging**; batch lookup TODO recorded for the staging deploy checklist. |
| g | Process note | The M4-core commit was pushed with the Dockerfile guard test red (caught by the guard, fixed in the next commit). | Rule reaffirmed: full suite green BEFORE push, no exceptions. |

Manual increment (R20): three W3-1 chapters + screenshots landed in
`docs/manual/` (wkhtmltoimage; its WebKit lacks CSS grid, so base.html
gained a dev-only `?shot=1` shim that collapses the app grid for capture —
never linked from the UI). Backfill chapters for W2 screens due by W3 close.

---

## F-W3-03 — MVP-1 + MVP-2 mini-review (override build)

| # | Seam | Finding | Resolution |
|---|---|---|---|
| a | Operator identity strength | Dropdown picker without PIN = honesty-based attribution (explicit override decision). Session cookie signed; SameSite=Lax default; open-redirect on `next` guarded (tested); unknown/inactive members rejected. | **As ruled.** PIN + IAP-JWT enforcement parked in `auth/` (unit-tested), re-wire is a small diff post-triage. |
| b | Gated approval without PIN | Approver is a dropdown claim; one-time approval refs still thread quote→order, still exactly ONE audit event, marker `m5_approver_no_pin` distinguishes the era from both `auto_approved_pre_m5` (dead) and future PIN'd events. | **As ruled**; tested incl. non-approver rejection. |
| c | Deposit validation | Over-total, non-positive, junk amount, unknown method all 400; deposit editable until terminal status; NEM SZÁMLA sheet carries a no-legal-effect clause and the remaining amount from the A1-allocated gross. | **No defect** (tests). |
| d | PDF generation | wkhtmltopdf subprocess: fixed arg list, temp html cleaned in `finally`, 60 s timeout, binary-missing degrades to an eseménynapló note. Local path under `var/` (gitignored after MVP-1 accidentally committed one PDF — removed). GCS branch env-gated, unexercised locally. | **Fixed in MVP-2** (gitignore); GCS path goes on the staging checklist. |
| e | Kezdőlap queue flags | 'értesítendő' derives from note events containing "értesítve" — a hand-written note with that word would also clear the flag. | **Accepted at MVP scope** (single marked button writes the note); revisit with M9-lite. |
| f | Copy semantics (R15) | Copy rebuilds from lens/option/frame SKUs at TODAY's catalog; discount deliberately dropped (fresh approval); works from terminal orders too. Removed lines stay removed (not copied). | **As designed**, tested. |

Deploy checklist additions (accumulating for the staging step): wkhtmltopdf
in the app image; `SZEMPONT_SECRET_KEY` secret; DDL 003+004 rerun (orders
gained sync_status/deposit; staff table + seed); `var/` volume or
SZEMPONT_DOCS_BUCKET for munkalap PDFs.
