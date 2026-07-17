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
