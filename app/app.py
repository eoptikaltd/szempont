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
from app.barcodes import code128_svg, ean13_svg                  # noqa: E402
from app.catalog import load_snapshot, tint_swatches             # noqa: E402
from app.discounts import get_discount_config, load_discount_configs  # noqa: E402
from quotes.records import (QuoteError, ServiceLine,             # noqa: E402
                            apply_discount, build_quote_record, invoice_lines,
                            totals)
from quotes.store import discount_audit_event                    # noqa: E402
from vendors.unas_frames import DemoFrameSource, UnasFrameSource  # noqa: E402
from iris import (FixturePersonDirectory, InMemoryWalkinStore,   # noqa: E402
                  attributed_person_id, is_z1, new_walkin)

app = Flask(__name__)
APP_NAME = "Szempont"
TOOL_ID = "szempont"
HERE = os.path.dirname(__file__)

def current_operator() -> str:
    """Single source of the acting operator (review ruling 2026-07-16):
    every actor field — audit events, quote created_by, walk-in created_by —
    reads from here and nowhere else. Pre-M5 shim: fixed store operator from
    env; M5 replaces the body with the authenticated session user."""
    return os.environ.get("SZEMPONT_OPERATOR", "sabie.valner")


def operator_display(op: str) -> str:
    """'sabie.valner' -> 'Sabie Valner' for chips and hints."""
    return " ".join(p.capitalize() for p in op.replace(".", " ").split())


# D2: munkadíj auto-added to every basket, optician-editable/removable.
# Amount is the demo config; the curated service price list lands with M2C.
MUNKADIJ = ServiceLine("Szemüvegkészítés munkadíj", Decimal("4500"))

if os.environ.get("SZEMPONT_FRAMES") == "unas":  # pragma: no cover
    FRAMES = UnasFrameSource(api_key=os.environ["UNAS_API_KEY"])
else:
    FRAMES = DemoFrameSource()

# M3: IRIS person directory + Z1 walk-in store (contracts/iris_contract.md).
# Fixture-backed until IRIS publishes the two views; flipping to BQ is a
# config change (SZEMPONT_IRIS=bq), never a code change.
if os.environ.get("SZEMPONT_IRIS") == "bq":  # pragma: no cover
    from google.cloud import bigquery
    from iris.directory import BQPersonDirectory, DEFAULT_LOOKUP_VIEW, \
        DEFAULT_SEARCH_VIEW
    from iris.walkins import BQWalkinStore
    _bq = bigquery.Client(project=os.environ.get(
        "GCP_PROJECT", "natural-caster-496309-j3"))
    DIRECTORY = BQPersonDirectory(
        _bq,
        search_view=os.environ.get("IRIS_SEARCH_VIEW", DEFAULT_SEARCH_VIEW),
        lookup_view=os.environ.get("IRIS_LOOKUP_VIEW", DEFAULT_LOOKUP_VIEW))
    WALKINS = BQWalkinStore(_bq)
else:
    DIRECTORY = FixturePersonDirectory()
    WALKINS = InMemoryWalkinStore()

# Pre-M5 audit shim: events collected in-process; staging loads them to
# szempont.audit_log (same row shape) through the BQ store path.
AUDIT_EVENTS: list[dict] = []


def _emit_audit(event: dict) -> None:
    AUDIT_EVENTS.append(event)

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

    op = operator_display(current_operator())
    return dict(t=t, app_name=APP_NAME, lang=lang, languages=LANGUAGES,
                density=_cookie("density", DENSITIES, "comfortable"),
                nav=NAV, nav_active=TOOL_ID, huf=huf,
                operator_name=op,
                operator_initials="".join(w[0] for w in op.split()[:2]).upper())


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


