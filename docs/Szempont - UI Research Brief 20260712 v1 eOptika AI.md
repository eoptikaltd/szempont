# Szempont - UI Research Brief 20260712 v1 eOptika AI

Competitor/reference research for the Szempont floor UI, what was applied today, and what to mine from ClearVis screenshots.

## 1. Sources reviewed

**Glasson** (Polish, closest architectural comparator — full lens DB in the product, 3.5M variants, 16 manufacturers): documented Lens Finder flow: entry form deliberately shaped like the paper prescription; results in <0.2s; two-stage refine (physical params: diameter/thickness ranges → material/coating); stock visibility inside the results ("never recommend then discover it's out of stock"); client history pre-loaded before the search; one click from result to sale. Their published pain-point data: 74% of opticians find catalog searching slow, 45% say they lose money by being unable to compare lens prices.

**ClearVisio** (the incumbent — public material): the vevő adatlap (customer card) is the central object everything hangs off; main menu domains include Készletvezetés (with Új leltár flow) and Kimutatások; the core loop is vizsgálat → ajánlat → megrendelés → automatic notification after deposit; barcode-first stocktake philosophy. Heritage: built for Ofotért/Vision Express/GrandOptical — chain-grade task flows.

**US/global optical POS** (Jelo, OfficeMate/Eyefinity, EDGEPro, iVend, ConnectPOS): common patterns — one-screen ring-up of frame+lens+coatings+add-ons; "smart lens pricing" auto-computed from Rx+material+treatments (the pricing engine as UI, exactly our M2); frame matrix views for inventory; lab-order submission from the POS screen with status-to-notification loop (our M7+M9); repeated warning that missed lens add-ons at quote time are the main margin leak.

## 2. Pattern inventory → Szempont mapping

| Pattern (source) | Status in Szempont |
|---|---|
| Prescription-pad-shaped entry, OD/OS rows (Glasson, everyone) | **APPLIED TODAY** — finder rebuilt pair-first; a pair = R-SKU + L-SKU of the same family (`pricing/pair.py`), margin-sorted |
| Sub-second search over full catalog (Glasson 0.2s) | Holds — snapshot in memory; BQ load once per instance |
| Stock visibility in results (Glasson) | W3/M10 — needs Tharanis stock read; column reserved |
| Client context loaded before search (Glasson, ClearVis vevő adatlap) | W2/M3 — IRIS lookup; flow: customer card → "Új ajánlat" carries person_id into finder |
| Side-by-side 2–3 lens compare (spec M2, industry) | W2 — pair results table covers ranking; dedicated compare screen still owed |
| Add-on prompts at quote (margin-leak defense, US POS) | W2 — surcharge checkboxes exist; promote to explicit "ajánlott extrák" prompts once PL options are priced |
| One-screen order: frame + lenses + options (US POS, ClearVis) | W3/M4 |
| Status→notification loop from POS (Jelo, ClearVis) | M7+M9, per spec |

## 3. ClearVis screenshot upload — yes, and here is exactly what to send

Purpose is **task-flow and terminology parity, not visual imitation** — visuals are Atlas (locked); what eases staff transition is that the same task lives in the same conceptual place with the same Hungarian words. ClearVis's visual design is their IP; menu logic, field ordering, and vocabulary as *facts of staff habit* are fair game to mirror.

Send, in priority order (plain screenshots, phone photos fine; anonymize any real customer data):
1. **Vevő adatlap** (customer card) — the anchor object; field layout + which actions branch from it.
2. **Ajánlat/quote screen** — lens selection + pricing entry, exactly as staff use it daily.
3. **Megrendelés/order entry** — incl. fitting measurements (PD, heights) field order.
4. **Munkalap** — the printed sheet Műhely reads today; M4's PDF should be near-identical so the lab needs zero retraining.
5. **Main menu / navigation tree** — full expanded menu, for the IA mapping table.
6. **Order list / status view** — what "where is it" looks like today.
7. **Napi zárás / Kimutatások** screens if used at Teréz50.
8. (M11 prep, later) any export/admin screens.

Deliverable on receipt: a ClearVis→Szempont IA map (old menu item → new location), a field-parity checklist for Rx entry + munkalap, and a one-page "mi hol van" staff cheat sheet — the spec's standing mitigation (§7) made concrete.

## 4. Applied today (v5 package)

`pricing/pair.py` (find_pair_options: family grouping, both-eyes requirement, R+L pricing, margin sort) · finder rebuilt as prescription pad (OD/OS × sph/cyl/add, minus-cylinder hint on empty results) · quote page renders pair build-up (OD/OS labeled lines) with single-SKU backcompat · 25/25 tests incl. 3 new pair tests (both-eyes-required, sum-of-two-SKUs pricing, identical-Rx same-SKU-twice).
