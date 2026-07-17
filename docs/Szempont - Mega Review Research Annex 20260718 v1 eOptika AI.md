# Szempont — Mega Review Research Annex

**Date:** 2026-07-18 · **Version:** v1 · **Status:** research annex (no decisions made here)

Pre-drafted researchable groundwork for seven questions of the founder decision brief. Every factual claim carries a source URL; conflicting or stale sources are flagged inline; anything unverifiable is listed under OPEN / NEEDS HUMAN CONFIRMATION, never stated as fact. Web research performed 2026-07-17. This annex changes no code and makes no product decisions.

---

## 1. Hungarian VAT on optical products (5% gyógyászati segédeszköz kör)

### FINDING

**The flat 27% currently charged is correct under the law in force (consolidated text 2026.VII.1–VIII.31, checked 2026-07-17).**

- Rate structure (Áfa tv. 82. §): 27% standard; 5% = 3. melléklet; 18% = 3/A; 0% = 3/B.
- **3. melléklet I. rész** (5% goods, 60 rows) contains no row for szemüveglencse, kontaktlencse, szemüvegkeret or szemüveg. The only vision-related items are aids for the blind (rows 7–14: Braille eszközök, fehér bot, stb.). A full-text grep of the consolidated act confirms the strings "szemüveglencse" and "kontaktlencse" do not occur anywhere in it, and vtsz 9001 (lenses incl. contact/spectacle) and 9021 (orthopaedic appliances) are not referenced in the act.
- **3. melléklet I/A. rész** (5% gyógyászati segédeszközök) is a **closed 19-row list identified by ISO (GYSE functional-group) code**, frozen to the **2012. január 1. state of 14/2007. (III. 14.) EüM rendelet 10. számú melléklete** — not tied to current NEAK/SEJK support status and not to vámtarifaszám. The **only optical item is row 18, "Távcsőszemüvegek" (ISO 21 03 21)** — telescopic low-vision spectacles.
- There is **no general "rendelésre készült / egyedi méretvétel = 5%" rule**. The phrase "egyedi méretvétel alapján egyedileg készített" appears only inside two specific orthosis rows (boka-láb 06 12 06 09, csípő 06 12 15 09) as part of those product descriptions. A custom-made prescription lens does not qualify by being custom-made.
- Consequently the "well-known rate split" does not exist in current law: keret 27%, lencse 27%, kontaktlencse 27%, komplett szemüveg 27%, szemüvegkészítés munkadíja 27%. The composite-supply question is rate-neutral today.
- Claims in circulation (including AI-generated search summaries encountered during research) that "szemüveglencse és kontaktlencse 5%" or "TB-támogatással értékesített keret 5%" are **contradicted by the primary text** — no such rows exist.
- 2020–2026 changes to the annexes were elsewhere (housing, meats, desszert sajtkészítmény 2024, szarvasmarha húsa 5% from 2026-01-01); **none of the 19 I/A rows carries any amendment footnote** — the list is identical in the NAV rate summary (2022-02-01), the Szamlazz.hu table (2023-09) and the July 2026 consolidated text.
- Adjacent nuance (service side, not product): humán-egészségügyi services are VAT-exempt under 85. § (1) b)–c) — potentially relevant to látásvizsgálat / kontaktlencse-illesztés fees as an *exemption* question, not a rate question.

### SOURCES

- Áfa tv. consolidated text (in force 2026.VII.1–VIII.31): https://net.jogtar.hu/jogszabaly?docid=a0700127.tv (njt.hu mirror: https://njt.hu/jogszabaly/2007-127-00-00 — unreachable from the research environment at the time; jogtar used)
- NAV rate summary PDF (2022-02-01, reproduces I/A list verbatim): https://nav.gov.hu/pfile/file?path=%2Fugyfeliranytu%2Fadokulcsok_jarulekmertekek%2Fafakulcs_adomen%2FAfa_kulcsok_es_a_tevekenyseg_kozerdeku_vagy_egyeb_sajatos_jellegere_tekintettel_adomentes_tevekenysegek_kore
- Szamlazz.hu 5% table (2023-09, secondary corroboration): https://www.szamlazz.hu/wp-content/uploads/2023/09/5sz-afakulcs_tablazat-2023_A4.pdf
- 14/2007. (III. 14.) EüM rendelet: https://net.jogtar.hu/jogszabaly?docid=a0700014.eum
- NAV 2022/4. Adózási kérdés (szemüveg, but SZJA context — shows existing NAV szemüveg guidance is not about output VAT): https://nav.gov.hu/ado/adozasi_kerdes/20224.-Adozasi-kerdes---A-szemeszeti-szakvizsgalat-meghatarozasa-az-eleslatast-biztosito-szemuveg-adomentes-juttatasa-kapcsan
- Adó Online (2018, GYSE VAT reduction remained a proposal): https://ado.hu/ado/csokkenhet-a-gyogyaszati-segedeszkozok-afaja/
- Optikai Magazin (TB szemüveg-támogatás withering, industry press): https://www.optikaimagazin.hu/milyen-ut-vezetett-a-szemuveg-tamogatas-megszunesehez

### DRAFT ANSWER

Keep charging 27%. There is no 5% optimization available for ordinary prescription lenses or contact lenses; the only 5% optical item is távcsőszemüveg (ISO 21 03 21). Neither NEAK support status nor custom-made character confers 5%. No retroactive over-declaration exists (27% was and is correct). Two follow-ons worth pursuing with the accountant: (a) whether optometrist service fees can be áfamentes under 85. § (1) c); (b) if the store ever dispenses an I/A-listed device, the pricing engine needs a per-SKU VAT field rather than a hard-coded 27% (it should have one anyway).

### OPEN / NEEDS HUMAN CONFIRMATION

- Historical rates pre-2013 (origin of the "lencse is 5%" folklore) not verified — do not rely on statements about past rates without checking time-states.
- Exact ISO codes of ordinary szemüveglencse/kontaktlencse in the frozen 2012-01-01 annex were not extracted (verified only that they are not among the 19 listed).
- Whether any NEAK support currently exists for ordinary glasses/contacts (children, aphakia, keratoconus) — irrelevant to VAT either way, but unverified.
- The 2026.IX.1 time-state of the Áfa tv. could not be opened (subscription-gated); transitional provisions indicate it concerns invoice data reporting, not rate annexes — not inspected directly.
- VAT-exemption of optometrist services in a retail optika context — plausible, not researched to a conclusion; covered by the accountant question.