def _person_view(person_param: str) -> dict | None:
    """Chip data for a person_id or Z1 token: resolves Z1 through the
    walkin_resolutions mapping at read time (rows never rewritten)."""
    pid = (person_param or "").strip()
    if not pid:
        return None
    if is_z1(pid):
        resolved = attributed_person_id(pid, WALKINS)
        card = DIRECTORY.lookup(resolved) if resolved != pid else None
        walkin = WALKINS.get(pid)
        return {
            "id": pid, "walkin": True,
            "resolved": resolved if resolved != pid else None,
            "name": card.display_name if card
                    else (walkin.display_name if walkin else pid),
            "ep_hint": card.ep_member_hint if card
                       else bool(walkin and walkin.ep_member),
        }
    card = DIRECTORY.lookup(pid)
    return {
        "id": pid, "walkin": False, "resolved": None,
        "name": card.display_name if card else pid,
        "ep_hint": card.ep_member_hint if card else False,
    }


@app.route("/ugyfel")
def ugyfel():
    """M3 customer search — v_person_search semantics via the directory
    adapter (A-grade zone only), with the Z1 walk-in fallback form."""
    q = request.args.get("q", "").strip()
    results = DIRECTORY.search(q) if q else []
    return render_template("ugyfel.html", page_title="Ügyfél", q=q,
                           results=results, searched=bool(q))


@app.route("/ugyfel/walkin", methods=["POST"])
def ugyfel_walkin():
    """Z1 walk-in capture: mints a Z1-<uuid> token (NOT a person id —
    hard rule 4), saves to szempont.walkin_persons, and continues straight
    to the finder so the walk-in never blocks a sale."""
    f = request.form
    try:
        w = new_walkin(
            display_name=f.get("name", ""), created_by=current_operator(),
            phone_raw=f.get("phone", "").strip(),
            email_raw=f.get("email", "").strip(),
            birth_date=f.get("birth_date", "").strip(),
            ep_member=bool(f.get("ep_member")),
            ep_fund_name=f.get("ep_fund_name", "").strip(),
            ep_member_id=f.get("ep_member_id", "").strip(),
            gdpr_signed=bool(f.get("gdpr_signed")),
            dm_ok=bool(f.get("dm_ok")))
    except ValueError as e:
        return render_template("ugyfel.html", page_title="Ügyfél", q="",
                               results=[], searched=False,
                               walkin_error=str(e)), 400
    WALKINS.save(w)
    return redirect(url_for("finder", person=w.z1_token))


@app.route("/")
def finder():
    """Prescription-pad-first lens finder (research: Glasson/ClearVis pattern).
    OD/OS rows -> lens families where BOTH eyes' exact-power SKUs exist,
    priced as R-SKU + L-SKU, margin-sorted."""
    snap = load_snapshot()
    today = dt.date.today().isoformat()
    person = request.args.get("person", "").strip()

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
        "needs_config": p.needs_configuration,   # D5 from-price flag
        "gross": huf(p.pair_retail_gross),
        # quote link carries the representative picks so the quote page opens
        # priced exactly as listed (the optician can re-chip from the finder)
        "quote_url": url_for("quote", sku_r=p.right.sku, sku_l=p.left.sku,
                             opt=sorted(options | p.representative_codes),
                             person=person or None),
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
        person=person, person_view=_person_view(person),
    )


def _preview_record(sku_r: str, sku_l: str, options: frozenset[str],
                    frame_sku: str, person: str, today: str):
    """Shared quote assembly for the GET view and the POST apply path.
    Raises PricingError for unknown SKUs / bad option combos."""
    snap = load_snapshot()
    qr = price_quote(snap, QuoteRequest(sku=sku_r, option_codes=options,
                                        quote_date=today, quantity=1))
    ql = price_quote(snap, QuoteRequest(sku=sku_l, option_codes=options,
                                        quote_date=today, quantity=1))
    frame = FRAMES.get(frame_sku) if frame_sku else None
    record = build_quote_record(
        quote_id="preview", quote_date=today, created_by=current_operator(),
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        engine_quotes=[("OD", qr), ("OS", ql)],
        frame=(frame.sku, frame.name, frame.retail_net) if frame else None,
        auto_services=[MUNKADIJ],
        # Z1 tokens are stored as-is; re-attribution happens through the
        # walkin_resolutions join at read time, never by rewriting rows.
        person_id=person or None,
    )
    return snap, qr, ql, frame, record


