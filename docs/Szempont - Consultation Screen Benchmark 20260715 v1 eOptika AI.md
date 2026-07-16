# Szempont - Consultation Screen Benchmark 20260715 v1 eOptika AI

What the industry does for the optician↔customer shared screen, what is legally and practically copyable, and what to build. ClearVis has nothing here — this is greenfield differentiation.

## 1. Benchmark inventory

| Vendor / tool | What it does | The idea worth taking |
|---|---|---|
| **Zeiss VISUCONSULT 500** (iPad + store server) | Step-by-step support "from when the patient enters until they leave": patient mgmt → exam → **Vision Needs Analysis lifestyle questionnaire** → centration → frame consultation with **side-by-side patient photos in different frames** → AR lens demonstration → order via VISUSTORE | The *whole-journey guided flow* as the product; frame photo compare "especially beneficial for high prescriptions" (they can't see themselves without correction!) |
| **Essilor Companion (+ Companion VR)** | Digital dispensing aid: lifestyle questionnaire (age, activities, screen time) → best-in-class **lens combination recommendation** → VR immersion simulating the future lenses | Questionnaire→recommendation mapping; "involve the patient in the choice" framing |
| **Kodak IDS** (Signet Armorlite, iPad kiosk/tablet) | Three sections: frames (take photos), lenses (**compare designs, coatings, tech + simulated situations**), measuring | The 3-section simplicity; situation simulations (night driving, screen glare) |
| **Zeiss Lens Consultation Toolbox** | Packaged demonstration assets for coatings/designs | Demo assets matter as much as software |
| **Glasson** (POS-level) | Collaborative comparison *at the dispensing table*: "here's this lens in 1.60 vs 1.67 — see how the thickness changes"; their data: practices with fast tools get the time for the upsell conversations | Thickness compare as the trust-builder; speed buys selling time |
| **GrandVision legacy 3-option model** (Sabie's brief) | Present exactly three packages; customers anchor middle-or-above | Tier construction discipline: Alap / Ajánlott / Prémium, recommended pre-marked |
| **GlassesUSA-style auto-packages** (e-comm) | Rx entered → system auto-recommends the lens package | The recommendation should be computed, not composed ad hoc by the optician |
| **Public thickness calculators** (LensFit, Visionet etc.) | Geometry-based sag estimates; the honest insight: *a 4 mm smaller frame can out-thin a 1.60→1.74 index jump* | Honesty as positioning — show frame-size effects, not just index upsell |
| **Hardware measuring** (Zeiss i.Terminal, Essilor m'eyeFIT, Hoya visuReal) | Digital centration capture, feeds fitting data | Integration point, not build target (ClearVis fitting dict already carries Hoya fields) |

## 2. Copyability check

**Freely copyable (ideas/mechanics — not protected):** guided step flow · lifestyle questionnaire → recommendation logic · 3-tier presentation · side-by-side lens compare · thickness geometry visualization (public-domain optics: sag = D·r²/(2000·(n−1))) · tint/photochromic swatch demos built from OUR product data · frame photo compare using our own camera + UI · situation simulations if we produce our own imagery.

**NOT copyable:** Zeiss/Essilor/Kodak code, imagery, AR/VR assets, questionnaire texts verbatim, trademarks, their simulation photography. Also impractical: their AR/VR pipelines (years of asset work).

**Third path — embed, don't rebuild:** manufacturer demo tools can run alongside (Hoya/Zeiss reps provide them free with supply relationships); Szempont just needs to not fight for the same screen. Keep the tablet browser one tap from Szempont konzultáció ↔ vendor demo app.

## 3. What was built today (prototype, in the v8 package)

`/konzultacio` route — customer-facing mode on the Atlas shell:
- **Three tiers** auto-constructed from the pair finder: Alap = cheapest viable pair, Ajánlott = best-margin (pre-marked "ajánljuk"), Prémium = highest-spec. Computed, not composed — the GrandVision discipline with GlassesUSA mechanics.
- **Thickness comparison**: horizontal bars per index (1.50→1.74) for the customer's own worst meridian and the actual frame's lens diameter; `pricing/thickness.py` (tested, 4 tests) with the honest footnote — "kisebb keret gyakran többet vékonyít, mint egy indexugrás" — straight from the calculator research. Weight factor shown alongside.
- Larger type, calmer density than the operator screens; disclaimer "becsült érték" throughout.

## 4. Recommendation — module M2C "Konzultáció", phased

**W2 (cheap, data already exists):** productionize today's prototype — tiers from real EyeTech+supplier catalog, thickness bars, running basket panel (frame + lens + options + total, always visible — the "see everything chosen" requirement), tint swatches rendered from the Szín catalog, photochromic explained with our own before/after imagery.

**W3–P1:** lifestyle questionnaire (5–7 questions: screen hours, driving, outdoor, presbyopia onset) mapping to tier construction inputs; step-flow rail (Igény → Keret → Lencse → Extrák → Összegzés) so the screen *paces* the conversation; frame photo compare via tablet camera (high-Rx customers can't see themselves in demo frames — the Zeiss insight, trivially ours with getUserMedia).

**Defer / embed:** AR try-on, VR immersion, situation simulations — vendor apps do this better; one-tap switch instead.

**Hardware note:** needs a customer-facing display at the dispensing table (swivel tablet or second monitor) — a Teréz50 furniture decision, not software.

## 5. Decision menu

1. **M2C scope** — (a) W2-light as in §4 (tiers + thickness + basket + swatches) — **recommended** (b) full guided flow incl. questionnaire in W2 (c) defer entirely to P1.
2. **Tier construction rule** — (a) Alap=cheapest viable / Ajánlott=margin-best / Prémium=top spec, per-Rx computed — **recommended** (b) fixed curated packages per Rx band (GlassesUSA style; less flexible, more predictable).
3. **Customer display hardware** — (a) swivel tablet at the table (VISUCONSULT pattern) — **recommended** (b) fixed second monitor (c) both, decide after a week of floor trial.
4. **Vendor demo coexistence** — (a) keep Hoya/Zeiss demo apps installed, Szempont links out — **recommended** (b) Szempont-only screen.