### ACCOUNTANT QUESTION (ready to send, Hungarian)

> **Tárgy: Optikai termékek áfakulcsa — 5%-os gyógyászati segédeszköz kör alkalmazhatósága**
>
> Kedves Könyvelőnk!
>
> Optikai kiskereskedelmi tevékenységünkben (Teréz körúti üzlet + webshop) jelenleg minden terméket és szolgáltatást egységesen 27% áfával számlázunk: szemüvegkeret, receptre készült (egyedi méretvétel alapján gyártott/csiszolt) szemüveglencse, komplett dioptriás szemüveg, kontaktlencse, ápolószerek, valamint a szemüvegkészítési munkadíj.
>
> Kérjük, erősítsék meg vagy cáfolják az alábbi értelmezésünket:
>
> 1. Az Áfa tv. (2007. évi CXXVII. tv.) 3. számú melléklet I/A. része alapján 5%-os kulcs kizárólag az ott ISO-kóddal felsorolt 19 gyógyászatisegédeszköz-csoportra alkalmazható (a 14/2007. (III. 14.) EüM rendelet 2012. január 1-jén hatályos 10. számú melléklete szerinti körből), és ebből optikai termék egyedül a „Távcsőszemüvegek" (ISO 21 03 21). Helyes-e, hogy a normál szemüveglencse, a kontaktlencse, a keret és a komplett szemüveg — akár egyedi méretvétel/rendelés alapján készül, akár raktári — nem tartozik az 5%-os körbe, tehát 27%?
> 2. Változtat-e ezen bármit, ha az adott lencse/eszköz szerepel a NEAK által támogatott gyógyászati segédeszközök (SEJK) aktuális listáján, vagy ha TB-támogatással kerül kiszolgáltatásra?
> 3. A szemüvegkészítés munkadíja (csiszolás, keretbe illesztés) megítélésük szerint a termékértékesítés adóalapjának része-e (egységes 27%-os ügylet), vagy külön szolgáltatásként számlázandó — és van-e ennek bármilyen áfakulcs-következménye?
> 4. A szolgáltatási oldalon: az optometrista által végzett látásvizsgálat, illetve kontaktlencse-illesztés díja kezelhető-e adómentesen az Áfa tv. 85. § (1) bekezdés c) pontja (humán-egészségügyi tevékenység) alapján, és ha igen, milyen feltételekkel (személyi/tárgyi feltételek, levonási hányad hatása)?
> 5. Amennyiben a jövőben az I/A. rész alá tartozó eszközt (pl. távcsőszemüveget) értékesítenénk, milyen bizonylatolási/nyilvántartási feltételekkel alkalmazható az 5%?
> 6. Jól látjuk-e, hogy mivel a 27% a helyes kulcs, visszamenőleges önellenőrzési kötelezettség vagy lehetőség e körben nem merül fel?
>
> Válaszukat a pénztárgép/számlázó rendszerünk áfakulcs-beállításainak véglegesítéséhez kérjük.
>
> Köszönettel, eOptika

---

## 2. Szamlazz.hu Számla Agent capabilities

Live docs: https://docs.szamlazz.hu/ (Agent: https://docs.szamlazz.hu/agent); knowledge base https://tudastar.szamlazz.hu/gyik. One XML per document, HTTPS multipart POST to `https://www.szamlazz.hu/szamla/`; the form field name selects the action (https://docs.szamlazz.hu/agent/basics/sending-requests).

### FINDING

**Előlegszámla → végszámla:** fully supported in the invoice XML (`xmlszamla`, field `action-xmlagentxmlfile`). Header flags `<elolegszamla>true`, `<vegszamla>true`; the **primary link is `<rendelesSzam>`** (order number carried on both documents). The current XSD also documents `<elolegSzamlaszam>` — explicit advance-invoice-number reference "if the down-payment invoice to be closed cannot be identified by order number". The final invoice carries the advance as a negative line + full price as positive line. **Limitation:** multiple advances cannot be auto-consolidated into one final invoice ("Sajnos egyelőre a Számlázz.hu nem képes arra, hogy több előlegszámla alapján elkészítsen egy darab végszámlát"); the documented workaround is final-invoicing against the last advance and manually adding earlier advances as negative lines under the same order number. *Conflict flag:* the tudástár FAQ ("csak a rendelésszámmal") predates `elolegSzamlaszam` in the XSD; treat `rendelesSzam` as primary, `elolegSzamlaszam` as documented fallback.

**Storno:** dedicated action `xmlszamlast` / `action-szamla_agent_st` with `<szamlaszam>` of the invoice to reverse. **Storno-of-storno: NO** — tudástár is explicit: "a sztornózó számlát nem tudod újabb sztornóval vagy helyesbítő számlával javítani"; recovery from a mistaken storno is issuing a new invoice referencing both prior documents in a remark.

**Nyugta via Agent:** four actions — create (`xmlnyugtacreate` / `action-szamla_agent_nyugta_create`, with `hivasAzonosito` idempotency-style call ID, `elotag` prefix, free-text `fizmod`, PDF templates incl. 80mm), storno (`xmlnyugtast`), query (`..._nyugta_get`), send-by-email (`xmlnyugtasend`). **E-nyugta 2026:** mandatory receipt-data reporting starts **2026-09-01** for manual and computer-issued receipts (NAV KOBAK, daily VAT-rate-summarized, within 3 days); Szamlazz.hu's blog (2026-07-01) commits "A Számlázz.hu 2026. szeptember 1-től automatikusan biztosítja a kötelező adatszolgáltatást" and a cloud e-pénztárgép product is in the works (https://enyugta.szamlazz.hu/). The Agent receipt doc pages do not yet mention this — doc gap flagged.

**Prefix / számlatömb:** per-call `<szamlaszamElotag>` selects "one of the prefixes from the invoice pad menu" — prefixes must first be configured in the web UI (Számlatömbök); any configured prefix is then selectable per Agent call (docs explicitly recommend separate prefixes per website/channel). Receipts: analogous required `<elotag>`. No API to create a prefix.

