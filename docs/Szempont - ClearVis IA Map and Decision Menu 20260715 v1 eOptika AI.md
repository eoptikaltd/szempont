# Szempont - ClearVis IA Map and Decision Menu 20260715 v1 eOptika AI

## 1. IA map — where every ClearVis menu item lives in Szempont

Principle: same task, same conceptual place, same Hungarian word. Atlas visuals, ClearVis vocabulary.

| ClearVis menu | Szempont home | Module | Notes |
|---|---|---|---|
| Kezdőlap | Kezdőlap | shell | Same two quick cards (Vevők search, Készlet check) + Aláírásra váró nyilatkozatok queue |
| Vevők | Vevők | M3 | IRIS A-grade lookup behind the same search box; vevő adatlap keeps action-bar order: Módosítás · Vizsgálat* · Rendelés · Új időpont* · Feljegyzés · Email · SMS (* = link out to Fovea/ClearVis during parallel-run) |
| Vizsgálatok | link-out (parallel-run) → later Fovea | — | Exam stays in ClearVis until Fovea; menu item present, routes out |
| Időpontfoglalások | link-out → Fovea | — | Fovea owns booking |
| Termékek | Termékek | M1/M4 | Catalog browse over szempont.lens_catalog + Unas products; keeps Tőcikkszám vocabulary |
| Készletvezetés | Készletvezetés | M10 | Verbatim op names: bevételezés, boltközi mozgás, kivét, selejtezés, leltár; Tharanis master |
| Megrendelések | Megrendelések | M4/M7 | Same quick-filter chips (Lencsék szállítótól megrendelendőek / Készleten / Kiadható / Késő + időszak) |
| Eladások | Eladások | M5/M8 | Register list; Előleg átvétele / Számla / Nyugta / Készpénz betét-kivét actions |
| Kimutatások | Kimutatások | M12 | Parity 6: napi + időszaki pénzforgalom, nyitott előlegszámlák, nyitott megrendelések, tételes eladás, készletmozgás; rest → Moneyprint |
| Üzenetkezelés (sablonok) | — | M9 | Templates live in GC comms module, not Szempont |
| Adminisztráció → Munkatársak | Adminisztráció | M5 | Role names verbatim: Cégvezető, Üzletvezető, Optometrista, Kontaktológus, Ügyfélszolgálatos, Bolti eladó |
| Adminisztráció → Kedvezmények | Adminisztráció | M5 | Structured configs (see decision D3) |
| Adminisztráció → Adatintegráció | DevOps (Atlas) | M11 | Sync/retry queues are an ops concern; surfaced in Atlas DevOps, not the POS |
| Adminisztráció → Üzletek / Rendszerbeállítások | Adminisztráció | M12 | Location list read from Tharanis/config |

New in Szempont (no ClearVis ancestor): **Lencsekereső** (pair-first finder — replaces catalog binders; the Glasson-pattern differentiator).

Staff cheat sheet ("mi hol van") = column 1 → column 2 of this table, one page, Atlas-styled; produce at W2 close.

## 2. The offer-flow parity checklist (M2 UI acceptance addendum)

From the observed wizard, Szempont's quote flow must have: correction-type entry with colour accents → Rx form (Jobb/Bal, per-eye PD, kontroll date, CL: BC/DIA/type + szemcsepp/ápoló mezők) → offer card with frame slot (typeahead + Hozott keret + per-eye min. átmérő) and lens slot (typeahead, per-eye power validation pills, Rendelésből/Készletről) → option layers (choice-group chips / optional services / tint) → misc line add → live gross total → multiple offer variants (◀ ▶ +) → Egy kijelölt ajánlat elfogadása → order with fitting-data + edging-data sub-forms and lencserendelés action.

## 3. Consolidated decision menu (F1–F27 → 9 decisions)

**D1 — Egészségpénztár support (F1).** Health-fund payer on person + invoice.
(a) MIN scope: payer entity on quotes/orders/invoices, member name+ID fields, multiple billing addresses — **recommended** (b) defer to post-go-live (blocks real store traffic) (c) IRIS owns payer entities, Szempont references.

**D2 — Service lines in the quote model (F11).** Munkadíj (PF-) + vizsgálat (ET-) as priced, discountable lines.
(a) Add `service` line type with code table, munkadíj auto-added by frame type — **recommended** (b) fold into lens price.

**D3 — Discounts (F20).** (a) Structured configs covering the ~12 live rules (threshold, coupon, percent-on-line-type, date window, auto/manual, exclusivity) — **recommended** (b) port the ClearVis DSL (c) manual-only at launch.

**D4 — Pair discount allocation (F12).** (a) Split pair-level discounts across eyes, remainder to Jobb (matches observed 27 144/27 143) — **recommended** (b) keep discount as separate line.

**D5 — Choice groups on lens options (F23).** (a) Add exactly-one-of `choice_group` to the surcharge model now (schema-level, cheap) — **recommended** (b) W3.

**D6 — Offer variants (F21).** (a) `szempont.quotes` gains offer_set_id + variant carousel in W2 UI — **recommended** (b) single quote at launch.

**D7 — Fitting-data dictionary (F13/§22).** (a) Adopt the observed ~35-field dictionary as JSON payload with per-supplier extensions (Hoya METS etc.) behind the supplier adapter; minimum set (PD + heights) as typed columns — **recommended** (b) full typed schema (rigid, supplier-hostile).

**D8 — Cheap wins bundle (F7 Másolás, F17 kedvenc csomagok, F26 kontroll date, F27 szemcsepp/ápoló prompts).** (a) All four into W2 backlog — **recommended** (b) cherry-pick.

**D9 — EESZT (F18).** (a) You confirm current usage; if live, parallel-run keeps exams (and EESZT) in ClearVis until Fovea, Szempont never touches it — **recommended** (b) investigate integration now (scope creep).

## 4. Sizing note

D1+D2+D5 touch `szempont.quotes`/pricing schema — decide before W2 build starts to avoid migration churn. D3/D6/D7 are W2-internal. D8 is backlog. D9 is a ruling, not work.
