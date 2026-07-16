"""Szempont — in-store POS, Atlas tool shell. W2 head start: M2 UI.

Pages:
  /        Lens finder — parametric search over the active CatalogSnapshot
           (Rx, design, index, coating tier, photochromic, options),
           candidates margin-sorted. Archetype: list_monitor.
  /quote   One configured quote in depth (lines, VAT, margin, override).
           Archetype: detail_view.

Data source: catalog.load_snapshot() — demo fixture now, BigQuery
szempont.lens_catalog_* once M1 has ingested a real supplier file.
All money/number formatting lives here (UI contract: formatting in Python).
"""
import datetime as dt
import os
import sys
import json
import glob
from decimal import Decimal

from flask import Flask, render_template, request, redirect, make_response, url_for

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pricing.engine import PricingError, price_quote            # noqa: E402
from pricing.models import LensDesign, CoatingTier, QuoteRequest, SearchQuery  # noqa: E402
from pricing.pair import EyeRx, find_pair_options                # noqa: E402
from pricing.search import search                                # noqa: E402
from app.catalog import load_snapshot                            # noqa: E402
from app.discounts import get_discount_config, load_discount_configs  # noqa: E402
from quotes.records import (QuoteError, ServiceLine,             # noqa: E402
                            apply_discount, build_quote_record, invoice_lines,
                            totals)
from vendors.unas_frames import DemoFrameSource, UnasFrameSource  # noqa: E402

app = Flask(__name__)
APP_NAME = "Szempont"
TOOL_ID = "szempont"
HERE = os.path.dirname(__file__)

# Auth is M5 (W3); until then the operator on the profile chip is the actor.
ACTOR = "sabie.valner"
# D2: munkadíj auto-added to every basket, optician-editable/removable.
# Amount is the demo config; the curated service price list lands with M2C.
MUNKADIJ = ServiceLine("Szemüvegkészítés munkadíj", Decimal("4500"))

if os.environ.get("SZEMPONT_FRAMES") == "unas":  # pragma: no cover
    FRAMES = UnasFrameSource(api_key=os.environ["UNAS_API_KEY"])
else:
    FRAMES = DemoFrameSource()

with open(os.path.join(HERE, "nav.json"), encoding="utf-8") as fh:
    NAV = json.load(fh)

LANGUAGES = [("hu", "Magyar"), ("en", "English")]
CATALOG_I18N = {}
for _f in glob.glob(os.path.join(HERE, "translations", "*.json")):
    with open(_f, encoding="utf-8") as fh:
        CATALOG_I18N[os.path.splitext(os.path.basename(_f))[0]] = json.load(fh)

DENSITIES = ("comfortable", "compact", "control")


def _cookie(name, allowed, default):
    v = request.cookies.get(name, default)
    return v if v in allowed else default


def huf(v: Decimal) -> str:
    """12 345 Ft — thousands with narrow spaces, no decimals."""
    return f"{int(v):,}".replace(",", "\u202f") + " Ft"


def pct(a: Decimal, b: Decimal) -> str:
    return f"{(a / b * 100):.1f}%" if b else "–"


@app.context_processor
def inject_globals():
    lang = _cookie("lang", dict(LANGUAGES), "hu")

    def t(key, **kw):
        s = (CATALOG_I18N.get(lang, {}).get(key)
             or CATALOG_I18N.get("en", {}).get(key, key))
        return s.format(**kw) if kw else s

    return dict(t=t, app_name=APP_NAME, lang=lang, languages=LANGUAGES,
                density=_cookie("density", DENSITIES, "comfortable"),
                nav=NAV, nav_active=TOOL_ID, huf=huf)


@app.route("/set-lang")
def set_lang():
    resp = make_response(redirect(request.args.get("next") or "/"))
    lang = request.args.get("lang", "hu")
    if lang in dict(LANGUAGES):
        resp.set_cookie("lang", lang, max_age=31536000, samesite="Lax")
    return resp


@app.route("/set-density")
def set_density():
    resp = make_response(redirect(request.args.get("next") or "/"))
    d = request.args.get("d", "comfortable")
    if d in DENSITIES:
        resp.set_cookie("density", d, max_age=31536000, samesite="Lax")
    return resp


def _dec(name, default="0"):
    raw = (request.args.get(name) or default).replace(",", ".").strip()
    try:
        return Decimal(raw)
    except Exception:
        return Decimal(default)