**Test/sandbox:** **no sandbox endpoint or test agent key** — the whole account is switched to **Tesztüzem**. For a live company: create a separate test account (same tax number allowed) and switch it to test mode; on switching back, all test documents are deleted and the same API parameters continue to work live. Testing in a live account is explicitly warned against. Test rate limit: 100 invoices/hour. A test-mode account is not connected to NAV Online Számla (the system blocks issuing reporting-liable invoices until the NAV link exists), so test documents generate no NAV reporting — but no verbatim "never reported" sentence was found (see OPEN).

**NAV Online Számla:** confirmed automatic for all Szamlazz.hu-issued invoices (Agent included): "Ha a jogszabályi feltételek megkövetelik, a Számlázz.hu automatikusan továbbítja a számlaadatokat a NAV-nak." Precondition: the account is linked with a NAV technical user (technikai felhasználó + aláírókulcs + cserekulcs under Beállítások / NAV online adatkapcsolat). No NAV-related field exists in the Agent XML.

**Auth & libraries:** current method is the **Számla Agent kulcs** in `<szamlaagentkulcs>` (generated in the web UI; **accepted lowercase only** per docs). Username/password is legacy/third-party-invoicing only. The only official client is the PHP API (v2.12.3, 2026-05-20, https://docs.szamlazz.hu/php); no official Python client — build XML directly.

### SOURCES

- https://docs.szamlazz.hu/agent/generating_invoice/xml · https://docs.szamlazz.hu/agent/generating_invoice/xsd (elolegSzamlaszam)
- https://tudastar.szamlazz.hu/gyik/vegszamlan-kotelezo-rendelesszam · https://tudastar.szamlazz.hu/gyik/tobb-elolegszamla-vegszamlazasa · https://tudastar.szamlazz.hu/gyik/elolegszamla-vegszamla-kiallitasa
- https://docs.szamlazz.hu/agent/reversing_invoice/xml · https://docs.szamlazz.hu/agent/basics/sending-requests · https://tudastar.szamlazz.hu/gyik/sztornozas · https://tudastar.szamlazz.hu/gyik/teves-sztornozo
- https://docs.szamlazz.hu/agent/generating_receipt/xml · https://docs.szamlazz.hu/agent/reversing_receipt/xml · https://docs.szamlazz.hu/agent/sending_receipt/xml
- https://www.szamlazz.hu/blog/2026/07/kotelezo-nyugtaadat-szolgaltatas-2026-szeptember-1-tol-kiket-erint-es-mi-a-teendo/ · https://enyugta.szamlazz.hu/ · https://nav.gov.hu/ado/enyugta
- https://docs.szamlazz.hu/agent/basics/details (multi-website prefixes; 100/h test limit) · https://tudastar.szamlazz.hu/gyik/teszt-api-hozzaferes · https://tudastar.szamlazz.hu/gyik/teszt-fiok-fejleszteshez · https://www.szamlazz.hu/egyedi-megoldasok/szamla-agent/
- https://tudastar.szamlazz.hu/gyik/nav-online-szamla-adatszolgaltatas · https://tudastar.szamlazz.hu/gyik/szamlazasi-fiokomat-hogyan-tudom-osszekotni-a-nav-online-szamla-rendszerevel · https://www.szamlazz.hu/szamla/tudastar/navonline
- https://docs.szamlazz.hu/agent/basics/authentication · https://docs.szamlazz.hu/php

### DRAFT ANSWER (recommended POS invoice flow)

1. Vendor behind the existing adapter; auth via Agent kulcs from Secret Manager (lowercase); plain XML-over-HTTPS in Python (only official lib is PHP — no unofficial dependency).
2. Dedicated prefixes pre-created in the web UI (e.g. store invoices, advances, receipts) and passed per call — isolates POS series from webshop series on one account.
3. Deposit flow: advance with `elolegszamla=true` + mandatory `rendelesSzam` = Szempont order ID; final with `vegszamla=true` + same `rendelesSzam` (belt-and-braces: also `elolegSzamlaszam`). Multi-installment: final against the last advance, earlier advances as manual negative lines. Persist returned invoice numbers.
4. Storno confirm-gated and treated as irreversible in the UI (no storno-of-storno exists; the only "undo" is a new invoice).
5. Receipts via `xmlnyugtacreate` with `hivasAzonosito` = idempotent POS transaction ID; plan for the 2026-09-01 receipt-reporting regime and verify Szamlazz's automatic handling landed before go-live.
6. NAV reporting: zero code — but make the NAV technical-user link a deployment checklist item (unlinked accounts cannot issue reporting-liable invoices at all).
7. Staging → dedicated Tesztüzem account, never the live one; respect 100/h test limit.

### OPEN / NEEDS HUMAN CONFIRMATION

- Exact Composer package name of the official PHP API (two fetches disagreed: `kboss/szamlaagent_v2` vs `kboss/szamlazzhu_v2`; install page 403 to bots). Moot if building XML directly.
- Explicit statement that test-mode invoices are never NAV-reported — strongly implied, no verbatim sentence; confirm with Szamlazz support before citing in compliance docs.
- Whether the agent key survives the test→live account switch unchanged ("API paraméterek megváltoztatása nélkül" implies yes; not explicit).
- `elolegSzamlaszam` behavior vs the older "rendelésszám only" FAQ — run a test-account experiment before relying on it.
- Agent-issued receipts under the 2026-09-01 regime: blog pledge, not yet in Agent docs — re-check near September 2026.

---

## 3. Egészségpénztár merchant invoicing (OTP, Prémium, Gondoskodás ex-MKB-Pannónia)

### FINDING — per fund (do not blend)

**OTP Egészségpénztár** (single rule, no product/service split published — "Egészségpénztári Kisokos" IV.):
- Invoice must show the fund as vevő: "OTP Egészségpénztár, 1138 Budapest, Váci út 135–139., adószám: 18105564-2-41", plus "a pénztártag nevét és valamely azonosítóját (tagsági okirat számát, OTP Egészségkártyája számát, lakcímét vagy adóazonosító jelét)"; kedvezményezett: name + TAJ. Exact product/service naming required. Incorrect invoices are rejected.
- Card (egészségkártya) at contracted merchant: POS swipe or phone authorization; **"A számlát a szolgáltató juttatja el a Pénztárhoz"** — card authorization does NOT replace the invoice; merchant still invoices the fund as vevő and submits. Cash/bank-card/transfer purchases: the member submits the invoice (transfers: attach statement or print "pénzügyi teljesítést nem igényel").
- Optics: szemüveg, kontaktlencse + ápolószer eligible; szemüveg "optometrista javaslata alapján is" elszámolható; napszemüveg "egészségvédelmi céllal" (recommendation required). Member-submitted route works at any optika without a merchant contract; contract (free; 2%+ÁFA fee on EP-card transactions only) needed only for card acceptance.
- Deadlines: member invoices accepted until June 30 of the 5th year after issue; the orvosi javaslat must be in the same name and dated ≤ invoice date; payout ≤ 15 (self-aid 25) working days.

**Prémium Egészségpénztár** (split by purchase type — member page "Számlakérés/számlabeküldés"):
- **Termék** (covers glasses/contact-lens retail): vevő = **the member** (or registered close relative) with name + address, plus the member's **tagi azonosító** on the invoice.
- **Szolgáltatás**: vevő = "Prémium Egészségpénztár, 1138 Budapest Dunavirág utca 2-6., adószám: 18177734-2-41" + member name + tagi azonosító.
- Card acceptance (merchant contract EP014 + card annex, public PDF): fedezetellenőrzés → immediate zárolás → slip in 2 copies (member signs one) → merchant invoices "az Egészségpénztár nevére és címére" with member name + pénztári azonosító (2.9.4) and **the transaction authorization number written on the invoice** or the signed slip attached (2.9.5); merchant mails invoice + slip; fund pays within 15 days minus fee (POS/voice 2%+ÁFA; internet 10 Ft + 0.5% + ÁFA; cash at contracted partner 1%+ÁFA). Free EDI e-invoicing via Egészségpénztári Elszámoló Központ Kft. **Conflict flag:** the card annex says card invoices name the FUND, while current member/pharmacy pages say termék → MEMBER as vevő; the e2k contract PDF may be an older version (it also carries the old Váci út address) — see OPEN.
- Optics: szemüveg, kontaktlencse, napszemüveg, tárolófolyadék "csak szakorvosi javaslatra" (stricter wording than OTP; downloadable form).
- Deadlines: member invoices must arrive by Dec 31, 14:00 of the year following the invoice date. Partner onboarding via szolgaltato@premium.hu / +36 1 580 2298; contract indefinite, 60-day notice.

**Gondoskodás Egészségpénztár** (ex MKB-Pannónia → MBH Gondoskodás 2023-05-01 → Gondoskodás 2025-12-31; adószám unchanged 18232761-1-41):
- **From 2026-07-01 only invoices naming "Gondoskodás Egészségpénztár" as vevő are accepted** — old names rejected. (Sourced from search-indexed content of their JS-only page — verify live, see OPEN.)
- Split by type (official "Iránytű" download, still MBH-era name): szolgáltatás → fund as vevő ("MBH Gondoskodás Egészség- és Önsegélyező Pénztár, 1134 Budapest, Váci út 23-27., adószám: 18232761-1-41") + member name + tagi azonosító; **termék → member as vevő** (name + address). Without a számlaelszámolási nyilatkozat on file, the tagi azonosító must be on the invoice confirmed by the member's signature.
- Card (legacy MKB merchant contract, public at e2k.hu): POS or phone authorization = zárolás; merchant invoices every card payment, sends invoices + signed slips at least monthly; fund pays correct invoices within 25 days; deficient ones returned for correction within 10 munkanap; **zárolás lapses by law on day 181** — after that the fund only pays up to the member's remaining balance and the merchant bears the shortfall risk. Cash refunds to members forbidden; corrections via helyesbítő számla.

**Cross-check vs the incumbent:** the ClearVis-era payer format "OTP Egészségpénztár (Member Name / MemberID)" **matches OTP's rule** (fund as vevő + member name + ID somewhere on the invoice) but is **wrong as a universal pattern** — Prémium and Gondoskodás require the member as vevő for termék purchases, which is most of what an optika sells.

### SOURCES

- OTP Kisokos (all OTP quotes): https://www.otpegeszsegpenztar.hu/static/otpegeszseg/sw/file/ep_kisokos.pdf
- OTP számlakiállítás: https://www.otpegeszsegpenztar.hu/hu/penztartagok/szamlakiallitas · https://www.otpegeszsegpenztar.hu/hu/uj-belepok/szamlakiallitas
- OTP merchant/elfogadóhely: https://www.otpegeszsegpenztar.hu/hu/szolgaltatok · https://www.otpegeszsegpenztar.hu/hu/elfogadohely
- OTP optics: https://www.otpegeszsegpenztar.hu/hu/szolgaltatasok/szemuveg-gyogyaszati-termekek (cross-check https://biztosdontes.hu/cikkek/szemuveg-akcio-egeszsegpenztarral)
- Prémium számlakérés: https://premiumegeszsegpenztar.hu/szamlakeresszamlabekuldes · szolgáltatóknak: https://premiumegeszsegpenztar.hu/szolgaltatoknak · onboarding: https://premiumegeszsegpenztar.hu/legyel-partnerunk
- Prémium szerződés EP014 (card annex): https://e2k.hu/assets/pdf/PremiumEP.pdf · szemüveg blog: https://premiumegeszsegpenztar.hu/blog/kell-egy-uj-szemuveg
- Gondoskodás Iránytű: https://webapi.gondoskodasegeszsegpenztar.hu/publicapi/download/document/iranytu · számla elszámolás (JS page): https://www.gondoskodasegeszsegpenztar.hu/tagok/szolgaltatasok/szamla-elszamolas
- MKB-Pannónia legacy merchant contract: https://www.e2k.hu/assets/pdf/Mkb.pdf
- Incumbent behavior cross-check (eOptika's own page): https://eoptika.hu/egeszsegpenztarak

### DRAFT ANSWER — what the Szempont invoice template must support

1. **Per-fund, per-type vevő profiles** in fund master data: `vevo_mode ∈ {fund, member}` keyed by (fund, termék/szolgáltatás). OTP: always fund. Prémium/Gondoskodás: termék→member, szolgáltatás→fund.
2. **Effective-dated fund identity** (name, address, adószám) — Gondoskodás rejects old names from 2026-07-01; Prémium's address changed between contract PDF and current site. Maps directly onto the project's effective-dated-tables rule.
3. **Member identification block** printable regardless of vevő mode: member name + ID with per-fund ID semantics (OTP: any of tagsági okirat szám / EP-kártyaszám / lakcím / adóazonosító; Prémium & Gondoskodás: tagi azonosító). Kedvezményezett: name + TAJ (OTP).
4. **Card-transaction fields**: authorization number line (Prémium contractual requirement) or attached signed slip; track merchant-submitted card invoices against the statutory 180-day zárolás window.
5. **Rx linkage**: exact product naming; orvosi javaslat flag with validations (same name as invoice, javaslat date ≤ invoice date per OTP); napszemüveg only with recommendation.
6. **Free-text clause**: "pénzügyi teljesítést nem igényel" for transfer-paid invoices (OTP).
7. **Two flows**: member-submitted (cash/card — member's deadlines) vs merchant-submitted (egészségkártya — POS batches invoices + slips to the fund).

### OPEN / NEEDS HUMAN CONFIRMATION

- **Prémium card-paid termék purchases**: contract annex says invoice to the FUND, current pages say termék → MEMBER — confirm with szolgaltato@premium.hu which applies to card-paid optical products and get the current contract version.
- OTP merchant-contract specifics (card-invoice submission deadline/channel) are behind the contract; the 180-day statutory zárolás is the only hard public backstop.
- Gondoskodás 2026-07-01 name rule and current registered address — verify on the live page (content came from search index of a JS-only page).
- Termék vs szolgáltatás classification of prescription glasses per fund (determines vevő mode at Prémium/Gondoskodás) — not unambiguously defined publicly.
- Whether OTP requires the member ID in a specific position (vevő block vs comment) — only "a számlán" is stated; the incumbent's parenthetical format appears acceptable but position is not formally prescribed.

---

## 4. GCP IAP for a shared store terminal

### FINDING

**JWT verification:** Google's current guidance is explicit — the app **must validate `x-goog-iap-jwt-assertion` on every request**; the plain `X-Goog-Authenticated-User-Email` header is "available for compatibility, but you shouldn't rely on [it] as a security mechanism" ("If an attacker bypasses IAP, the attacker can forge the IAP unsigned identity headers"). Validation parameters: issuer `https://cloud.google.com/iap`, algorithm ES256, keys from `https://www.gstatic.com/iap/verify/public_key-jwk` (rotate — auto-refresh). **Audience** depends on how IAP is attached: direct-on-Cloud-Run (the newer recommended mode) uses `/projects/PROJECT_NUMBER/locations/REGION/services/SERVICE_NAME`; behind an HTTPS LB it's `/projects/PROJECT_NUMBER/global/backendServices/SERVICE_ID`. **Bypass caveat:** IAP on a load balancer does not protect the `run.app` URL — disable the default URL or restrict ingress; with direct IAP, grant invoker only to `service-PROJECT_NUMBER@gcp-sa-iap.iam.gserviceaccount.com`. Verify the JWT in-app regardless (defense in depth).

**Sessions:** for Google-account login the IAP session is tied to the underlying Google login session and "only expires when that session expires"; account-state changes propagate "within a couple minutes". Expired sessions on fetch/XHR return **401** (send `X-Requested-With: XMLHttpRequest`, include credentials); Google documents a programmatic refresh: open a window to `/?gcp-iap-mode=DO_SESSION_REFRESH` — directly relevant to a long-lived kiosk tab. IAP reauthentication policy (`reauthSettings`, maxAge ≥ 300 s) exists but should be left **unset** for a kiosk (it forces mid-day re-logins). Workspace admin: **Google Session control** (web session length, default 14 days) governs how often the kiosk must re-login to Google; the separate **Google Cloud session control** (1–24 h) is scoped to Cloud console/gcloud/Cloud-scope OAuth and does not list IAP web apps — but neither doc states the negative (see OPEN).

**Kiosk/shared-device guidance: explicit negative finding.** Google documents no IAP-specific kiosk or shared-terminal pattern (searched IAP docs, Chrome Enterprise docs, engineering blogs). ChromeOS kiosk mode and managed guest sessions run without Google sign-in and never mention IAP.

**Shared account:** Google states "Google Accounts are intended for use by only one person" (support recommendation, **not** a ToS prohibition — the Workspace ToS only restricts fee-avoidance multi-accounting; one shared account = one paid license). Costs: IAP/Cloud audit logs record one `principalEmail` for everything (per-operator attribution must come from the app layer), and login challenges/2SV on a shared credential are the documented lockout risk; a security key left at the till is workable but weakens 2SV to "possession of the till".

### SOURCES

- Signed headers / JWT: https://docs.cloud.google.com/iap/docs/signed-headers-howto · identity headers warning: https://docs.cloud.google.com/iap/docs/identity-howto · samples: https://docs.cloud.google.com/iap/docs/samples/iap-validate-jwt
- IAP for Cloud Run (ingress, default-URL, invoker SA): https://docs.cloud.google.com/iap/docs/enabling-cloud-run
- Sessions (401/XHR, DO_SESSION_REFRESH): https://docs.cloud.google.com/iap/docs/sessions-howto · reauth: https://docs.cloud.google.com/iap/docs/configuring-reauth
- Google Session control (14-day default): https://support.google.com/a/answer/7576830 · Google Cloud session control (1–24 h): https://support.google.com/a/answer/9368756 · ACM session controls: https://docs.cloud.google.com/access-context-manager/docs/session-controls-for-reauthentication
- Shared accounts: https://support.google.com/a/answer/33330 · Workspace ToS: https://workspace.google.com/terms/premier_terms/ · IAP audit logs: https://docs.cloud.google.com/iap/docs/audit-log-howto
- Managed guest sessions: https://support.google.com/chrome/a/answer/3017014 · kiosk internals: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/enterprise/kiosk_public_session.md · 2SV: https://support.google.com/a/answer/175197
- (Note: `cloud.google.com/iap/docs/...` 301-redirects to `docs.cloud.google.com/...`; support.google.com/a articles redirect to knowledge.workspace.google.com — pin the stable forms above.)

### DRAFT ANSWER

The shared-Workspace-account + in-app operator picker + per-action PIN pattern is **sound**, as a perimeter/attribution split: IAP answers "is this device allowed in", the app answers "which human clicked". Google documents no kiosk pattern for IAP, so this is a design decision, not a documented best practice; the shared account deviates from Google's one-person-per-account *recommendation* (not ToS). Requirements on the app/infra:

1. Verify `x-goog-iap-jwt-assertion` on every request (ES256, correct audience for direct Cloud Run IAP, JWKS auto-refresh); never authorize from the plain email header.
2. Close the bypass: invoker restricted to the IAP service agent; disable/restrict the `run.app` URL if an LB is ever in front.
3. Treat IAP identity as **terminal identity**; operator + PIN result + terminal principal all go into `szempont.audit_log` for sensitive actions (discounts, cancellations). PINs rate-limited, hashed, short step-up TTL.
4. Handle 401 on fetch (`X-Requested-With`) and recover via `/?gcp-iap-mode=DO_SESSION_REFRESH`.
5. Leave IAP reauth unset; long Google Session control (14-day default is fine); 2SV via a security key kept at the till or an OU exemption if the physical-store threat model justifies it.

Alternative (only if per-person infra-level audit becomes mandatory): per-operator Google logins with profile switching — nothing Google documents makes that fast enough for a POS counter.

### OPEN / NEEDS HUMAN CONFIRMATION

- Whether Workspace "Google Cloud session control" (1–24 h) binds IAP browser sessions — neither doc states the negative; **empirically test on staging** (set the shared account's OU to 1 h and watch for mid-day 401s). This is the one setting that could silently force mid-day re-logins.
- Exact periodic-refresh interval of an IAP session — undocumented.
- Reauth maxAge maximum — undocumented (minimum 300 s).
- Whether login challenges trip on a fixed-IP store terminal in practice — confirm during pilot (security key + stable network as mitigation).
- Cloud Run direct-IAP GA status per region — check release notes before production rollout.

---

## 5. Unas API v2 testing options (contingency only — kept short)

### FINDING

- **Test facility:** free trial/test shop, converted by Unas to "developer status" on request (with demo integration files); development/testing happens there. **No dry-run/test flag exists on setOrder** — the test environment is the shop, not a mode. Production integrations require fixed IP(s) reported to Unas.
- **Rate limits** (per tier, per IP, per shop): PREMIUM 2,000/h, VIP 6,000/h; failed logins max 5/h; login token valid ~2 h; 20 failed calls per endpoint → 1-hour per-shop IP ban; 10 unidentifiable calls in 10 min → 2-hour full ban; 128 MB max XML; API requires PREMIUM or VIP package.
- **setOrder required fields:** no formal required/kötelező list is published; the official `Action=add` example includes Date, Lang, Customer (contact + invoice/shipping addresses), Currency, Payment, Shipping, SumPriceGross, Items (Id/Sku/Name/Unit/Quantity/PriceNet/PriceGross/Vat/Status). Special line Ids: `handel-cost`, `shipping-cost`, `discount-amount`, `discount-percent`.
- **Email suppression: yes, per order** — SET-only fields `OrderEmail.Customer` (yes/no), `OrderEmail.Admin` (yes/no), `StatusEmail` (yes/no) control whether order-created and status emails are sent for API-created orders.
- **Auth:** per-shop API key (admin → Külső kapcsolatok → API kapcsolat) exchanged via `login` for a ~2-hour token; username/password is legacy.

### SOURCES

https://unas.hu/tudastar/api/limitaciok · https://unas.hu/tudastar/api/azonositas · https://unas.hu/tudastar/api/azonositas-login-keres · https://unas.hu/tudastar/api/megrendelesek-adatszerkezet · https://unas.hu/tudastar/api/megrendelesek-peldak · https://unas.hu/tudastar/integracio/elso-lepesek · https://unas.hu/tudastar/rendeles/tesztaruhaz-nyitas · https://api.unas.eu/shop/?wsdl (tudastar pages are public but JS-rendered — full text is in raw HTML, not visible to simple fetchers)

### DRAFT ANSWER

If (and only if) the Unas route is chosen: develop against a dedicated developer test shop; always set `OrderEmail.Customer=no`, `OrderEmail.Admin=no`, `StatusEmail=no` explicitly on POS-created orders so no customer messaging fires; plan a static egress IP; confirm the shop's tier for the applicable rate limit. There is no sandbox mode on the live shop.

### OPEN / NEEDS HUMAN CONFIRMATION

- Exact minimal required field set for `Action=add` (undocumented — confirm empirically or via Unas support).
- eOptika's subscription tier (PREMIUM vs VIP) — check shop admin.
- Whether the fixed-IP requirement applies to merchant-own integrations or only listed third-party apps.
- Default email behavior when the suppression flags are omitted is not stated — assume emails send; always set flags explicitly.

---

## 6. Hardware shopping list (HU market, prices checked 2026-07-17)

### FINDING

**(a) Consultation tablet + swivel stand.** The Galaxy Tab A9+ (2023) is end-of-line (out of stock at Samsung HU and Euronics, live-verified); its successor **Galaxy Tab A11+ 11"** (SM-X230, 8GB/128GB, Android 16) is the current equivalent.

| Option | Price | Source | Note |
|---|---|---|---|
| Samsung Galaxy Tab A11+ 11" 128GB Wi-Fi | ~89 890 Ft | https://www.argep.hu/product_3305717.html · https://www.mediamarkt.hu/hu/product/_samsung-galaxy-tab-a11-11-128gb-wifi-szurke-tablet-sm-x230nzareue-1500872.html | price from comparison-site snippet — **needs click-through confirmation** (MediaMarkt/Alza block bots) |
| iPad 11" (A16, 2025) 128GB Wi-Fi | 209 990 Ft | https://istyle.hu/collections/ipad | live-verified, official Apple Premium Partner |
| Durable TWIST TABLE 8941-01 (360°, ≤13", not lockable) | 9 390 Ft | https://ipon.hu/shop/termek/durable-twist-table-tablet-tarto-asztali-allvany/2245945 · https://www.pcx.hu/tablet-tarto-allvany-asztali-durable-twist-table-894101-567821 | live-verified |
| Durable Tablet Holder TABLE 8930-23 (key-lockable, 360°, 7–13", anti-pull-out) | 41 000 Ft | https://arazastechnika.hu/spl/671320/Tablet-tarto | live-verified; same shop: flexible-arm 8931-23 at 53 000 Ft |

Pick rationale: Tab A11+ = current model, 8GB RAM, half the iPad's price — fine for a browser kiosk; Durable 8930-23 = the lockable one for a customer-facing counter. Compulocks/Maclocks are sold in HU but no live-confirmable price (captcha/403) — https://tablet-tarto-es-allvany.arukereso.hu/compulocks/.

**(b) Barcode scanner.** Only **2D area imagers** reliably read from backlit screens; laser scanners cannot. Both options are USB HID 2D imagers, HU listings explicitly mention reading codes from phone screens.

| Option | Price | Source | Note |
|---|---|---|---|
| Honeywell Voyager 1470g 2D (1470G2D-2USB-R) | 37 432 Ft | https://www.digicode.hu/vonalkod-olvaso-c2/honeywell-voyager-1470g-p11391 | live-verified, 5+ munkanap; distributor page https://ident.hu/termek/voyager-1470g |
| Zebra DS2208 kit (scanner + cable + stand) | 51 828 Ft | https://www.digicode.hu/vonalkod-olvaso-c2/zebra-ds2208-p2602 | live-verified; 5-yr warranty, hands-free stand |

Pick rationale: Voyager 1470g = best brand-name price/performance; DS2208 kit if hands-free munkalap scanning at the counter is wanted. Netum-class no-names ~15–25 000 Ft on eMAG unverified (bot-blocked).

**(c) Signature capture.** Recommended: **draw on the consultation tablet itself (0 Ft)** — a canvas field, finger or cheap stylus. Dedicated pad only if signing must happen while the tablet shows something else: Wacom STU-430 at 119 651 Ft (live-verified, in stock: https://pepita.hu/digitalis-rajztablak-c4571/wacom-stu-430-sign-pro-pdf-p8798567; ~86 190 Ft offers per Árukereső, bot-blocked: https://digitalizalo-tabla.arukereso.hu/wacom/stu-430-p263689911/).

Legal adequacy for GDPR nyilatkozat signing on a tablet: **adequate — and a signature is not even strictly required.** GDPR Art. 7(1) requires only demonstrability of consent (stored form + drawn-signature image + timestamp + operator ID satisfies it) — https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679. A tablet-drawn signature is a simple electronic signature under eIDAS Art. 25(1), which cannot be denied legal effect solely for being electronic — https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014R0910. Hungarian caveat: SES generally does not satisfy the Ptk. written-form requirement (https://jogaszvilag.hu/cegvilag/elektronikus-alairasok-tipusai-maganszemelyeknek-es-cegvezetoknek/ · https://fintechzone.hu/elektronikus-alairas-magyarorszagon-gyakorlati-utmutato/), but GDPR consent has no written-form requirement, so this doesn't affect the consent use case. **Critical NAIH caveat: store only the flat signature image.** Capturing dynamic characteristics (pressure, speed — what Wacom "sign pro" does for identification) is biometric data under Art. 9, on NAIH's mandatory DPIA list (https://www.naih.hu/hatasvizsgalati-lista · NAIH/2019/1074: https://www.naih.hu/files/2019-01-28-NAIH-2019-1074-biometr.pdf · practitioner guide: https://www.adatvedelmiszakerto.hu/2017/01/adatvedelmi-teendok-biometrikus-alairas-alkalmazasa-soran/).

**(d) A4 mono laser for the munkalap: 600 dpi is sufficient — confirmed.** Code-128/GS1-128 minimum X-dimension is 0.250 mm (≈10 mil); at 600 dpi one dot = 0.0423 mm, so a 10-mil module = exactly 6 dots, zero rounding error. Bar-growth/rounding "is not usually an issue with 600 dpi or greater printers" (problems arise at 203 dpi thermal) — https://www.barcodefaq.com/knowledge-base/print-quality/ · https://www.barcodefaq.com/1d/code-128/ · https://www.idautomation.com/barcode-fonts/gs1-128/user-manual/. Template rule: render Code-128 with module width an integer multiple of dots (6 or 8 dots at 600 dpi), bar height ≥ 12.7 mm, quiet zone ≥ 10× X.

| Option | Price | Source | Note |
|---|---|---|---|
| Brother HL-L2402D (1200 dpi, 30 ppm, duplex) | 44 999 Ft | https://euronics.hu/lezernyomtato/brother-hl-l2402d-lezernyomtato-p300734 | live-verified, orderable; Alza 44 990 Ft (snippet): https://www.alza.hu/brother-hl-l2402d-d8613736.htm |
| HP LaserJet M110w (600 dpi, Wi-Fi, no duplex) | ~32 890 Ft | https://www.alza.hu/hp-laserjet-m110w-d6414629.htm | snippet only — **needs confirmation**; avoid the "we" (HP+) variant (toner lock-in) |

Pick rationale: Brother = no subscription lock-in, cheap third-party toner, duplex — the boring right answer.

### DRAFT ANSWER — recommended cart

| Item | Pick | Price (gross) |
|---|---|---|
| Tablet | Samsung Galaxy Tab A11+ 11" 128GB Wi-Fi | ~89 890 Ft (confirm) |
| Stand | Durable 8930-23 lockable 360° | 41 000 Ft |
| Scanner | Honeywell Voyager 1470g 2D USB | 37 432 Ft |
| Signature | On-tablet canvas, flat image only | 0 Ft |
| Printer | Brother HL-L2402D | 44 999 Ft |
| **Total (Android route)** | | **≈ 213 300 Ft** |
| **Total (iPad route)** | iPad 11 A16 instead of Tab A11+ | **≈ 333 400 Ft** |

Budget variant (Twist Table + Tab A11+ + Voyager + HP M110w) ≈ **169 600 Ft**.

### OPEN / NEEDS HUMAN CONFIRMATION

- Tab A11+/A9+ exact prices (Alza/MediaMarkt/eMAG/Árukereső bot-blocked) — click through the listed URLs; ~80–95k Ft band expected; prefer A11+ (A9+ phasing out).
- Compulocks HU pricing if an enclosure-grade lock is wanted over the Durable 8930-23.
- Cheapest scanner tier (Netum ~15–25k on eMAG) unverified; brand-name imagers are only ~12–20k more.
- No NAIH guidance addresses *flat-image* tablet signatures specifically (their material targets biometric capture); the adequacy conclusion rests on GDPR Art. 7 + eIDAS Art. 25 + practitioner commentary. Belt-and-braces option: checkbox + operator attestation alongside the drawn signature, or a short question to the firm's DPO/lawyer.

---

## 7. ClearVisio (clearvis.io) apiV2 and data export

### FINDING

**An apiV2 exists, but public documentation covers only the appointment-booking surface; the full API docs live behind the subscriber login.**
- Base URL `https://clearvis.io/<instance>/apiV2`, API key in `X-AUTH-API-TOKEN` header + per-store `storeCode`; JSON-LD/Hydra wire format (signature of the PHP API Platform framework — which *normally* implies a fuller REST resource model, but that is inference, not documented fact).
- Publicly proven resources (from the official open-source booker client): `stores`, `appointment_calendars`, `eye_examination_processes`, `privacy_policies`, plus POSTs for customer registration and appointment creation.
- The README states: "The API itself is only available for subscribers" and "For details of the clearvis.io API see the documentation on the clearvis.io UI" — **real API docs exist inside the logged-in product**. API keys are self-service in the UI.
- Negative finding: no public Swagger/OpenAPI, no developer portal, no documented read API for customers/orders/exams/stock. docs.clearvis.io "Integrations" holds only Datagate, Hoya VisuReal, MacOS printing, and the site itself says it is "under development".

**Data export: report-shaped Excel downloads only; no documented bulk/raw export.** Documented reports (paid top tier — docs say "Gold", price page says "Fókusz", 28 000 Ft/mo): Customers (incl. recent orders/exams, XLSX, custom templates), Detailed Sales (payment-line detail incl. margin), Orders and Payments (3 worksheets: Orders/Order Lines/Sales Lines), Eye Examinations (metadata — creator, date, patient name + birth year, linked orders; **not documented as full Rx export**), Stock (full attributes incl. barcodes, tariff codes, purchase prices; XLSX/PDF). Product **import** from Excel is documented; no bulk export outside reports. Nothing public about a full-database dump or offboarding export; backups are vendor-side only.

**ÁSZF (hatályos 2026-01-01) — strong contractual exit lever.** eOptika is adatkezelő, ClearVis is adatfeldolgozó (§9.1.2). **§9.4.6 mirrors GDPR Art. 28(3)(g):** "Szolgáltató az Előfizetői szerződés megszűnése esetén az Előfizető döntése alapján minden személyes adatot töröl vagy **visszajuttat az Előfizetőnek**…" — a contractual right to get all personal data back on termination; **format/medium unspecified** (the negotiation point). §9.4.4–9.4.5: processor must assist with data-subject rights and incidents; §9.4.7: information/audit rights incl. on-site. §9.3.5 (new in 2026): vendor may process subscriber data for anonymized statistics/analytics (objection right exists). Termination mechanics: ordinary termination binds to the billing period (§6.3); prepaid fees non-refundable (§6.6.1, §7.6.3); auto-termination after 6 months non-use (§6.2) — **pull exports while the subscription is live**. The privacy notice's adathordozhatóság clause is the *member's* Art. 20 right, not eOptika's lever (eOptika's lever is §9.4.6 + Art. 28). Invoicing: "a clearvis.io rendszer nem minősül számlázó programnak" — invoices are created in Számlázz.hu/Billingo, so the authoritative invoice archive already lives outside ClearVisio.

**Community/user reports on data extraction: none found** (genuine negative — no public prior art on a ClearVisio exit migration).

### SOURCES

- https://github.com/clearvis-io/clearvisio-appointment-booker (README, api.php proxy) · https://raw.githubusercontent.com/clearvis-io/clearvisio-appointment-booker/main/helper/api.js · https://github.com/clearvis-io/clearvisio-appointment-booker-wordpress (env vars incl. apiV2 URL) · https://github.com/orgs/clearvis-io/repositories
- https://docs.clearvis.io/ · https://docs.clearvis.io/en/integrations/datagate/ · report pages: https://docs.clearvis.io/en/manual/backoffice/reports/ (+ customers%20report/, sales_report/, orders_and_payments/, eye%20examinations%20report/, stock_report/) · https://docs.clearvis.io/en/manual/backoffice/products/importing_from_excel
- https://clearvis.io/en/functions/ · https://clearvis.io/en/prices/
- ÁSZF 2026-01-01: https://clearvis.io/wp-content/uploads/2025/12/ClearvisioAszf20260101.pdf · ÁSZF 2023-04-06 (same key clauses): https://clearvis.io/wp-content/uploads/2023/03/ClearvisioAszf20230406.pdf · Adatkezelési tájékoztató: https://clearvis.io/wp-content/uploads/2021/07/adatkezelesi-tajekoztato-1.pdf

### DRAFT ANSWER — migration-scoping implications

1. **Highest-value next step needs no vendor contact:** open the API documentation inside eOptika's own clearvis.io UI and see whether apiV2 exposes read endpoints for customers/orders/exams/stock.
2. Without any vendor help, the Reports-module XLSX exports (Customers, Orders & Payments, Detailed Sales, Stock, Exam metadata) likely support a workable first-pass migration via XLSX → BigQuery staging; unknowns are stable internal IDs and full Rx content.
3. The contractual lever is strong: cite ÁSZF §9.4.6 + GDPR Art. 28 and request a machine-readable full dump (per-entity CSV/JSON/SQL incl. internal IDs, Rx/exam payloads, documents, consent records, appointment history), ideally as a **pre-termination dry run**.
4. Timing: schedule cutover just before a renewal date (prepaid fees non-refundable; export must happen while live).
5. Szempont constraints: Rx/health data flows to IRIS, not the szempont dataset (hard rule 5); identity mapping through IRIS (rule 4); ClearVis behind an adapter (rule 2). Invoice history is out of scope (already in Számlázz.hu/Billingo). Carry consent flags across — the Customers Report can include non-consented customers.

Vendor questions (support@clearvis.io / info@clearvis.io): apiV2 scope beyond booking (rate limits, pagination, key scopes); §9.4.6 return format/timeframe; pre-termination full-export dry run; whether report XLSX exports carry stable internal record IDs.

### OPEN / NEEDS HUMAN CONFIRMATION

- apiV2 scope beyond booking — check in-app API docs first, then vendor.
- Format/medium/SLA of the §9.4.6 data return — not specified; vendor question.
- Whether full Rx/exam content is exportable (reports show metadata only).
- Whether report exports carry internal record IDs — verify empirically in eOptika's account.
- Whether a per-client GDPR export exists in-app (not publicly documented).
- Tier naming mismatch (docs "Gold" vs price page "Fókusz") — confirm eOptika's tier includes Reports/exports.

---

*End of annex. Research performed 2026-07-17 by parallel web-research agents; all claims trace to the URLs above. Items marked OPEN / NEEDS HUMAN CONFIRMATION require the founder, the accountant, or vendor contact.*
