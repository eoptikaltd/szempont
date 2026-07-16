# Szempont - ClearVis Functional Audit 20260715 v1 eOptika AI (final — 45 screens, 3 batches)

Extraction from 13 live ClearVis screenshots (Teréz körút, user szabivagyok). Purpose:
task-flow/terminology parity + feature coverage vs Execution Spec v2. Visuals stay Atlas.

## 1. Shell & session model

- Login (username/password, previous-users panel) → **Store selection** ("Select the
  store you are in"): Teréz körút 41 (warehouse — a "store" in ClearVis!) and Teréz
  körút 50. Store context persists in the top bar and pre-filters every list.
- Top bar: Főmenü (hamburger) · notification bell (red badge) · store switcher · user menu.
- Szempont mapping: Atlas top bar already has profile; **add store-context chip**
  (Teréz50 default; Teréz41 needed for M10 stock ops) and keep it as a global filter.

## 2. Menu tree (verbatim — basis of the IA map)

Kezdőlap · Vevők · Vizsgálatok [badge: 424 open] · Időpontfoglalások · Termékek ·
Készletvezetés · Megrendelések · Eladások · Kimutatások ·
**Üzenetkezelés**: Email sablonok · SMS sablonok · Levelezés beállítások ·
**Adminisztráció**: Munkatársak · Adatintegráció · Üzletek · Kedvezmények · Rendszerbeállítások

## 3. Kezdőlap pattern

Two quick-action cards: **Vevők** (search name/phone/email + Új vevő + recent-history
icon) and **Készletvezetés** (stock check by cikkszám/name/**barcode** + Új bevételezés).
Below: **Aláírásra váró nyilatkozatok** — GDPR declarations awaiting signature, names +
birthdates, front and center. → Szempont home = same two cards + declarations queue
(M3 consent flow feeds it).

## 4. Vevő adatlap (customer card — the anchor object)

Header: name, **PA-xxxxxxx id**, address, phone, email, **"7 számlázási cím"** (multiple
billing addresses), **"DM tiltva"** flag, tag add. Warning banner: no loyalty card
("törzsvásárlói kártya") + register link.
Action bar (verbatim order): **Módosítás · Vizsgálat · Rendelés · Új időpont ·
Feljegyzés rögzítése · Email küldése · SMS küldése · ⋮**
Body: full **omnichannel event timeline** (filter: "Összes esemény") — webshop orders
("Webshop és ERP API fiók rendelést rögzített") and store orders (named colleague
rögzített) interleaved, oldest at bottom. Per order card:
- line items: eye (Jobb/Bal), product, SKU, params (BC/Dia/Sph), qty, price
- **ERP azonosító VO25/xxxxxx** + **Hivatkozás EO43321-xxxxxxx** (= Unas ShopId ref!)
- Belső feljegyzés hozzáadása · Napló megtekintése (audit log per order)
- Összesen · Számla rows incl. **sztornó** (storno referencing original) · Még fizetendő
- status ✓ Rendelés teljesítve; pills **Kiadott / Visszavett**
- footer: **Aláírás · Rendelés nyomtatása · Másolás · Értesítő üzenet küldése ▾**

## 5. Megrendelések list

Quick-filter chips, two groups (verbatim):
- **Címkékre**: Lencsék szállítótól megrendelendőek · Készleten · Kiadható · Késő
- **Időszakra**: Aktuális hét · Múlt hét · Aktuális hónap · Előző hónap
Rows: customer · SO-number (SO-1604884A) · product class (Egyéb termék / Állandó
kontaktlencse / Egyfókuszú távoli szemüveg) · timestamp · store · **assigned colleague**
(e.g. Varga Orsolya; "Látszerész Mariann") · status pill(s) · total ·
**"Fizetve összesen: X Ft, Még fizetendő: Y Ft"** — deposit balance on every row
(live example: 111 120 total, 50 000 paid, 61 120 owed).

## 6. Termékek / Készletvezetés

Termékek rows: name · **Tőcikkszám** (master SKU) · price chip · stock chip
**"13+40 db szabadon"** (two-pool free-stock format — pools TBC, likely store+warehouse) ·
Kategória · lifecycle (Rendelhető / **Kifutó termék**). Bottom action bar: Új termék ·
Gyártók · Beszállítók · Címkék · **Tömeges vonalkód nyomtatás** · Import és Export.
Készletvezetés ops list (filter "Beavatkozást igénylő"): **Bevételezés** (suppliers seen:
eOptika Kft., Hoya Lens Hungary Zrt., Carl Zeiss Vision Hungary Kft.) · **Selejtezés**,
each store + timestamp + MO-xxxxxxxx id + státusz **Tervezett**. Bottom bar (verbatim →
M10 movement_type vocabulary): **Új bevételezés · Új boltközi mozgás · Bejövő
bizonylatok · Új selejtezés · Új kivét · Új leltár**.

## 7. Vizsgálatok list

Filters: store + **"Nyitott (legrégebbi elől)"**. Rows: name · phone · birthdate (with
computed age) · address. 424 open badge in menu. Bottom floating **Frissítés** bar.

## 8. Functional findings NOT (or only partly) in Execution Spec v2 — decision candidates

| # | Finding | Evidence | Spec status |
|---|---|---|---|
| F1 | **Egészségpénztár purchases**: health funds are customer records — "OTP Egészségpénztár (Unszorg Aliz / 229022992)", "Prémium Egészségpénztár (Lengyel Andrea) / 66344"; member name + member ID in the customer name; multiple billing addresses per person (the "7 számlázási cím") | Vevők list, vevő adatlap | ABSENT — invoicing to health funds is a compliance-relevant HU optics staple; touches M3 (person model), M5 (checkout), M8 (invoice recipient) |
| F2 | **Loyalty card** (törzsvásárlói kártya) prompt on customer card | adatlap banner | ABSENT — IRIS territory? needs ruling |
| F3 | **Signature capture** ("Aláírás" on orders; Aláírásra váró nyilatkozatok queue) | home + order footer | Partial — spec M3 mentions GDPR consent; signing device flow not specified |
| F4 | **DM tiltva** (marketing opt-out) surfaced on card header | adatlap | M9/GC comms concern — Szempont must display, GC must enforce |
| F5 | **Assigned colleague per order** incl. látszerész role | Megrendelések rows | Partial (M5 roles exist; per-order assignment not spec'd) |
| F6 | **Storno invoice flow** visible per order with reference chain | adatlap timeline | M8 has storno — confirm reference-chain display |
| F7 | **Order copy** ("Másolás") — repeat CL orders in one click | order footer | ABSENT — cheap, high-value for contact-lens repeat buyers |
| F8 | **Two-pool stock display** "X+Y db szabadon" | Termékek | M10 detail TBC |
| F9 | **Barcode-first** stock check + bulk barcode print | home, Termékek | M10 — confirm barcode printing in scope |
| F10 | Order quick-filters incl. **"Késő"** (late) and **"Lencsék szállítótól megrendelendőek"** | Megrendelések | Direct input to M7 (lab/status) + supplier-ordering worklist |

## 9. Status vocabulary observed (→ szempont.orders.status / tags)

Order: **Rögzített → Kiadott**, exception **Visszavett**; completion "Rendelés teljesítve".
Tags: Lencsék szállítótól megrendelendőek · Készleten · Kiadható · Késő.
Stock op: **Tervezett** (→ presumably Végrehajtott). Product lifecycle: Rendelhető · Kifutó.

## 10. Still needed (batch 2+) — in priority order

1. **Rendelés creation flow** from the vevő adatlap (the wizard: product/lens selection,
   Rx entry, measurements, pricing, deposit) — the M2/M4 heart; not yet seen.
2. **Vizsgálat detail form** (Rx fields, protocol).
3. **Eladások** screen (non-Rx POS sale + napi zárás if any).
4. Order detail incl. **printed munkalap/order sheet**.
5. Kimutatások (which reports staff actually use).
6. Kedvezmények admin (discount model → M5 gating).
7. Időpontfoglalások (Fovea overlap check).
8. Rendszerbeállítások / Adatintegráció (M11 migration surface).


---

# BATCH 2 (14 screens: order details, product model, Eladás, invoice, reports, staff, locations, discounts, settings)

## 11. Order detail — glasses order (Czinege Anikó, SO-1604869D) — the M2/M4/M7 blueprint

Line-item anatomy of a complete spectacle order:
- **Frame**: Emporio Armani EA 4115 — dual price display **69 600 → 43 819 Ft** (list vs after-discount, both always visible)
- **Jobb lens**: Streetlife Ormix 1.60 Raktári (kiszerelés: Alapértelmezett), ES-E6S100-91, Dia 6565, Sph +0.75, Cyl −0.25, **Axis 100** — 29 200 → 27 144
- **Bal lens**: ES-E6S100-92, Sph +1.00, Cyl −0.25, Axis 80 — 29 200 → **27 143** (1 Ft difference: pair-level discount split across eyes with remainder handling!)
- **Munkadíj** as line item: "Szemüveglencsék elkészítése teli keretbe" **PF-00005** 4 000 → 3 718 (work fee coded per frame type: teli/damilos/fúrt)
- **Látásvizsgálat szemüvegkészítés céljából** **ET-00001** 10 000 → 9 296 — the eye exam is a chargeable line, discounted when converting to purchase
Sub-form links on the order: **Illesztési adatok megadása** (fitting data) · **Becsiszolási adatok megadása** (edging data) · **Lencserendelés létrehozása** (create supplier lens order) — these three ARE the M7 Műhely/WIMO-4a contract surface.
Payments: **Előleg** invoice EOPT-2026-18342 (Bankkártya) 50 000 · Még fizetendő 61 120.
**Eseménynapló**: every tag add/remove timestamped with store + user ("Új címkék: Rögzített, Lencsék szállítótól megrendelendőek") → maps 1:1 to szempont.audit_log.

## 12. Order detail — CL order (Endrész Dávid): "(Hozott recept alapján)" flag in the title — brought-own-Rx is a first-class order attribute. CL line carries BC/Dia/Sph + doboz qty. Footer: Vissza · Vevő megtekintése.

## 13. Product model (lens) — three-level hierarchy

Parent **ES-E6S100** "Streetlife Ormix 1.60 Raktári" → **Változatok (96)** power variants → per-variant **Kiszerelések** (packaging units with own cikkszám + "Eoptika cikkszám").
Parent page shows: attribute text (tömörség, UV transmission), **Listaár szerkeszthető: Nem**, per-diameter parameter matrix (65/70/75) with **Sph range chips** (e.g. +0.25→+6.00; −6.00→plan), **Cyl Max**, **Prizma: Nem rendelhető**, Fogyasztói ár **"29200 HUF (2016)"** — the price carries its vintage year (stale-price signal; these 2016 prices are exactly why the FS6→BQ pipeline exists).
**ELÉRHETŐ SZOLGÁLTATÁSOK (Opcionális)** attached to the lens: Damilos keret beküldve 10 800 · Fúrt keret beküldve 14 400 · Teljes keret beküldve 7 200 · Távbecsiszolás 3 000 — services-as-surcharges bound to the lens product, incl. remote-edging for external frames. ÁFA 27%, Vámtarifaszám, Gyártó. Footer: **Másolás új termékbe · Vonalkódok nyomtatása · Szerkesztés**.

## 14. Eladás (register) + invoice

Eladás list rows: buyer · **EOPT-2026-xxxxx** number · timestamp · store · payment tag (Bankkártya/Készpénz) · amount; storno pairs ("EOPT-2026-18346 sztornója" ↔ "Sztornózott"), **Előleg** and **"Előleg visszafizetés"** (−100 000 refund) rows. Bottom bar: **Előleg átvétele · Számla létrehozása · Nyugta létrehozása · Készpénz betét/kivét** — nyugta vs számla distinction AND cash-drawer in/out ops.
Invoice detail: billing name/address/adószám, megjegyzés auto-references the SO, kiállítás/teljesítés/fizetési határidő, fizetési mód, line items each tagged with source SO, **Áfa gyűjtő** summary. Footer: **Számla sztornózása · Számla javítása · Visszavét · Nyomtatás**. Invoicing is native in ClearVis (EOPT- prefix, per-location prefixes visible in settings) — M8 replaces this with Szamlazz.hu Agent; parity list = these four footer actions + deposit/final/storno/refund chain.

## 15. Kimutatások (verbatim inventory)

Eladások: Időszaki pénzforgalmi jelentés · Megrendelések és eladások · **Napi pénzforgalmi jelentés** (= napi zárás) · **Nyitott előlegszámlák listája** · Számla export · Tételes eladási kimutatás · Tételes pénzforgalmi kimutatás. Készlet: Készletlekérdezés · Készletmozgás kimutatás. Vevői rendelések: Kedvezmények · Nyitott megrendelések. Vevők: Időpontfoglalási kimutatás · Szemvizsgálati kimutatás · Vevők (utolsó rendeléseik + szemvizsgálataik).
→ Szempont M12 report parity target ≈ 6 of these (napi/időszaki pénzforgalom, nyitott előlegek, nyitott megrendelések, tételes eladás, készletmozgás); rest lives better in Moneyprint/BQ.

## 16. Roles & staff (Munkatársak + profile)

Role tags in live use: **Cégvezető · Üzletvezető · Optometrista · Kontaktológus · Ügyfélszolgálatos · Bolti eladó · Könyvelő · Előfizető** (+ "Arany díjcsomag" plan tag). API integrations exist AS user accounts: **"Webshop és ERP API fiók"** (the account that writes webshop orders into ClearVis) and **"Google BigQuery API"** (Könyvelő role!) — our own current export path, relevant to M11.
Profile page: **Pecsétszám** (optometrist stamp number — medical credential field), language choice, **Kedvenc termékcsomagok** (favourite bundles per user), notification-subscription matrix (Igen/Nem/Automatikus) incl. **"EESZT jogosultság hiba"** — EESZT (national eHealth) integration exists in ClearVis. Device-level settings page (Eszközbeállítások): theme, **incoming-call notification** (CTI!), **"Mérőműszerekről jövő eredmények másolása automatikusan"** (DataGate instrument auto-copy).

## 17. Üzletek = full location graph (M10 model, much richer than store+warehouse)

Dozens of "stores": numbered **raktár zones (32–59)**, Teréz 41 with sub-locations (**Anyagok, Eszközök, Foglalás, Nem találtuk!, Sérültek, VW #01**), Teréz 50 with (**Foglalás, Nem találtuk!, Sérültek, <#014**), **Műhely - Teréz körút 50** (+ <#001, <#010), 3PLs (**Cloud Fulfilment, iOttica.it Magazzino Amalfi, Pueblo Torrequebrada**, each with < #sub-locations), **GLS (Italy, Trieste)**, **GPSe (Expected returns)**, Baross utca, Táblás utca, deleted marker ("ID #3 - Törölt!").
Semantic virtual locations: **Foglalás** (reservation), **Sérültek** (damaged), **Nem találtuk!** (lost) — the "X+Y db szabadon" two-pool display from batch 1 is explained by free vs reserved. Tharanis is stock master per spec; this list defines the location vocabulary Szempont must at least read/display.

## 18. Kedvezmények = a rule DSL, not a flat table (M5 sizing input!)

Editor fields: Név · **Elérhetőség** (availability expression, e.g. `date.until('2022-04-07') and option.hasProductWithTag('Szemvizsgálat')`) · Prioritás · **Automatikus használat** toggle · **Csoportok** (Basic/Kategória) · **Csoporton belül exkluzív** · Aktív · repeated **Feltétel** blocks (`not product.hasTag('Szemvizsgálat') and option.hasProductWithCode('ET-00001')`) each with **Típus (Érték/%)** + Érték — per-exam-code values 5000/7000/5000/6000 in one discount.
Live catalog includes: threshold discounts ("20000ft felett"), coupon codes, −50% munkadíj, **−100% sikertelen kontaktlencse-illesztés** (failed CL fitting write-off), 50% Berkeley/Helvetia frame. Footer: Új kedvezmény · **Kedvezmények importálása**.
→ M5 estimate in spec assumed simple discounts; real usage needs: date windows, tag/code conditions, order-level qualifiers, amount|percent, auto vs manual, group exclusivity, priority. DECISION: port the DSL (big), or curate the ~dozen live rules into structured configs (recommended).

## 19. New findings F11–F20 (batch 2)

| # | Finding | Spec impact |
|---|---|---|
| F11 | Work fee (munkadíj) + eye exam as priced, discountable order lines with PF-/ET- codes | M2 quote model: add service lines (beyond frame+lens+options) |
| F12 | Pair-level discount split across eyes w/ remainder (27 144 / 27 143) | pricing engine: pair discount allocation rule needed |
| F13 | Illesztési + becsiszolási data as structured sub-forms on the order | defines M7 contract fields; coordinate with WIMO 4a |
| F14 | "Lencserendelés létrehozása" — explicit supplier lens-order step + auto tag "Lencsék szállítótól megrendelendőek" | M7/M10 supplier ordering worklist (batch-1 F10 confirmed as a flow, not just a tag) |
| F15 | "(Hozott recept alapján)" order flag | M2/M6: brought-own-Rx boolean, affects exam-line and liability |
| F16 | Nyugta vs Számla + Előleg átvétele + Előleg visszafizetés + Készpénz betét/kivét | M8 scope: receipt mode, deposit refund, cash-drawer ops — currently unspecced |
| F17 | Per-user Kedvenc termékcsomagok (favourite bundles) | M2 UI nicety; cheap, staff-loved |
| F18 | EESZT integration signals (jogosultság-hiba notification) | verify with Sabie: is EESZT in active use? If yes → IRIS/Fovea territory, NOT Szempont, but parallel-run must not break it |
| F19 | Instrument auto-copy (DataGate) + incoming-call CTI as device settings | out of Szempont MIN; note for M12/Fovea; parallel-run keeps ClearVis on the exam side anyway |
| F20 | Discount rule DSL (see §18) | M5 re-scope decision |

## 20. Still missing (batch 3 wish-list, shortened)

Order **creation** wizard (product/lens picker in action, Rx entry step, discount picker) · Vizsgálat detail form · Időpontfoglalások screen · napi zárás flow · munkalap/order PRINT output (the physical sheet Műhely reads).


---

# BATCH 3 (18 screens: the ajánlat creation wizard, Rx entry, fitting data, Adatintegráció, product stock ledger)

## 21. The ajánlat (offer) flow — ClearVis's answer to M2, end to end

**Entry**: from the vevő adatlap, Új esemény → correction-type picker, colour-coded:
Egyfókuszú szemüveg (orange) · Többfókuszú szemüveg (red) · Kontaktlencse (purple) ·
Multifokális kontaktlencse (purple) · Egyéb termék (blue) — or "Egyéb termék rendelése"
straight through. The colour coding carries through to order headers everywhere
(batch-2 orders: purple CL, orange SV, blue egyéb — staff navigate by colour).

**Rx entry forms** (per correction type, all with Jobb/Bal rows):
- SV glasses: tabs **Távoli / Olvasó / Speciális**; szférikus, cylinder, axis,
  **pupillatávolság per eye**; Távolság (cm); **Javasolt kontroll időpontja** (date —
  next-checkup recall hook!); Feljegyzés.
- Multifocal glasses: tabs **Normál / Beltéri degresszióval / Beltéri addícióval**;
  adds addíció per eye.
- Contact lens: header toggles **✓jobb ✓bal szemre** (single-eye orders possible!);
  tabs **Állandó / Alkalmi / Orthokeratológiai**; type, görbület (BC), átmérő per eye;
  sph/cyl/tengely; inline **"kontaktlencse készlet"** stock panel per eye;
  **Szemcsepp + Ápoló folyadék** fields (cross-sell captured at Rx entry!); kontroll date.
- Multifocal CL: same + addíció, Állandó/Alkalmi tabs.

**Offer card(s)**: one customer can hold MULTIPLE parallel ajánlat variants —
carousel ◀ ▶ + "+" adds another; bottom bar "**Egy kijelölt ajánlat elfogadása ✓**"
converts the selected one to a megrendelés. Card toolbar: favourite ★ · document ·
delete · **copy** · select ✓. Incomplete cards show a red (!) price tag; slot rows
("Keret választása…", "Lencse választása…") carry yellow warning tags until filled.

**Frame slot**: name/cikkszám typeahead + **"Hozott keret" checkbox** (customer's own
frame) + **Jobb/Bal minimális átmérő** (default 50/50 — the frame drives minimum lens
diameter per eye) + "Nincs készletmozgás" dropdown (no stock movement for own frames).
Chosen stock frame shows **"Készletről"** source note.

**Lens slot**: typeahead by name/code (e.g. "HOYA" → Hoyatint 1.50 U4 G.Bar Hvsp
B.Raktári (HO-QHURB), M.Raktári…); per-eye power pills turn **green when the chosen
lens covers both eyes' powers**, warning tag if not; source dropdown **Rendelésből /
Készletről**; then three option layers:
1. **Választandó Szolgáltatások** — mandatory-choice chip group from the lens product
   (e.g. Essilor SunMax: Crizal Sun XProtect | e-mirror Arany rózsaszín | Bronz | Erdő
   zöld | Ezüst | Ezüst Szürke | Ibolya | Keki | Kék | Narancs | Rózsaszín).
2. **Szolgáltatások** — optional multi-select (observed list: Damilos keret beküldve ·
   Decentrálás · Egyedi bázisgörbület · Élre vékonyítás · Fúrt keret beküldve · Precal ·
   Súlylencse · Szélvastagság (damilszél) · …).
3. **Szín** — tint catalogue (Színezés nélkül · Sport Narancs · Sport Sárga · Xperio
   barna 12/18/35/62/75% · …).
Running total updates live (63 000 frame + 94 600 lens = **157 600 Ft** green tag).
"Egyéb cikk hozzáadása…" adds arbitrary items to the same offer.

→ Szempont mapping: this validates the pair-first finder AND adds the missing shape —
the M2 UI's real unit is the **offer card** (frame slot + lens slot + option layers +
misc items + live total), with **multiple competing offer variants per customer** and
one-click accept-to-order. The mandatory-choice vs optional vs tint option taxonomy maps
directly onto our surcharge model (needs a `choice_group` concept: exactly-one-of).

## 22. Illesztési adatok (fitting) modal — the M7/lens-order parameter dictionary

Banner: **import from centering device and tracer** ("Centrálóberendezésről és tracerről
érkezett adatok importálásához…"). Sections:
- **Online lencserendeléshez szükséges**: Normál PD (jobb/bal) mm · Illesztési magasság
  (jobb/bal) mm — the minimum set.
- **Trace adatok** (frame trace; "Trace adat nem elérhető" when absent).
- **Opcionális** + **További paraméterek** — the full individualized-lens dictionary
  (~35 fields, many per-eye): LC távolság · Íveltségi szög · Pantoszkópikus szög ·
  Hídméret · Karika magasság/szélesség · Addíció mérési metódus · Átmenetes szín axis ·
  Bázis görbület · Beltéri távolság · Ccode · Csatornahossz (+közeli/közép/messzi) ·
  Domináns szem · Élvastagság · Fej dőlésszög · Fejforgás szög · Framefit ·
  Horizontális decentrálás · Keret anyag · **Kialakítási változat kód (Hoya)** ·
  Közeli tárgy távolsága · Közelre tekintési szokások · Márkajel · Mélyítés ·
  **METS (Hoya)** · Munkatávolság · Optimalizált átmérő · Szélkiegyenlítő prizma ·
  Szem forgáspont B'/Z' · Vastagság középen · Megjegyzés.
→ This is the field dictionary for `szempont` fitting data + the supplier lens-order
payload (M7 + the Lencserendelés flow). Hoya-specific fields confirm per-supplier
parameter extensions — adapter-friendly design required, not a fixed schema.

## 23. Adatintegráció — the live ClearVis→ERP bridge and its failure queue

"Adatküldési feladatok": failed/skipped transfer jobs with retry ("Ismét sorba állítás")
and delete. Observed: **Számla átadása EOPT-2025-xxx** failing on
`INSERT INTO eoptika_customer (erp_id, created, customer_id, payer_address_id)` (SQL
errors), and "Not found erp id for orderLine" from `PaymentXmlFactory.php`; also
**Selejtezés átadása MO-xxx**. Jobs sit as **Kihagyva** since January 2025.
→ M11 reality check: the incumbent CV→Tharanis sync has a manual retry queue with
long-lived skipped items; migration reconciliation must not assume ClearVis-side data
fully reached the ERP. Also confirms invoice + customer + selejtezés are the transfer
object types.

## 24. Product stock ledger (per product, per store)

Product page shows: stock **"1177 (1174 szabadon)"** = total (free) — reservation pool
explains the difference; **Beszerzési ár with date** (45 HUF, 2025.08.29.);
**Foglalások az üzletben** table (reservations: date, SO-bizonylat, type, −db,
kiszerelés, partner, rögzítette/lezárta); **Mozgások az üzletben (legutóbbi 10)**
ledger linking SO/MO documents to EOPT invoices with partner + operator. Health-fund
partner strings appear here too ("Otp Egészségpénztár (Tóth Bálint Csaba / Ep203001324)").
→ M10 read-model target: per-SKU per-location ledger with reservation vs free split,
document-linked.

## 25. Batch-3 findings F21–F27

| # | Finding | Spec impact |
|---|---|---|
| F21 | Multiple parallel offer variants per customer with carousel + accept-one | M2 UI: quote page → offer-variant model (matches spec compare req., stronger) |
| F22 | Correction-type colour coding used as primary navigation cue everywhere | Atlas adaptation: keep a colour accent per order type (within Atlas palette) |
| F23 | Mandatory-choice option groups on lens products ("Választandó Szolgáltatások") | pricing model: add exactly-one-of choice_group to surcharges |
| F24 | "Hozott keret" + per-eye minimum diameter from frame + "Nincs készletmozgás" | M2 quote: own-frame flag; frame→lens diameter constraint feeds the finder |
| F25 | Lens source Rendelésből/Készletről per line + per-eye stock panel in CL Rx form | finder/quote: stock-source field; ties to Glasson-pattern stock visibility (W3/M10) |
| F26 | Javasolt kontroll időpontja captured at Rx entry | recall/retention hook — IRIS/GC comms feed, capture in quote/order now |
| F27 | Szemcsepp + Ápoló folyadék prompts inside CL Rx form | cross-sell capture at the right moment; cheap M2 addition |

## 26. Coverage status

Seen: shell/session, full menu, home, vevő adatlap + timeline, orders (list, CL detail,
glasses detail), ajánlat wizard end-to-end incl. Rx forms + fitting modal, products
(3-level model + stock ledger), készletvezetés ops, eladás/register + invoice,
kimutatások, munkatársak/roles, üzletek/locations, kedvezmények + rule editor,
rendszerbeállítások (overview), profile/device settings, adatintegráció queue.
**Still unseen** (acceptable residual): vizsgálat detail form (exam protocol — Fovea/IRIS
territory anyway), printed munkalap output, napi zárás flow detail, időpontfoglalások.