@app.route("/quote/discount", methods=["POST"])
def quote_discount():
    """D3 apply path (review ruling 2026-07-16): the POST applies the curated
    discount and — for approval-gated configs — emits exactly ONE audit event
    with the auto_approved_pre_m5 marker, then redirects (PRG) to the GET
    view. Page renders never write audit."""
    f = request.form
    sku_r = f.get("sku_r", "")
    sku_l = f.get("sku_l") or sku_r
    options = frozenset(f.getlist("opt"))
    frame_sku = f.get("frame", "")
    person = f.get("person", "").strip()
    discount_id = f.get("discount", "")
    today = dt.date.today().isoformat()

    cfg = get_discount_config(discount_id) if discount_id else None
    if cfg is not None and cfg.requires_approval:
        try:
            *_, record = _preview_record(sku_r, sku_l, options, frame_sku,
                                         person, today)
            record = apply_discount(record, cfg,
                                    approved_by=current_operator())
            import uuid
            _emit_audit(discount_audit_event(
                record, uuid.uuid4().hex,
                dt.datetime.now(dt.timezone.utc).isoformat(),
                marker="auto_approved_pre_m5"))
        except (PricingError, QuoteError):
            pass  # the GET view renders the error; nothing was approved
    return redirect(url_for("quote", sku_r=sku_r, sku_l=sku_l,
                            opt=sorted(options), frame=frame_sku or None,
                            person=person or None,
                            discount=discount_id or None))


@app.route("/quote")
def quote():
    """Pair quote assembled through the persistence record (W2 item 2):
    lens pair + optional Unas frame + auto munkadíj + curated discount.
    Stateless preview — pure render, NO audit writes on GET (discounts are
    applied and audited on the POST path above)."""
    options = frozenset(request.args.getlist("opt"))
    today = dt.date.today().isoformat()
    sku_r = request.args.get("sku_r") or request.args.get("sku", "")
    sku_l = request.args.get("sku_l") or sku_r
    frame_sku = request.args.get("frame", "")
    person = request.args.get("person", "").strip()
    try:
        snap, qr, ql, frame, record = _preview_record(
            sku_r, sku_l, options, frame_sku, person, today)
    except PricingError as e:
        return render_template("quote.html", page_title="Quote", error=str(e),
                               q=None, r=None, l=None, lines=[]), 404

    lens_r, lens_l = snap.lenses[sku_r], snap.lenses[sku_l]

    discount_id = request.args.get("discount", "")
    discount_error = None
    applied_config = None
    if discount_id:
        cfg = get_discount_config(discount_id)
        if cfg is None:
            discount_error = f"ismeretlen kedvezmény: {discount_id}"
        else:
            try:
                record = apply_discount(
                    record, cfg,
                    approved_by=(current_operator()
                                 if cfg.requires_approval else None))
                applied_config = cfg
            except QuoteError as e:
                discount_error = str(e)

    t_ = totals(record)
    base_params = {"sku_r": sku_r, "sku_l": sku_l, "opt": sorted(options),
                   "frame": frame_sku or None, "discount": discount_id or None,
                   "person": person or None}

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
        approved_by_display=(operator_display(record.discount_approved_by)
                             if record.discount_approved_by else None),
        base_params=base_params, person_view=_person_view(person),
    )