@app.route("/")
def finder():
    """Prescription-pad-first lens finder (research: Glasson/ClearVis pattern).
    OD/OS rows -> lens families where BOTH eyes' exact-power SKUs exist,
    priced as R-SKU + L-SKU, margin-sorted."""
    snap = load_snapshot()
    today = dt.date.today().isoformat()

    od = EyeRx(sph=_dec("od_sph", "-2.00"), cyl=_dec("od_cyl", "0"),
               add=_dec("od_add", "0"))
    os_rx = EyeRx(sph=_dec("os_sph", "-2.00"), cyl=_dec("os_cyl", "0"),
                  add=_dec("os_add", "0"))
    # opt = independent checkboxes; cg_* = one radio param per D5 choice group
    # (radios must not share a name across groups, so they merge here).
    options = frozenset(
        set(request.args.getlist("opt"))
        | {v for k, v in request.args.items()
           if k.startswith("cg_") and v})

    pairs = find_pair_options(snap, od, os_rx, quote_date=today,
                              option_codes=options)

    rows = [{
        "family": p.family_name,
        "supplier": p.supplier,
        "index": f"{p.index}",
        "dia": p.diameter_mm,
        "coating": p.right.coating_tier.value,
        "photo": p.right.photochromic,
        "sku_r": p.right.sku,
        "sku_l": p.left.sku,
        "dormant_r": p.right_dormant,       # ruling 10: muted pill
        "dormant_l": p.left_dormant,
        "gross": huf(p.pair_retail_gross),
        "quote_url": url_for("quote", sku_r=p.right.sku, sku_l=p.left.sku,
                             opt=sorted(options)),
    } for p in pairs]

    # D5: mandatory-choice surcharges render as one-of chip groups; the rest
    # stay independent checkboxes.
    plain_surcharges = sorted((s for s in snap.surcharges.values()
                               if not s.choice_group), key=lambda s: s.name)
    grouped: dict[str, list] = {}
    for s in sorted(snap.surcharges.values(), key=lambda s: s.name):
        if s.choice_group:
            grouped.setdefault(s.choice_group, []).append(s)
    choice_groups = [{
        "key": f"cg_{i}",
        "name": gname,
        "members": members,
        "selected": next((s.code for s in members if s.code in options), ""),
    } for i, (gname, members) in enumerate(sorted(grouped.items()))]

    kpis = {
        "candidates": len(rows),
        "suppliers": len({p.supplier for p in pairs}),
        "best_price": huf(min((p.pair_retail_gross for p in pairs), default=0)) if pairs else "–",
        "catalog_version": snap.catalog_version,
    }
    return render_template(
        "finder.html", page_title="Lens finder", rows=rows, kpis=kpis,
        f=request.args, surcharges=plain_surcharges,
        choice_groups=choice_groups, options=options,
    )


@app.route("/quote")
def quote():
    """Pair quote assembled through the persistence record (W2 item 2):
    lens pair + optional Unas frame + auto munkadíj + curated discount.
    Stateless preview — saving lands with the person attach (M3)."""
    snap = load_snapshot()
    options = frozenset(request.args.getlist("opt"))
    today = dt.date.today().isoformat()
    sku_r = request.args.get("sku_r") or request.args.get("sku", "")
    sku_l = request.args.get("sku_l") or sku_r
    try:
        qr = price_quote(snap, QuoteRequest(sku=sku_r, option_codes=options,
                                            quote_date=today, quantity=1))
        ql = price_quote(snap, QuoteRequest(sku=sku_l, option_codes=options,
                                            quote_date=today, quantity=1))
    except PricingError as e:
        return render_template("quote.html", page_title="Quote", error=str(e),
                               q=None, r=None, l=None, lines=[]), 404

    lens_r, lens_l = snap.lenses[sku_r], snap.lenses[sku_l]

    frame_sku = request.args.get("frame", "")
    frame = FRAMES.get(frame_sku) if frame_sku else None

    record = build_quote_record(
        quote_id="preview", quote_date=today, created_by=ACTOR,
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        engine_quotes=[("OD", qr), ("OS", ql)],
        frame=(frame.sku, frame.name, frame.retail_net) if frame else None,
        auto_services=[MUNKADIJ],
    )

    discount_id = request.args.get("discount", "")
    discount_error = None
    applied_config = None
    if discount_id:
        cfg = get_discount_config(discount_id)
        if cfg is None:
            discount_error = f"ismeretlen kedvezmény: {discount_id}"
        else:
            try:
                # Approval UI is M5 (permissions); the operator on the
                # profile chip approves for now, audited on save.
                record = apply_discount(
                    record, cfg,
                    approved_by=ACTOR if cfg.requires_approval else None)
                applied_config = cfg
            except QuoteError as e:
                discount_error = str(e)

    t_ = totals(record)
    base_params = {"sku_r": sku_r, "sku_l": sku_l, "opt": sorted(options),
                   "frame": frame_sku or None, "discount": discount_id or None}

    frame_query = request.args.get("qf", "").strip()
    frame_hits = [{
        "sku": f.sku, "name": f.name, "net": huf(f.retail_net),
        "add_url": url_for("quote", **{**base_params, "frame": f.sku}),
    } for f in (FRAMES.search(frame_query) if frame_query else [])]

    lines = [{
        "type": x.line_type, "name": x.name, "sku": x.sku or "",
        "qty": x.qty, "unit": huf(x.unit_retail_net), "net": huf(x.net),
        "auto": x.auto_added,
    } for x in invoice_lines(record)]

    view = {
        "basket_net": huf(t_.basket_net),
        "discount_net": huf(t_.discount_net),
        "total_net": huf(t_.total_retail_net),
        "vat": huf(t_.total_vat),
        "gross": huf(t_.total_retail_gross),
        "vat_rate": f"{record.vat_rate * 100:.0f}%",
        "override": qr.override_applied or ql.override_applied,
        "catalog_version": record.catalog_version,
        "date": record.quote_date,
        "remove_frame_url": url_for("quote", **{**base_params, "frame": None}),
        "clear_discount_url": url_for("quote",
                                      **{**base_params, "discount": None}),
    }
    return render_template(
        "quote.html", page_title="Quote", error=None,
        q=view, r=lens_r, l=lens_l, lines=lines,
        frame=frame, frame_query=frame_query, frame_hits=frame_hits,
        discount_configs=load_discount_configs(), discount_id=discount_id,
        applied_config=applied_config, discount_error=discount_error,
        base_params=base_params,
    )



