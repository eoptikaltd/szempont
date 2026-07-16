# Szempont - Spec Reconciliation 20260712 v1 eOptika AI

Execution Spec v2 (received after W1 was built) reconciled against the v3 package.
Spec wins on module detail per the Handover Brief — except where Sabie's same-day
ruling supersedes it (one case, §2 below).

## 1. W1 assumptions (A1–A8) vs spec — verdicts

| # | Assumption as built | Spec verdict |
|---|---|---|
| A1 | Net catalog prices, 27% VAT at quote, whole-HUF final rounding | Consistent — M2: "base price + surcharges + combo overrides + VAT". House rounding rules mentioned but not defined → **confirm rounding rule** (currently ROUND_HALF_UP on gross). |
| A2 | Combo override replaces computed retail; cost never overridden | Consistent — M1: "negotiated combination prices not representable in SF6", pattern `ext_cogs_corrections`. |
| A3 | Most-recently-effective override wins | Not specified — stands as documented behaviour. |
| A4 | valid_from/valid_to inclusive | Consistent with "effective-dating". |
| A5 | Default quantity = pair | Not specified — stands. |
| A6 | Margin-sorted results | Confirmed verbatim — "margin-sorted 'best glass' default". |
| A7 | Content-addressed catalog_version | Spec wants valid-from/until versioning; effective_from present, "until" implied by successor version. Reproducibility requirement met (versions retained, engine snapshot-pure). |
| A8 | VAT rate per snapshot | Not contradicted; protects historical quotes. |

All eight stand. No pricing-engine changes required.

## 2. The one divergence: M1 mechanism

Spec §M1 (authored this morning): wrap the FS6 Converter as Cloud Run job
`szempont-catalog-ingest`, land supplier ZIPs into `szempont.lens_catalog_*`
(7 normalized SF6-shaped tables).

Sabie's ruling (this afternoon, supersedes): Szempont never parses FS6; it
consumes the sf6-converter's BigQuery output. Implemented as `CatalogSource` →
`szempont.lens_catalog` (flat, per-SKU) sync, live-verified against
`sf6_catalog_converter.pl_items_enriched` (1,111 EyeTech SKUs).

Spec intent preserved: "this module is integration, versioning and overrides,
not parser development" — the parse step just lives in the converter repo
rather than a Szempont-wrapped subprocess. Same versioning, same overrides,
same health report.

**Open schema question for M1x (not now):** branded supplier catalogs
(Zeiss/Hoya/Essilor/Noptiker, ~500K possible variants per OQ-1b) are
range-based, not per-SKU — the flat table won't hold them. When the converter's
import direction lands a supplier catalog in BQ, Szempont will need the
normalized range tables (head/types/geometries/prices/coatings/colors/
surcharges as in spec §6) plus a variant-resolution step at quote time. The
names are reserved; decision deferred to M1x kickoff with real converter-import
output in hand.

## 3. Spec items now added

- DDL for §6 tables: `quotes` (full price-component breakdown for audit,
  discount + approver fields for M5 permission gating), `orders` (Unas ID
  mirror, munkalap URI), `sku_promotions` (M4 first-sale registry),
  `invoices` (M8), `stock_movements` (M10, Tharanis master per OQ-4).
- Spec docx checked into `/docs`.

## 4. W2 remaining (M2 UI completion + M3), per spec

Already built ahead: parametric finder, quote detail view, Atlas shell.
Still owed for W2 acceptance:

1. Side-by-side compare of 2–3 candidate lenses (retail/cost/margin columns).
2. Quote = frame line via Unas product search (unas_data + enrichment,
   images from Unas CDN) + lens lines + options.
3. Discount entry with permission gating (role model lands fully in M5;
   gate stub in W2).
4. Quote save/retrieve to `szempont.quotes`; branded quote PDF; one-step
   convert-to-order handoff point (order write itself is W3/M4).
5. M3 customer layer: IRIS A-grade lookup component (name/phone/email/order),
   disambiguation cards, walk-in create via Z1, GDPR consent flag.
   **Blocked on Brief §8.2: IRIS canonical view names + Z1 contract doc.**

Acceptance bar (spec): 3-option comparison + branded quote PDF for a real Rx
in under 3 minutes; 20 test cases match manual calculation; M3 correct on 20
known customers incl. diacritic variants.

## 5. Verifications the spec parks (no action now)

ClearVis apiV2 export coverage (M11 kickoff) · Unas order-create limits for the
store channel (W3 sandbox order) · Tharanis SOAP stock-write coverage (M10 kickoff).