@app.route("/konzultacio")
def konzultacio():
    """M2C Konzultáció — customer-facing shared screen, W2-light scope
    (benchmark §4): three tiers from the live catalog path, honest thickness
    bars, ALWAYS-VISIBLE basket panel, tint swatches from the Szín catalog
    when the active snapshot carries tints. No questionnaire, no camera."""
    from pricing.thickness import compare_indices

    snap = load_snapshot()
    today = dt.date.today().isoformat()
    od = EyeRx(sph=_dec("od_sph", "-4.00"), cyl=_dec("od_cyl", "0"))
    os_rx = EyeRx(sph=_dec("os_sph", "-3.75"), cyl=_dec("os_cyl", "0"))
    frame_ed = _dec("frame_ed", "50")
    tint = request.args.get("tint", "").strip()
    frame_sku = request.args.get("frame", "").strip()
    person = request.args.get("person", "").strip()

    swatches = tint_swatches(snap)          # {} on tint-less live catalogs
    tint_code = next(iter(swatches), None)
    options = (frozenset({tint_code})
               if tint and tint_code else frozenset())

    base = {"od_sph": request.args.get("od_sph"),
            "od_cyl": request.args.get("od_cyl"),
            "os_sph": request.args.get("os_sph"),
            "os_cyl": request.args.get("os_cyl"),
            "frame_ed": request.args.get("frame_ed"),
            "tier": request.args.get("tier"), "tint": tint or None,
            "frame": frame_sku or None, "person": person or None}

    def kurl(**over):
        merged = {**base, **over}
        return url_for("konzultacio",
                       **{k: v for k, v in merged.items() if v})

    pairs = find_pair_options(snap, od, os_rx, quote_date=today,
                              option_codes=options)
    # Ruling 10: dormant SKUs stay sellable (finder, muted pill) but are not
    # proposed on the customer-facing consultation tiers.
    pairs = [p for p in pairs if not (p.right_dormant or p.left_dormant)]
    # price-anchored tiers (no margin data in Szempont): cheapest / middle / top;
    # rank_score can override the middle pick when published.
    by_price = sorted(pairs, key=lambda p: p.pair_retail_gross)
    tiers, picks = [], {}
    if by_price:
        mid = max(pairs, key=lambda p: p.rank_score) if any(
            p.rank_score for p in pairs) else by_price[len(by_price) // 2]
        picks = {"Alap": by_price[0],
                 "Ajánlott": mid,
                 "Prémium": by_price[-1]}
        selected_label = request.args.get("tier") or "Ajánlott"
        if selected_label not in picks:
            selected_label = "Ajánlott"
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
                "selected": label == selected_label,
                "select_url": kurl(tier=label),
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

    # Always-visible basket: the selected tier priced through the SAME record
    # path as the quote page (frame + lens pair + options + munkadíj).
    basket = None
    if picks:
        chosen = picks.get(request.args.get("tier") or "Ajánlott",
                           picks["Ajánlott"])
        try:
            *_, record = _preview_record(chosen.right.sku, chosen.left.sku,
                                         options, frame_sku, person, today)
            t_ = totals(record)
            one = 1 + record.vat_rate
            basket = {
                "lines": [{"name": l.name,
                           "gross": huf((l.net * one).quantize(Decimal("1")))}
                          for l in invoice_lines(record)],
                "total": huf(t_.total_retail_gross),
                "tint": tint or None,
                "quote_url": url_for(
                    "quote", sku_r=chosen.right.sku, sku_l=chosen.left.sku,
                    opt=sorted(options), frame=frame_sku or None,
                    person=person or None),
            }
        except PricingError:
            basket = None

    frame = FRAMES.get(frame_sku) if frame_sku else None
    frame_query = request.args.get("qf", "").strip()
    frame_hits = [{"sku": h.sku, "name": h.name, "net": huf(h.retail_net),
                   "add_url": kurl(frame=h.sku, qf=None)}
                  for h in (FRAMES.search(frame_query) if frame_query else [])]

    swatch_rows = []
    for code, colors in swatches.items():
        sc = snap.surcharges[code]
        swatch_rows.append({
            "name": sc.name,
            "gross": huf((sc.retail_net * (1 + snap.vat_rate))
                         .quantize(Decimal("1"))),
            "colors": [{"name": n, "hex": h,
                        "url": kurl(tint=None if tint == n else n),
                        "active": tint == n} for n, h in colors],
        })

    return render_template("konzultacio.html", page_title="Konzultáció",
                           tiers=tiers, thick=thick, f=request.args,
                           frame_ed=frame_ed, basket=basket, frame=frame,
                           frame_query=frame_query, frame_hits=frame_hits,
                           swatch_rows=swatch_rows, kurl=kurl)


# ------------------------------------------------------- print routes (item 4b)
HU_WEEKDAYS = ("hétfő", "kedd", "szerda", "csütörtök", "péntek",
               "szombat", "vasárnap")
HU_MONTHS = ("január", "február", "március", "április", "május", "június",
             "július", "augusztus", "szeptember", "október", "november",
             "december")


def _hu_date(d: dt.date) -> str:
    return f"{d.year}. {d.month:02d}. {d.day:02d}."


def _fmt_power(raw: str) -> str:
    """'+0.75' / '-0,25' -> '+0,75' / '−0,25' (print sheet convention:
    always-signed, comma decimals, U+2212 minus)."""
    s = (raw or "").strip().replace(",", ".")
    if not s:
        return ""
    try:
        v = Decimal(s)
    except Exception:
        return raw
    return f"{v:+.2f}".replace(".", ",").replace("-", "−")


def _fmt_mm(raw: str) -> str:
    s = (raw or "").strip().replace(",", ".")
    if not s:
        return ""
    try:
        return f"{Decimal(s):.1f}".replace(".", ",")
    except Exception:
        return raw


def _person_print_fields(person: str) -> dict:
    """name/id/phone/birth/email for print sheets, resolving Z1 via the join."""
    pv = _person_view(person)
    if not pv:
        return {"name": "", "id": "", "phone": "", "birth": "", "email": ""}
    card = DIRECTORY.lookup(pv["resolved"] or pv["id"])
    walkin = WALKINS.get(pv["id"]) if pv["walkin"] else None
    return {
        "name": pv["name"], "id": pv["resolved"] or pv["id"],
        "phone": (card.phone_e164 if card
                  else (walkin.phone_raw if walkin else "")) or "",
        "birth": (card.birth_date if card
                  else (walkin.birth_date if walkin else "")) or "",
        "email": (card.email if card
                  else (walkin.email_raw if walkin else "")) or "",
    }


@app.route("/print/munkalap")
def print_munkalap():
    """Lab glazing sheet — design-frozen template, data wired in (item 4b).
    Real Code-128 (order, lens SKUs) and EAN-13 (frame GTIN) inline SVGs
    replace the CSS placeholder stripes. Centration fields left blank when
    not passed — the sheet stays pencil-friendly by design."""
    snap = load_snapshot()
    a = request.args.get
    sku_r = a("sku_r") or a("sku", "")
    sku_l = a("sku_l") or sku_r
    lens_r, lens_l = snap.lenses.get(sku_r), snap.lenses.get(sku_l)
    if lens_r is None or lens_l is None:
        return f"ismeretlen SKU: {sku_r if lens_r is None else sku_l}", 404

    today = dt.date.today()
    order_no = a("order", "").strip()
    job_id = a("job", "").strip() or f"ML-{today:%y%m%d}-0001"
    try:
        due = dt.date.fromisoformat(a("due", ""))
    except ValueError:
        due = today + dt.timedelta(days=3)
    frame = FRAMES.get(a("frame", "")) if a("frame") else None
    p = _person_print_fields(a("person", "").strip())

    def lens_row(eye, lens, pre):
        return {
            "eye": eye, "name": lens.name, "sku": lens.sku,
            "barcode": code128_svg(lens.sku, module_width=0.12,
                                   module_height=3.5, font_size=5),
            "sph": _fmt_power(a(f"{pre}_sph", "")),
            "cyl": _fmt_power(a(f"{pre}_cyl", "")),
            "axis": (a(f"{pre}_ax", "") + "°") if a(f"{pre}_ax") else "",
            "pd": _fmt_mm(a(f"{pre}_pd", "")),
            "height": _fmt_mm(a(f"{pre}_h", "")),
        }

    ml = {
        "job_id": job_id,
        "order_no": order_no or "—",
        "order_barcode": code128_svg(order_no or job_id, module_width=0.18,
                                     module_height=4.5, write_text=False),
        "recorded_by": operator_display(current_operator()),
        "today_display": _hu_date(today),
        "due_display": f"{due.month:02d}. {due.day:02d}.",
        "due_weekday": HU_WEEKDAYS[due.weekday()],
        "prio": "SÜRGŐS" if a("prio") == "surgos" else "NORMÁL",
        "customer_name": p["name"] or "—",
        "customer_id": p["id"] or "—",
        "customer_phone": p["phone"] or "—",
        "frame_name": frame.name if frame else "Hozott keret / nincs megadva",
        "frame_code": frame.sku if frame else "—",
        "frame_barcode": (ean13_svg(frame.ean, module_height=3.5, font_size=5)
                          if frame and frame.ean else
                          (code128_svg(frame.sku, module_width=0.12,
                                       module_height=3.5, font_size=5)
                           if frame else "")),
        "od": lens_row("J", lens_r, "od"),
        "os": lens_row("B", lens_l, "os"),
        "work_code": a("work_code", "PF-00005"),
        "work_note": a("work_note", "(teli keretbe)"),
        "printed_at": (_hu_date(today)
                       + f" {dt.datetime.now():%H:%M}"),
    }
    return render_template("print/munkalap.html", ml=ml)


# Layout-check sample for the exam sheet (the frozen mockup's own data).
DEMO_EXAM = {
    "name": "Minta Anna", "address": "1066 Budapest, Példa utca 12.",
    "birth": "1985. 03. 14.", "phone": "+36 30 123 4567",
    "email": "minta.anna@example.com", "pid": "PA-1225063",
    "exam_date": "2026. 07. 15.", "control_date": "2026. 10. 15.",
    "validity_date": "2026. 10. 15.",
    "ar_j_sph": "−6.75", "ar_j_cyl": "+1.25", "ar_j_ax": "83",
    "ar_b_sph": "−6.25", "ar_b_cyl": "+1.25", "ar_b_ax": "96",
    "ker_j": "8.26", "ker_b": "8.17", "pd_j": "29.5", "pd_b": "29.5",
    "mono_j_sph": "−6.75", "mono_j_cyl": "+1.25", "mono_j_ax": "85",
    "mono_b_sph": "−6.75", "mono_b_cyl": "+1.25", "mono_b_ax": "95",
    "viz_j": "0.9", "viz_b": "0.9", "viz_bin": "1.0",
    "bino_j_sph": "−6.75", "bino_j_cyl": "+1.25", "bino_j_ax": "85",
    "bino_b_sph": "−6.75", "bino_b_cyl": "+1.25", "bino_b_ax": "95",
    "tavoli_j_sph": "−6.75", "tavoli_j_cyl": "+1.25", "tavoli_j_ax": "85",
    "tavoli_b_sph": "−6.75", "tavoli_b_cyl": "+1.25", "tavoli_b_ax": "95",
    "kl_j_sph": "−5.00", "kl_j_cyl": "−1.25", "kl_j_ax": "170",
    "kl_j_type": "JJ OATP", "kl_j_bc": "8.60",
    "kl_b_sph": "−5.00", "kl_b_cyl": "−1.25", "kl_b_ax": "10",
    "kl_b_type": "JJ OATP", "kl_b_bc": "8.60",
    "anam_dx": "Kl szeretne. Jelenlegi kl. nem cylinderes.",
    "anam_notes": "Mai eredmény:\nod: 2mou −5,50 −1,25cyl 175° V0,9\n"
                  "os: 2mou −5,50 −1,25cyl 5° V0,9\nVbin 0,9–1,0",
}


@app.route("/print/latasvizsgalat")
def print_latasvizsgalat():
    """Exam-result + suggested-correction sheet — design-frozen template.
    PURE PASS-THROUGH: values exist only in this request; Szempont stores no
    Rx/health data (hard rule 5 — IRIS owns it, M6 reads via contract).
    ?demo=1 renders the mockup's sample for layout verification. Person
    fields prefill from the directory/walk-in when ?person= is given."""
    d = {k: v for k, v in request.args.items() if k not in ("demo", "person")}
    if request.args.get("demo") == "1":
        d = {**DEMO_EXAM, **d}
    person = request.args.get("person", "").strip()
    if person:
        p = _person_print_fields(person)
        d.setdefault("name", p["name"])
        d.setdefault("pid", p["id"])
        d.setdefault("phone", p["phone"])
        d.setdefault("email", p["email"])
        d.setdefault("birth", p["birth"])
    today = dt.date.today()
    printed = f"{today.year}. {HU_MONTHS[today.month - 1]} {today.day}."
    return render_template("print/latasvizsgalat_eredmenye.html",
                           d=d, printed_display=printed)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