@app.route("/konzultacio")
def konzultacio():
    """Consultation mode — customer-facing shared screen (M2C prototype).
    Three tiers built from the pair finder (research: GrandVision 3-option
    model, Essilor Companion / Zeiss VISUCONSULT guided flow), with an honest
    geometry-based thickness comparison (becsult ertek)."""
    from decimal import Decimal
    from pricing.thickness import compare_indices

    snap = load_snapshot()
    today = dt.date.today().isoformat()
    od = EyeRx(sph=_dec("od_sph", "-4.00"), cyl=_dec("od_cyl", "0"))
    os_rx = EyeRx(sph=_dec("os_sph", "-3.75"), cyl=_dec("os_cyl", "0"))
    frame_ed = _dec("frame_ed", "50")

    pairs = find_pair_options(snap, od, os_rx, quote_date=today)
    # Ruling 10: dormant SKUs stay sellable (finder, muted pill) but are not
    # proposed on the customer-facing consultation tiers.
    pairs = [p for p in pairs if not (p.right_dormant or p.left_dormant)]
    # price-anchored tiers (no margin data in Szempont): cheapest / middle / top;
    # rank_score can override the middle pick when published.
    by_price = sorted(pairs, key=lambda p: p.pair_retail_gross)
    tiers = []
    if by_price:
        mid = max(pairs, key=lambda p: p.rank_score) if any(
            p.rank_score for p in pairs) else by_price[len(by_price) // 2]
        picks = {"Alap": by_price[0],
                 "Ajánlott": mid,
                 "Prémium": by_price[-1]}
        seen = set()
        for label, p in picks.items():
            if p.family_key in seen and len(by_price) > len(seen):
                continue
            seen.add(p.family_key)
            tiers.append({
                "label": label,
                "family": p.family_name,
                "index": f"{p.index}",
                "supplier": p.supplier,
                "gross": huf(p.pair_retail_gross),
                "recommended": label == "Ajánlott",
            })

    worst_eye = min(od.sph + min(od.cyl, Decimal(0)),
                    os_rx.sph + min(os_rx.cyl, Decimal(0)))
    thick = [{
        "index": f"{t.index}",
        "edge": f"{t.edge_mm}",
        "bar_pct": 100,   # filled below relative to max
        "weight": f"{t.weight_factor}",
    } for t in compare_indices(worst_eye, Decimal("0"), frame_ed)]
    max_edge = max((Decimal(t["edge"]) for t in thick), default=Decimal(1))
    for t in thick:
        t["bar_pct"] = int(Decimal(t["edge"]) / max_edge * 100)

    return render_template("konzultacio.html", page_title="Konzultáció",
                           tiers=tiers, thick=thick, f=request.args,
                           frame_ed=frame_ed)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
