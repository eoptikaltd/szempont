"""Szempont — in-store POS, Atlas tool shell. W2 head start: M2 UI.

Pages:
  /              Kezdőlap — ClearVis-pattern landing: ügyfélkeresés quick card
                 + W3 placeholders (készlet-ellenőrzés, queue cards).
  /lencsekereso  Lens finder — parametric search over the active
                 CatalogSnapshot (Rx, design, index, coating tier,
                 photochromic, options). Archetype: list_monitor.
  /quote         One configured quote in depth (lines, VAT, margin, override).
                 Archetype: detail_view.
  /megrendelesek M4 order list — ClearVis quick-filter chips + időszak.
  /megrendeles/x M4 order detail — status machine, eseménynapló, Tharanis
                 dry-run (R1/F-W3-01: live write hard-blocked).

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

from flask import (Flask, render_template, request, redirect, make_response,
                   session, url_for)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pricing.engine import PricingError, price_quote            # noqa: E402
from pricing.models import LensDesign, CoatingTier, QuoteRequest, SearchQuery  # noqa: E402
from pricing.pair import EyeRx, find_pair_options                # noqa: E402
from pricing.search import search                                # noqa: E402
from app.barcodes import code128_svg, ean13_svg                  # noqa: E402
from app.catalog import load_snapshot, tint_swatches             # noqa: E402
from app.discounts import get_discount_config, load_discount_configs  # noqa: E402
from quotes.records import (QuoteError, QuoteStatus, ServiceLine,  # noqa: E402
                            apply_discount, build_quote_record,
                            gross_line_allocation, invoice_lines, totals)
from quotes.records import transition as quote_transition        # noqa: E402
from quotes.store import InMemoryQuoteStore, discount_audit_event  # noqa: E402
from orders.ids import next_order_id                             # noqa: E402
from orders.records import (STATUS_HU, OrderError, OrderStatus,  # noqa: E402
                            allowed_next, build_order_from_quote,
                            cancel_order, order_totals, transition_order)
from orders.store import InMemoryOrderStore                      # noqa: E402
from orders.promotions import (InMemoryPromotionRegistry,        # noqa: E402
                               register_first_sale)
# MVP override 2026-07-18: PIN + IAP-JWT enforcement are PARKED in auth/
# (package + tests stay); the UI uses the roster read-only — operator
# dropdown (MVP-2) and approver select on gated discounts.
from auth.staff import InMemoryStaffStore                        # noqa: E402
from auth.iap import IapError, iap_audience, verify_iap_jwt      # noqa: E402
from vendors.unas_frames import DemoFrameSource, UnasFrameSource  # noqa: E402
from iris import (FixturePersonDirectory, InMemoryWalkinStore,   # noqa: E402
                  attributed_person_id, is_z1, new_walkin)

app = Flask(__name__)
APP_NAME = "Szempont"
TOOL_ID = "szempont"
HERE = os.path.dirname(__file__)

# M5 session cookie signing. Dev: per-process random (session resets on
# restart — fine). Staging/prod MUST set SZEMPONT_SECRET_KEY (Secret
# Manager) or every deploy logs everyone out mid-day. Deploy checklist item.
import secrets as _secrets                                        # noqa: E402
app.secret_key = os.environ.get("SZEMPONT_SECRET_KEY") or _secrets.token_hex(32)


def current_operator() -> str:
    """Single source of the acting operator: the session operator picked at
    the terminal (M5, R6). Fallback while nobody picked (fresh terminal,
    non-browser client, tests, out-of-request callers): fixed store operator
    from env. Every actor field — audit events, created_by, approvals —
    reads from here."""
    from flask import has_request_context
    if has_request_context() and session.get("operator"):
        return session["operator"]
    return os.environ.get("SZEMPONT_OPERATOR", "valner.szabolcs")


def operator_display(op: str) -> str:
    """Display name from the staff roster (M5); derived fallback for ids
    outside the roster ('sabie.valner' -> 'Sabie Valner')."""
    name = STAFF.display_name(op)
    if name:
        return name
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

# M4 stores (W3-1): in-memory for dev/tests; SZEMPONT_STORES=bq flips all
# three to the BigQuery implementations (DDL 003) — config, never code.
if os.environ.get("SZEMPONT_STORES") == "bq":  # pragma: no cover
    from google.cloud import bigquery as _sbq
    from orders.promotions import BQPromotionRegistry
    from orders.store import BQOrderStore
    from quotes.store import BQQuoteStore
    _sclient = _sbq.Client(project=os.environ.get(
        "GCP_PROJECT", "natural-caster-496309-j3"))
    ORDERS = BQOrderStore(_sclient)
    QUOTE_STORE = BQQuoteStore(_sclient)
    PROMOTIONS = BQPromotionRegistry(_sclient)
else:
    ORDERS = InMemoryOrderStore()
    QUOTE_STORE = InMemoryQuoteStore()
    PROMOTIONS = InMemoryPromotionRegistry()

# M5 staff roster (R7 seed). BQ store loads szempont.staff (DDL 004).
if os.environ.get("SZEMPONT_STORES") == "bq":  # pragma: no cover
    from auth.staff import BQStaffStore
    STAFF = BQStaffStore(_sclient)
else:
    STAFF = InMemoryStaffStore()

# Pre-M5 audit shim: events collected in-process; staging loads them to
# szempont.audit_log (same row shape) through the BQ store path.
AUDIT_EVENTS: list[dict] = []


def _emit_audit(event: dict) -> None:
    AUDIT_EVENTS.append(event)


# ---- pre-M5 web hardening (F-W2-02 / F-W2-07) -------------------------------
# IAP covers WHO reaches the app (perimeter authN); it does NOT stop CSRF —
# the IAP cookie rides along on cross-site POSTs — nor XSS, nor roles (M5).
# Minimal guards until M5: (1) same-origin check on every POST; (2) one-time
# form tokens that double as replay keys, so a double-submit (retry, double
# click) replays the FIRST result instead of writing twice.
from collections import OrderedDict                              # noqa: E402
from urllib.parse import urlparse as _urlparse                   # noqa: E402

_UNUSED = object()
_FORM_TOKENS: "OrderedDict[str, object]" = OrderedDict()  # token -> _UNUSED | result
_FORM_TOKEN_CAP = 1000


@app.before_request
def _iap_guard():
    """R6: when an IAP audience is configured (staging/prod), EVERY request
    must carry a verifiable x-goog-iap-jwt-assertion — the plain email
    header is never trusted. Unset audience = dev/tests, guard off."""
    aud = iap_audience()
    if not aud:
        return None
    try:
        verify_iap_jwt(request.headers.get("x-goog-iap-jwt-assertion"), aud)
    except IapError as e:
        return f"IAP-ellenőrzés sikertelen: {e}", 401
    return None


@app.before_request
def _same_origin_guard():
    if request.method != "POST":
        return None
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        return "cross-site POST elutasítva", 403
    src = request.headers.get("Origin") or request.headers.get("Referer")
    if src and _urlparse(src).netloc and _urlparse(src).netloc != request.host:
        return "cross-site POST elutasítva", 403
    return None


def issue_form_token() -> str:
    import uuid
    tok = uuid.uuid4().hex
    _FORM_TOKENS[tok] = _UNUSED
    while len(_FORM_TOKENS) > _FORM_TOKEN_CAP:
        _FORM_TOKENS.popitem(last=False)
    return tok


def token_replay_result(tok: str | None) -> object:
    """The stored first result if this token was already used, else None.
    Check BEFORE performing the write; unknown/absent tokens (non-browser
    client, expired) count as fresh, untracked."""
    if tok and tok in _FORM_TOKENS and _FORM_TOKENS[tok] is not _UNUSED:
        return _FORM_TOKENS[tok]
    return None


def token_mark_used(tok: str | None, result: object) -> None:
    if tok and _FORM_TOKENS.get(tok) is _UNUSED:
        _FORM_TOKENS[tok] = result


# ---- M5 gated-discount approvals (W3-2, retires auto_approved_pre_m5) -------
# A successful approver-PIN check mints a one-time approval reference that
# rides the stateless quote URL (appr=...) into renders and order creation.
# Server-side map only — the token itself carries nothing.
_APPROVALS: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
_APPROVAL_CAP = 1000


def issue_approval(discount_id: str, approver: str) -> str:
    import uuid
    tok = uuid.uuid4().hex
    _APPROVALS[tok] = (discount_id, approver)
    while len(_APPROVALS) > _APPROVAL_CAP:
        _APPROVALS.popitem(last=False)
    return tok


def approval_for(tok: str | None, discount_id: str) -> str | None:
    """The approver's operator_id if tok is a valid approval FOR THIS
    discount config, else None."""
    if not tok:
        return None
    entry = _APPROVALS.get(tok)
    if entry and entry[0] == discount_id:
        return entry[1]
    return None

with open(os.path.join(HERE, "nav.json"), encoding="utf-8") as fh:
    NAV = json.load(fh)

# Szempont left-rail (IA map §1, column 2) — ClearVis vocabulary verbatim.
# Items without an endpoint are W3: rendered visible but disabled with a wave
# badge, so staff learn the final layout during the parallel run.
TOOL_NAV = [
    {"label": "Kezdőlap", "endpoint": "kezdolap"},
    {"label": "Ügyfelek", "endpoint": "ugyfel"},
    {"label": "Lencsekereső", "endpoint": "finder",
     "children": [{"label": "Konzultáció", "endpoint": "konzultacio"}]},
    {"label": "Ajánlat", "endpoint": "quote"},
    {"label": "Megrendelések", "endpoint": "megrendelesek"},
    {"label": "Eladások", "wave": "W3"},
    {"label": "Készlet", "wave": "W3"},
    {"label": "Kimutatások", "wave": "W3"},
    {"label": "Adminisztráció", "wave": "W3"},
]

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

    op_id = current_operator()
    op = operator_display(op_id)
    member = STAFF.get(op_id)
    return dict(t=t, app_name=APP_NAME, lang=lang, languages=LANGUAGES,
                density=_cookie("density", DENSITIES, "comfortable"),
                nav=NAV, nav_active=TOOL_ID, tool_nav=TOOL_NAV, huf=huf,
                operator_name=op,
                operator_role=(member.roles[0] if member else "Munkatárs"),
                operator_picked=bool(session.get("operator")),
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
                           results=results, searched=bool(q),
                           ftok=issue_form_token())


@app.route("/ugyfel/walkin", methods=["POST"])
def ugyfel_walkin():
    """Z1 walk-in capture: mints a Z1-<uuid> token (NOT a person id —
    hard rule 4), saves to szempont.walkin_persons, and continues straight
    to the finder so the walk-in never blocks a sale."""
    f = request.form
    # F-W2-07: a double-submit replays the FIRST walk-in instead of minting
    # a second Z1 token for the same person.
    prior_token = token_replay_result(f.get("ftok"))
    if prior_token is not None:
        return redirect(url_for("finder", person=prior_token))
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
                               results=[], searched=False, walkin_error=str(e),
                               ftok=issue_form_token()), 400
    WALKINS.save(w)
    token_mark_used(f.get("ftok"), w.z1_token)
    return redirect(url_for("finder", person=w.z1_token))


@app.route("/")
def kezdolap():
    """ClearVis-pattern landing (IA map row 1): ügyfélkeresés quick card
    posting into /ugyfel + the two LIVE queues (MVP override 2026-07-18):
    Mai átvételek (kiadható orders, with the értesítendő flag replacing
    M9-lite email for now) and Aláírásra váró nyilatkozatok (walk-ins
    without a signed GDPR declaration). Készlet-ellenőrzés stays W3."""
    # Pre-shell links carried finder params on "/" — forward them, nothing
    # else on this route takes query params.
    if any(k in request.args for k in ("od_sph", "os_sph", "person", "opt")):
        return redirect(url_for("finder", **request.args.to_dict(flat=False)))
    today = dt.date.today().isoformat()
    pickups = []
    for o in ORDERS.list_orders():
        if o.status in (OrderStatus.KESZ, OrderStatus.QC_KESZ):
            pv = _person_view(o.person_id or "")
            pickups.append({
                "order_id": o.order_id,
                "person": pv["name"] if pv else "—",
                "status_hu": STATUS_HU[o.status],
                "due_date": o.due_date,
                "late": o.due_date < today,
                "notified": _order_notified(o.order_id),
                "url": url_for("megrendeles", order_id=o.order_id),
            })
    pickups.sort(key=lambda r: r["due_date"])
    unsigned = [{"name": w.display_name, "z1": w.z1_token,
                 "created": w.created_at[:10]}
                for w in WALKINS.unsigned()]
    return render_template("kezdolap.html", page_title="Kezdőlap",
                           pickups=pickups, unsigned=unsigned,
                           ftok=issue_form_token())


@app.route("/lencsekereso")
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
    """D3 apply path. M5 (W3-2): gated configs need a REAL approval — an
    Üzletvezető/Cégvezető picks themselves and enters their PIN (R7); the
    POST emits exactly ONE audit event (marker=m5_pin, actor=approver) and
    redirects with a one-time approval reference. The pre-M5
    auto_approved_pre_m5 shim is retired — rows carrying that marker in
    szempont.audit_log predate this commit (migration note, F-W3-03).
    Page renders still never write audit."""
    f = request.form
    sku_r = f.get("sku_r", "")
    sku_l = f.get("sku_l") or sku_r
    options = frozenset(f.getlist("opt"))
    frame_sku = f.get("frame", "")
    person = f.get("person", "").strip()
    discount_id = f.get("discount", "")
    today = dt.date.today().isoformat()

    def back(appr: str | None = None, appr_err: str | None = None):
        return redirect(url_for(
            "quote", sku_r=sku_r, sku_l=sku_l, opt=sorted(options),
            frame=frame_sku or None, person=person or None,
            discount=discount_id or None, appr=appr, appr_err=appr_err))

    ftok = f.get("ftok")
    cfg = get_discount_config(discount_id) if discount_id else None
    if cfg is None or not cfg.requires_approval:
        return back()

    replay = token_replay_result(ftok)           # F-W2-07: no double audit
    if replay is not None:
        return back(appr=replay)

    # MVP override: approver picks themselves from the dropdown; PIN proof
    # is parked (auth/ package ready). Marker on the audit event says so.
    approver = f.get("approver", "").strip()
    member = STAFF.get(approver)
    if member is None or not member.is_approver or not member.active:
        return back(appr_err="szerep")

    try:
        *_, record = _preview_record(sku_r, sku_l, options, frame_sku,
                                     person, today)
        record = apply_discount(record, cfg, approved_by=approver)
    except (PricingError, QuoteError):
        return back()      # the GET view renders the config error
    appr = issue_approval(discount_id, approver)
    import uuid
    _emit_audit(discount_audit_event(
        record, uuid.uuid4().hex,
        dt.datetime.now(dt.timezone.utc).isoformat(),
        marker="m5_approver_no_pin"))     # PIN parked by the MVP override
    token_mark_used(ftok, appr)
    return back(appr=appr)


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
    if not sku_r:
        # Reached from the left rail with nothing configured — friendly
        # empty state (200), not the unknown-SKU 404.
        return render_template("quote.html", page_title="Quote", error=None,
                               empty=True, q=None, r=None, l=None, lines=[])
    try:
        snap, qr, ql, frame, record = _preview_record(
            sku_r, sku_l, options, frame_sku, person, today)
    except PricingError as e:
        return render_template("quote.html", page_title="Quote", error=str(e),
                               q=None, r=None, l=None, lines=[]), 404

    lens_r, lens_l = snap.lenses[sku_r], snap.lenses[sku_l]

    discount_id = request.args.get("discount", "")
    appr = request.args.get("appr", "")
    discount_error = None
    applied_config = None
    if discount_id:
        cfg = get_discount_config(discount_id)
        if cfg is None:
            discount_error = f"ismeretlen kedvezmény: {discount_id}"
        elif cfg.requires_approval:
            # M5: gated discounts price in ONLY with a live approval ref —
            # a bare ?discount=DOLG25 URL no longer applies it.
            approver = approval_for(appr, discount_id)
            if approver is None:
                discount_error = ("jóváhagyás szükséges — Üzletvezető vagy "
                                  "Cégvezető")
            else:
                try:
                    record = apply_discount(record, cfg, approved_by=approver)
                    applied_config = cfg
                except QuoteError as e:
                    discount_error = str(e)
        else:
            try:
                record = apply_discount(record, cfg, approved_by=None)
                applied_config = cfg
            except QuoteError as e:
                discount_error = str(e)
    appr_err = request.args.get("appr_err", "")
    if appr_err and not discount_error:
        discount_error = {
            "szerep": "a jóváhagyó csak Üzletvezető vagy Cégvezető lehet",
            "pin": "hibás PIN — a kedvezmény nem került jóváhagyásra",
            "zarolva": "a PIN zárolva (túl sok hibás próbálkozás) — "
                       "próbáld később",
        }.get(appr_err, "jóváhagyási hiba")

    t_ = totals(record)
    base_params = {"sku_r": sku_r, "sku_l": sku_l, "opt": sorted(options),
                   "frame": frame_sku or None, "discount": discount_id or None,
                   "appr": appr or None, "person": person or None}

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
        approvers=[m for m in STAFF.active_members() if m.is_approver],
        base_params=base_params, person_view=_person_view(person),
        ftok=issue_form_token(),
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
            # F-W2-01: per-line gross via the shared allocation — the lines
            # sum EXACTLY to the A1 total, one money path with /quote.
            basket = {
                "lines": [{"name": l.name, "gross": huf(g)}
                          for l, g in gross_line_allocation(record)],
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


# --------------------------------------------------------- M4 orders (W3-1)
_STATUS_TONE = {
    OrderStatus.FELVETT: "info", OrderStatus.MEGRENDELVE: "progress",
    OrderStatus.BEERKEZETT: "info", OrderStatus.CSISZOLAS: "progress",
    OrderStatus.KESZ: "success", OrderStatus.QC_KESZ: "success",
    OrderStatus.ATADVA: "muted", OrderStatus.LEMONDVA: "danger",
}

# ClearVis quick-filter chips, verbatim vocabulary (functional audit).
ORDER_FILTERS = (
    ("mind", "Mind"),
    ("megrendelendo", "Lencsék szállítótól megrendelendőek"),
    ("keszleten", "Készleten"),
    ("kiadhato", "Kiadható"),
    ("keso", "Késő"),
)


def _order_is_late(o, today: str) -> bool:
    return (o.due_date < today
            and o.status not in (OrderStatus.ATADVA, OrderStatus.LEMONDVA))


def _order_matches(o, szuro: str, today: str) -> bool:
    if szuro == "megrendelendo":
        return (o.status is OrderStatus.FELVETT
                and o.lens_source == "rendeles")
    if szuro == "keszleten":
        return (o.status is OrderStatus.BEERKEZETT
                or (o.status is OrderStatus.FELVETT
                    and o.lens_source == "keszlet"))
    if szuro == "kiadhato":
        return o.status in (OrderStatus.KESZ, OrderStatus.QC_KESZ)
    if szuro == "keso":
        return _order_is_late(o, today)
    return True


def _order_row(o, today: str) -> dict:
    lens = [l for l in o.lines if l.line_type == "lens" and not l.removed]
    pv = _person_view(o.person_id or "")
    return {
        "order_id": o.order_id,
        "status": o.status,
        "status_hu": STATUS_HU[o.status],
        "tone": _STATUS_TONE[o.status],
        "late": _order_is_late(o, today),
        "person": pv["name"] if pv else "—",
        "lens_summary": (lens[0].name.split(" · ", 1)[-1]
                         if lens else "(nincs lencse)"),
        "lens_source": o.lens_source,
        "order_date": o.order_date,
        "due_date": o.due_date,
        "gross": huf(order_totals(o).total_retail_gross),
        "url": url_for("megrendeles", order_id=o.order_id),
    }


@app.route("/megrendeles/uj", methods=["POST"])
def megrendeles_uj():
    """Quote → order conversion (M4). Persists the quote (saved→converted),
    mints the SZP- id (R4), saves the order (eseménynapló 'created'),
    registers R13 first-sale SKUs. Double-submit replays the FIRST order."""
    f = request.form
    prior = token_replay_result(f.get("ftok"))
    if prior is not None:
        return redirect(url_for("megrendeles", order_id=prior))
    sku_r = f.get("sku_r", "")
    sku_l = f.get("sku_l") or sku_r
    options = frozenset(f.getlist("opt"))
    frame_sku = f.get("frame", "")
    person = f.get("person", "").strip()
    discount_id = f.get("discount", "")
    lens_source = f.get("lens_source", "rendeles")
    today = dt.date.today()
    due_raw = f.get("due", "").strip()
    try:
        due = dt.date.fromisoformat(due_raw) if due_raw \
            else today + dt.timedelta(days=3)
    except ValueError:
        due = today + dt.timedelta(days=3)

    try:
        *_, record = _preview_record(sku_r, sku_l, options, frame_sku,
                                     person, today.isoformat())
        if discount_id:
            cfg = get_discount_config(discount_id)
            if cfg is None:
                # F-W3-02: an unknown discount must fail the order, not
                # silently price without it.
                return f"ismeretlen kedvezmény: {discount_id}", 400
            if cfg.requires_approval:
                # M5: a gated discount reaches the order only through a
                # live approval reference minted by the PIN'd POST.
                approver = approval_for(f.get("appr", ""), discount_id)
                if approver is None:
                    return ("a kedvezményhez Üzletvezető/Cégvezető "
                            "jóváhagyás szükséges", 400)
                record = apply_discount(record, cfg, approved_by=approver)
            else:
                record = apply_discount(record, cfg, approved_by=None)
        import uuid
        import dataclasses as _dc
        record = _dc.replace(record, quote_id=uuid.uuid4().hex)
        order_id = next_order_id(ORDERS.all_ids(), today)
        order = build_order_from_quote(
            record, order_id=order_id, created_by=current_operator(),
            created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            order_date=today.isoformat(), due_date=due.isoformat(),
            lens_source=lens_source)
        # persist the quote trail: saved revision, then converted
        saved = QUOTE_STORE.save(quote_transition(record, QuoteStatus.SAVED))
        QUOTE_STORE.save(quote_transition(saved, QuoteStatus.CONVERTED,
                                          order_id=order_id))
        ORDERS.save(order, actor=current_operator(), expect_new=True)
        new_promos = register_first_sale(PROMOTIONS, order)
        if new_promos:
            ORDERS.add_event(
                order_id, "promotion", current_operator(),
                note="Új SKU regisztrálva Tharanis cikktörzs-felvételre "
                     f"(R13): {', '.join(r.sku for r in new_promos)}")
    except (PricingError, QuoteError, OrderError) as e:
        return f"megrendelés nem hozható létre: {e}", 400
    token_mark_used(f.get("ftok"), order_id)
    return redirect(url_for("megrendeles", order_id=order_id))


@app.route("/megrendelesek")
def megrendelesek():
    """M4 order list — ClearVis quick-filter chips + időszak (list_monitor)."""
    today = dt.date.today()
    szuro = request.args.get("szuro", "mind")
    if szuro not in {k for k, _ in ORDER_FILTERS}:
        szuro = "mind"
    try:
        napok = max(1, min(365, int(request.args.get("napok", "30"))))
    except ValueError:
        napok = 30
    cutoff = (today - dt.timedelta(days=napok)).isoformat()
    t_iso = today.isoformat()
    recent = [o for o in ORDERS.list_orders() if o.order_date >= cutoff]
    rows = [_order_row(o, t_iso) for o in recent
            if _order_matches(o, szuro, t_iso)]
    counts = {key: sum(1 for o in recent if _order_matches(o, key, t_iso))
              for key, _ in ORDER_FILTERS}
    return render_template(
        "megrendelesek.html", page_title="Megrendelések", rows=rows,
        filters=ORDER_FILTERS, szuro=szuro, napok=napok, counts=counts)


@app.route("/megrendeles/<order_id>")
def megrendeles(order_id):
    """M4 order detail — lines, status actions, eseménynapló (detail_view)."""
    o = ORDERS.load(order_id)
    if o is None:
        return "ismeretlen megrendelés", 404
    today = dt.date.today().isoformat()
    t_ = order_totals(o)
    lens = [l for l in o.lines if l.line_type == "lens" and not l.removed]
    frame_line = next((l for l in o.lines
                       if l.line_type == "frame" and not l.removed), None)
    munkalap_url = url_for(
        "print_munkalap",
        sku_r=(lens[0].sku if lens else None),
        sku_l=(lens[1].sku if len(lens) > 1 else (lens[0].sku if lens else None)),
        frame=(frame_line.sku if frame_line else None),
        person=o.person_id or None, order=o.order_id, due=o.due_date)
    view = {
        "row": _order_row(o, today),
        "legacy_order_id": o.legacy_order_id,
        "quote_id": o.quote_id,
        "catalog_version": o.catalog_version,
        "cancel_reason": o.cancel_reason,
        "created_by": operator_display(o.created_by),
        "totals": {"net": huf(t_.total_retail_net),
                   "vat": huf(t_.total_vat),
                   "discount": huf(t_.discount_net),
                   "gross": huf(t_.total_retail_gross)},
        "lines": [{"type": l.line_type, "name": l.name, "sku": l.sku or "",
                   "qty": l.qty, "unit": huf(l.unit_retail_net),
                   "net": huf(l.net), "auto": l.auto_added}
                  for l in invoice_lines(o)],
        "next_statuses": [(str(s), STATUS_HU[s]) for s in allowed_next(o)],
        "terminal": o.status in (OrderStatus.ATADVA, OrderStatus.LEMONDVA),
        "munkalap_url": munkalap_url,
        "sync_status": o.sync_status,          # MVP outbox seam, read-only
        "deposit": (huf(o.deposit_gross) if o.deposit_gross else None),
        "deposit_method_hu": DEPOSIT_HU.get(o.deposit_method or "", ""),
        "remaining": huf(t_.total_retail_gross - o.deposit_gross),
        "munkalap_pdf": o.munkalap_gcs_uri,
    }
    events = [{"occurred_at": e.occurred_at.replace("T", " ")[:16],
               "actor": operator_display(e.actor),
               "type": e.event_type, "note": e.note,
               "payload": e.payload}
              for e in reversed(ORDERS.events(order_id))]
    return render_template("megrendeles.html",
                           page_title=f"Megrendelés {o.order_id}",
                           o=view, events=events,
                           person_view=_person_view(o.person_id or ""),
                           ftok=issue_form_token())


@app.route("/megrendeles/<order_id>/status", methods=["POST"])
def megrendeles_status(order_id):
    """Forward status change. Double-submit replays (no duplicate events)."""
    o = ORDERS.load(order_id)
    if o is None:
        return "ismeretlen megrendelés", 404
    if token_replay_result(request.form.get("ftok")) is not None:
        return redirect(url_for("megrendeles", order_id=order_id))
    try:
        target = OrderStatus(request.form.get("target", ""))
        ORDERS.save(transition_order(o, target), actor=current_operator())
        token_mark_used(request.form.get("ftok"), order_id)
    except (ValueError, OrderError) as e:
        return f"státuszváltás sikertelen: {e}", 400
    return redirect(url_for("megrendeles", order_id=order_id))


@app.route("/megrendeles/<order_id>/lemond", methods=["POST"])
def megrendeles_lemond(order_id):
    """R7: ANY staff member may cancel; reason mandatory; the store writes
    the audit_log event with the actor. Confirm happens in the UI."""
    o = ORDERS.load(order_id)
    if o is None:
        return "ismeretlen megrendelés", 404
    if token_replay_result(request.form.get("ftok")) is not None:
        return redirect(url_for("megrendeles", order_id=order_id))
    try:
        ORDERS.save(cancel_order(o, reason=request.form.get("reason", "")),
                    actor=current_operator())
        token_mark_used(request.form.get("ftok"), order_id)
    except OrderError as e:
        return f"lemondás sikertelen: {e}", 400
    return redirect(url_for("megrendeles", order_id=order_id))


# MVP override 2026-07-18: no Tharanis surface in the app. Orders carry
# sync_status='pending' (queued outbox); the future verified R1 integration
# drains them. vendors/tharanis.py stays parked for that day.
DEPOSIT_HU = {"keszpenz": "Készpénz", "kartya": "Bankkártya",
              "utalas": "Átutalás"}


@app.route("/megrendeles/<order_id>/eloleg", methods=["POST"])
def megrendeles_eloleg(order_id):
    """MVP deposit: gross amount + method on the order (no invoice, no
    Szamlazz). The fizetési összesítő print shows it."""
    from orders.records import record_deposit
    o = ORDERS.load(order_id)
    if o is None:
        return "ismeretlen megrendelés", 404
    if token_replay_result(request.form.get("ftok")) is not None:
        return redirect(url_for("megrendeles", order_id=order_id))
    raw = (request.form.get("amount") or "").replace(" ", "")\
        .replace(" ", "").strip()
    method = request.form.get("method", "")
    try:
        amount = Decimal(raw)
    except Exception:
        return "érvénytelen összeg", 400
    try:
        o2 = record_deposit(o, gross=amount, method=method)
        ORDERS.save(o2, actor=current_operator(),
                    event_note=f"Előleg rögzítve: {huf(amount)} "
                               f"({DEPOSIT_HU.get(method, method)})")
        token_mark_used(request.form.get("ftok"), order_id)
    except OrderError as e:
        return f"előleg sikertelen: {e}", 400
    return redirect(url_for("megrendeles", order_id=order_id))


@app.route("/megrendeles/<order_id>/ertesitve", methods=["POST"])
def megrendeles_ertesitve(order_id):
    """MVP replacement for M9-lite: staff mark 'ügyfél értesítve' by hand
    (phone call); the Mai átvételek queue clears its értesítendő flag."""
    o = ORDERS.load(order_id)
    if o is None:
        return "ismeretlen megrendelés", 404
    if token_replay_result(request.form.get("ftok")) is None:
        ORDERS.add_event(order_id, "note", current_operator(),
                         note="Ügyfél értesítve (telefonon / személyesen)")
        token_mark_used(request.form.get("ftok"), order_id)
    return redirect(request.form.get("next")
                    if (request.form.get("next") or "").startswith("/")
                    else url_for("megrendeles", order_id=order_id))


def _order_notified(order_id: str) -> bool:
    return any(e.event_type == "note" and "értesítve" in e.note.lower()
               for e in ORDERS.events(order_id))


# ------------------------------------------------- munkalap PDF (R11, MVP)
def _docs_dir() -> str:
    """Local PDF root. GCS (gs://szempont-docs) takes over when
    SZEMPONT_DOCS_BUCKET is set at the infra step; local keeps staging and
    the rehearsal working today (override: GCS-optional)."""
    return os.environ.get("SZEMPONT_DOCS_DIR",
                          os.path.join(os.path.dirname(HERE), "var", "docs"))


def _munkalap_pdf_local(order_id: str, order_date: str) -> str:
    y, m = order_date[:4], order_date[5:7]
    return os.path.join(_docs_dir(), "munkalap", y, m, f"{order_id}.pdf")


@app.route("/megrendeles/<order_id>/munkalap-pdf", methods=["POST"])
def megrendeles_munkalap_pdf(order_id):
    """Render the frozen munkalap for THIS order to PDF (wkhtmltopdf),
    store it (local dir; GCS when configured), remember the uri on the
    order (R11) and log the event."""
    import shutil
    import subprocess
    import tempfile
    o = ORDERS.load(order_id)
    if o is None:
        return "ismeretlen megrendelés", 404
    if token_replay_result(request.form.get("ftok")) is not None:
        return redirect(url_for("megrendeles", order_id=order_id))
    if shutil.which("wkhtmltopdf") is None:
        ORDERS.add_event(order_id, "note", current_operator(),
                         note="Munkalap PDF sikertelen: wkhtmltopdf hiányzik "
                              "a gépről (deploy checklist)")
        return redirect(url_for("megrendeles", order_id=order_id))

    lens = [l for l in o.lines if l.line_type == "lens" and not l.removed]
    frame_line = next((l for l in o.lines
                       if l.line_type == "frame" and not l.removed), None)
    vals = {"sku_r": lens[0].sku if lens else "",
            "sku_l": (lens[1].sku if len(lens) > 1
                      else (lens[0].sku if lens else "")),
            "frame": frame_line.sku if frame_line else "",
            "person": o.person_id or "", "order": o.order_id,
            "job": o.order_id.replace("SZP", "ML", 1), "due": o.due_date}
    html, err = _munkalap_html(lambda k, d="": vals.get(k) or d)
    if err:
        return err, 404
    pdf_path = _munkalap_pdf_local(o.order_id, o.order_date)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(html)
        tmp_html = fh.name
    try:
        subprocess.run(["wkhtmltopdf", "--quiet",
                        "--enable-local-file-access", tmp_html, pdf_path],
                       check=True, timeout=60)
    finally:
        os.unlink(tmp_html)

    uri = pdf_path
    bucket = os.environ.get("SZEMPONT_DOCS_BUCKET")
    if bucket:  # pragma: no cover — staging with GCS configured
        from google.cloud import storage
        blob_path = (f"munkalap/{o.order_date[:4]}/{o.order_date[5:7]}/"
                     f"{o.order_id}.pdf")
        storage.Client().bucket(bucket).blob(blob_path)\
            .upload_from_filename(pdf_path)
        uri = f"gs://{bucket}/{blob_path}"
    import dataclasses as _dc
    ORDERS.save(_dc.replace(o, munkalap_gcs_uri=uri),
                actor=current_operator(),
                event_note=f"Munkalap PDF elkészült: {uri}")
    token_mark_used(request.form.get("ftok"), order_id)
    return redirect(url_for("megrendeles", order_id=order_id))


@app.route("/megrendeles/<order_id>/munkalap.pdf")
def megrendeles_munkalap_pdf_file(order_id):
    """Serve the locally stored munkalap PDF (GCS uris are opened via the
    console/signed links at the infra step)."""
    from flask import send_file
    o = ORDERS.load(order_id)
    if o is None or not o.munkalap_gcs_uri \
            or o.munkalap_gcs_uri.startswith("gs://") \
            or not os.path.exists(o.munkalap_gcs_uri):
        return "nincs tárolt munkalap PDF", 404
    return send_file(o.munkalap_gcs_uri, mimetype="application/pdf")


@app.route("/print/fizetesi-osszesito")
def print_fizetesi_osszesito():
    """MVP payment summary print — NOT an invoice, marked NEM SZÁMLA on the
    sheet. Covers the rehearsal need until M8/Szamlazz (deferred)."""
    o = ORDERS.load(request.args.get("order", ""))
    if o is None:
        return "ismeretlen megrendelés", 404
    t_ = order_totals(o)
    alloc = gross_line_allocation(o)
    p = _person_print_fields(o.person_id or "")
    today = dt.date.today()
    fo = {
        "order_id": o.order_id,
        "order_date": o.order_date,
        "customer_name": p["name"] or "—",
        "customer_id": p["id"] or "—",
        "lines": [{"name": l.name, "qty": l.qty, "gross": huf(g)}
                  for l, g in alloc],
        "vat_note": f"Az árak {o.vat_rate * 100:.0f}% ÁFÁ-t tartalmaznak.",
        "gross": huf(t_.total_retail_gross),
        "deposit": huf(o.deposit_gross) if o.deposit_gross else None,
        "deposit_method": DEPOSIT_HU.get(o.deposit_method or "", ""),
        "remaining": huf(t_.total_retail_gross - o.deposit_gross),
        "operator": operator_display(o.created_by),
        "printed_at": _hu_date(today) + f" {dt.datetime.now():%H:%M}",
    }
    return render_template("print/fizetesi_osszesito.html", fo=fo)


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


@app.route("/print/munkalap", methods=["GET", "POST"])
def print_munkalap():
    """Lab glazing sheet — design-frozen template, data wired in (item 4b).
    POST supported (F-W2-04): Rx values in a POST body stay out of request
    logs; real print flows must POST, GET remains for links/demos."""
    html, err = _munkalap_html(request.values.get)
    if err:
        return err, 404
    return html


def _munkalap_html(a) -> tuple[str | None, str | None]:
    """Render the frozen munkalap from a value getter — shared by the print
    route (request.values.get) and the order-PDF generator (order fields).
    Real Code-128 (order, lens SKUs) and EAN-13 (frame GTIN) inline SVGs;
    centration fields stay blank when not passed (pencil-friendly)."""
    snap = load_snapshot()
    sku_r = a("sku_r") or a("sku", "")
    sku_l = a("sku_l") or sku_r
    lens_r, lens_l = snap.lenses.get(sku_r), snap.lenses.get(sku_l)
    if lens_r is None or lens_l is None:
        return None, f"ismeretlen SKU: {sku_r if lens_r is None else sku_l}"

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
    return render_template("print/munkalap.html", ml=ml), None


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


@app.route("/print/latasvizsgalat", methods=["GET", "POST"])
def print_latasvizsgalat():
    """Exam-result + suggested-correction sheet — design-frozen template.
    PURE PASS-THROUGH: values exist only in this request; Szempont stores no
    Rx/health data (hard rule 5 — IRIS owns it, M6 reads via contract).
    POST supported (F-W2-04): health data in a POST body stays out of
    request logs — the future exam UI MUST POST here; GET is for the ?demo=1
    layout check. Person fields prefill from the directory/walk-in."""
    d = {k: v for k, v in request.values.items()
         if k not in ("demo", "person")}
    if request.values.get("demo") == "1":
        d = {**DEMO_EXAM, **d}
    person = request.values.get("person", "").strip()
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
