"""Szempont M2 — quote persistence records (pure domain layer).

Maps engine Quotes + frame/service lines + payer data onto the
szempont.quotes schema (DDL 001 + 002). Pure functions over frozen
dataclasses: no I/O, no clock, no randomness — ids and timestamps come in as
arguments, so a persisted quote is as reproducible as the engine Quote it
wraps (acceptance criterion, spec §3.1).

Rulings applied (2026-07-16, frozen — do not reopen):
  D1  payer block (egészségpénztár) on the quote; flows to order/invoice.
  D2  service lines; EVERY line optician-editable; auto-added munkadíj is
      basket-only — removal is a flag, the invoice renders non-removed lines.
  D3  discounts only via curated DiscountConfig; approval gating + audit.
  D6  offer variants: carousel variants share offer_set_id; each variant is
      a full quote row.
  A1  ROUND_HALF_UP to whole HUF on the final gross only (frozen).

Price overrides (lens_price_overrides) are NOT discounts: when the engine
applied one, the delta vs. list price is persisted as an auto-added
line_type='discount' line ("Akciós ár") so line sums always equal the
engine total and the printed quote shows the saving.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Sequence

from pricing.models import Quote

_HUF = Decimal("1")
_ZERO = Decimal("0")


class QuoteError(Exception):
    """Invalid quote construction, edit, payer data, or status transition."""


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    SAVED = "saved"
    PRINTED = "printed"
    CONVERTED = "converted"
    EXPIRED = "expired"


_TRANSITIONS: dict[QuoteStatus, set[QuoteStatus]] = {
    QuoteStatus.DRAFT: {QuoteStatus.SAVED, QuoteStatus.EXPIRED},
    QuoteStatus.SAVED: {QuoteStatus.PRINTED, QuoteStatus.CONVERTED,
                        QuoteStatus.EXPIRED},
    QuoteStatus.PRINTED: {QuoteStatus.CONVERTED, QuoteStatus.EXPIRED},
    QuoteStatus.CONVERTED: set(),
    QuoteStatus.EXPIRED: set(),
}

# D2: edits allowed while the quote is still a working document.
_EDITABLE = {QuoteStatus.DRAFT, QuoteStatus.SAVED}

LINE_TYPES = ("frame", "lens", "option", "service", "discount")


@dataclass(frozen=True, slots=True)
class QuoteLineRec:
    """One persisted quote line (szempont.quotes.lines struct)."""
    line_type: str                    # frame|lens|option|service|discount
    sku: str | None
    name: str
    qty: int
    unit_retail_net: Decimal
    auto_added: bool = False          # D2: system-added (munkadíj, akciós ár)
    removed: bool = False             # D2: soft delete — kept, never rendered
    source: str | None = None         # discount lines only: 'config' (D3, quote
                                      # carries discount_config_id) | 'override'
                                      # (lens_price_overrides; sku = override_id)

    @property
    def net(self) -> Decimal:
        return self.unit_retail_net * self.qty


@dataclass(frozen=True, slots=True)
class ServiceLine:
    """Input shape for service lines (szemüvegkészítés munkadíj, javítás...)."""
    name: str
    retail_net: Decimal
    qty: int = 1


@dataclass(frozen=True, slots=True)
class PayerInfo:
    """D1 egészségpénztár support. payer_type='person' = the customer pays;
    'health_fund' = invoice goes to the fund for the named member."""
    payer_type: str = "person"        # person | health_fund
    payer_name: str | None = None     # e.g. 'OTP Egészségpénztár'
    payer_member_name: str | None = None
    payer_member_id: str | None = None
    payer_billing_address: str | None = None


@dataclass(frozen=True, slots=True)
class DiscountConfig:
    """D3: curated structured discount (szempont.discount_configs row)."""
    config_id: str
    name: str
    kind: str                         # percent | amount_net
    value: Decimal
    applies_to_line_types: frozenset[str] = frozenset()  # empty = whole basket
    requires_approval: bool = False
    valid_from: str = ""              # ISO date, inclusive
    valid_to: str | None = None       # ISO date, inclusive; None = open-ended
    active: bool = True

    def active_on(self, quote_date: str) -> bool:
        if not self.active or quote_date < self.valid_from:
            return False
        return self.valid_to is None or quote_date <= self.valid_to


@dataclass(frozen=True, slots=True)
class QuoteRecord:
    """One revision of one quote (= one szempont.quotes row).

    Totals are never stored on the record — totals() derives them from the
    lines so an edited line can never leave a stale total behind. person_id
    is an IRIS id or a Z1-<uuid> walk-in token, never minted here (rule 4).
    """
    quote_id: str
    catalog_version: str
    quote_date: str                   # ISO date
    status: QuoteStatus
    lines: tuple[QuoteLineRec, ...]
    vat_rate: Decimal
    created_by: str
    created_at: str                   # ISO timestamp, first save
    person_id: str | None = None
    payer: PayerInfo = PayerInfo()
    offer_set_id: str | None = None   # D6
    variant_label: str | None = None  # D6: 'Alap' | 'Ajánlott' | 'Prémium' | custom
    discount_net: Decimal = _ZERO     # D3
    discount_config_id: str | None = None
    discount_approved_by: str | None = None
    revision: int = 0
    saved_at: str = ""                # ISO timestamp of this revision
    converted_order_id: str | None = None


@dataclass(frozen=True, slots=True)
class Totals:
    basket_net: Decimal               # non-removed lines, before discount
    discount_net: Decimal
    total_retail_net: Decimal         # payable net = basket - discount
    total_vat: Decimal
    total_retail_gross: Decimal       # whole HUF, ROUND_HALF_UP (A1, frozen)


# --------------------------------------------------------------------- totals
def _basket_net(lines: Sequence[QuoteLineRec],
                line_types: frozenset[str] = frozenset()) -> Decimal:
    return sum((l.net for l in lines if not l.removed
                and (not line_types or l.line_type in line_types)), _ZERO)


def totals(record: QuoteRecord) -> Totals:
    basket = _basket_net(record.lines)
    net = basket - record.discount_net
    gross = (net * (1 + record.vat_rate)).quantize(_HUF, rounding=ROUND_HALF_UP)
    return Totals(basket_net=basket, discount_net=record.discount_net,
                  total_retail_net=net, total_vat=gross - net,
                  total_retail_gross=gross)


def invoice_lines(record: QuoteRecord) -> tuple[QuoteLineRec, ...]:
    """D2: the invoice/munkalap renders only non-removed lines."""
    return tuple(l for l in record.lines if not l.removed)


def gross_line_allocation(
        record: QuoteRecord) -> tuple[tuple[QuoteLineRec, Decimal], ...]:
    """Customer-facing per-line gross figures that sum EXACTLY to the A1
    total (F-W2-01): rounding each line's gross independently can drift from
    the once-rounded quote total by ±1 Ft per line. Largest-remainder
    allocation of totals().total_retail_gross across the non-removed lines,
    pro-rata by line net, closes the gap — every UI that shows per-line gross
    goes through here, so lines can never disagree with the quote total."""
    from decimal import ROUND_FLOOR
    t = totals(record)
    lines = invoice_lines(record)
    if not lines:
        return ()
    if t.basket_net == 0:
        out = [(l, _ZERO) for l in lines]
        return ((lines[0], t.total_retail_gross),) + tuple(out[1:]) \
            if t.total_retail_gross else tuple(out)
    raw = [l.net * t.total_retail_gross / t.basket_net for l in lines]
    floors = [r.quantize(_HUF, rounding=ROUND_FLOOR) for r in raw]
    remainder = int(t.total_retail_gross - sum(floors))
    order = sorted(range(len(lines)), key=lambda i: raw[i] - floors[i],
                   reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    return tuple(zip(lines, floors))


# -------------------------------------------------------------------- builder
def _lines_from_engine(eye: str | None, q: Quote) -> list[QuoteLineRec]:
    prefix = f"{eye} · " if eye else ""
    base, *opts = q.lines
    out = [QuoteLineRec("lens", q.sku, prefix + base.name, q.quantity,
                        base.retail_net)]
    out += [QuoteLineRec("option", l.code, prefix + l.name, q.quantity,
                         l.retail_net) for l in opts]
    if q.override_applied:
        delta = q.unit_retail_net - sum((l.retail_net for l in q.lines), _ZERO)
        if delta != 0:
            out.append(QuoteLineRec(
                "discount", q.override_applied,   # sku = override_id (structured)
                prefix + f"Akciós ár ({q.override_applied})",
                q.quantity, delta, auto_added=True, source="override"))
    return out


def build_quote_record(
    *,
    quote_id: str,
    quote_date: str,
    created_by: str,
    created_at: str,
    engine_quotes: Sequence[tuple[str | None, Quote]] = (),  # (eye label, Quote)
    frame: tuple[str, str, Decimal] | None = None,  # (sku, name, retail_net)
    services: Sequence[ServiceLine] = (),
    auto_services: Sequence[ServiceLine] = (),      # D2: munkadíj auto-add,
                                                    # basket only, removable
    person_id: str | None = None,
    payer: PayerInfo = PayerInfo(),
    offer_set_id: str | None = None,
    variant_label: str | None = None,
    catalog_version: str | None = None,             # required if no engine quotes
    vat_rate: Decimal | None = None,                # required if no engine quotes
) -> QuoteRecord:
    if engine_quotes:
        versions = {q.catalog_version for _, q in engine_quotes}
        vats = {q.vat_rate for _, q in engine_quotes}
        dates = {q.quote_date for _, q in engine_quotes}
        if len(versions) > 1 or len(vats) > 1:
            raise QuoteError(f"engine quotes span catalog versions {versions} "
                             f"/ VAT rates {vats}; one quote = one snapshot")
        if dates != {quote_date}:
            raise QuoteError(f"engine quote dates {dates} != quote_date "
                             f"{quote_date!r} (reproducibility anchor)")
        catalog_version = versions.pop()
        vat_rate = vats.pop()
    if catalog_version is None or vat_rate is None:
        raise QuoteError("catalog_version and vat_rate are required when "
                         "no engine quotes are given")

    lines: list[QuoteLineRec] = []
    for eye, q in engine_quotes:
        lines += _lines_from_engine(eye, q)
    if frame is not None:
        sku, name, retail = frame
        lines.append(QuoteLineRec("frame", sku, name, 1, retail))
    lines += [QuoteLineRec("service", None, s.name, s.qty, s.retail_net)
              for s in services]
    lines += [QuoteLineRec("service", None, s.name, s.qty, s.retail_net,
                           auto_added=True) for s in auto_services]

    validate_payer(payer)
    return QuoteRecord(
        quote_id=quote_id, catalog_version=catalog_version,
        quote_date=quote_date, status=QuoteStatus.DRAFT, lines=tuple(lines),
        vat_rate=vat_rate, created_by=created_by, created_at=created_at,
        person_id=person_id, payer=payer,
        offer_set_id=offer_set_id, variant_label=variant_label,
    )


def assign_offer_set(records: Sequence[QuoteRecord], offer_set_id: str,
                     labels: Sequence[str]) -> tuple[QuoteRecord, ...]:
    """D6: stamp carousel variants with a shared offer_set_id + labels."""
    if len(records) != len(labels):
        raise QuoteError("one label per variant required")
    if len({r.quote_id for r in records}) != len(records):
        raise QuoteError("offer set variants must have distinct quote_ids")
    return tuple(dataclasses.replace(r, offer_set_id=offer_set_id,
                                     variant_label=lab)
                 for r, lab in zip(records, labels))


# --------------------------------------------------------------- edits (D2)
def _require_editable(record: QuoteRecord) -> None:
    if record.status not in _EDITABLE:
        raise QuoteError(f"quote {record.quote_id} is {record.status} — "
                         "not editable")


def _replace_line(record: QuoteRecord, index: int,
                  **changes) -> QuoteRecord:
    _require_editable(record)
    if not 0 <= index < len(record.lines):
        raise QuoteError(f"no line at index {index}")
    lines = list(record.lines)
    lines[index] = dataclasses.replace(lines[index], **changes)
    return dataclasses.replace(record, lines=tuple(lines))


def edit_line(record: QuoteRecord, index: int, *, name: str | None = None,
              qty: int | None = None,
              unit_retail_net: Decimal | None = None) -> QuoteRecord:
    """D2: every line is optician-editable (incl. auto-added service lines)."""
    changes: dict = {}
    if name is not None:
        changes["name"] = name
    if qty is not None:
        if qty < 1:
            raise QuoteError("qty must be >= 1; use remove_line to drop a line")
        changes["qty"] = qty
    if unit_retail_net is not None:
        changes["unit_retail_net"] = unit_retail_net
    if not changes:
        raise QuoteError("nothing to edit")
    return _replace_line(record, index, **changes)


def remove_line(record: QuoteRecord, index: int) -> QuoteRecord:
    """Soft delete: the row stays (audit/history), invoice skips it."""
    return _replace_line(record, index, removed=True)


def restore_line(record: QuoteRecord, index: int) -> QuoteRecord:
    return _replace_line(record, index, removed=False)


def add_service_line(record: QuoteRecord, service: ServiceLine,
                     auto_added: bool = False) -> QuoteRecord:
    _require_editable(record)
    line = QuoteLineRec("service", None, service.name, service.qty,
                        service.retail_net, auto_added=auto_added)
    return dataclasses.replace(record, lines=record.lines + (line,))


# ------------------------------------------------------------ discounts (D3)
def apply_discount(record: QuoteRecord, config: DiscountConfig,
                   approved_by: str | None = None) -> QuoteRecord:
    """Apply one curated discount config; replaces any prior discount."""
    _require_editable(record)
    if not config.active_on(record.quote_date):
        raise QuoteError(f"discount config {config.config_id} not active "
                         f"on {record.quote_date}")
    if config.requires_approval and not approved_by:
        raise QuoteError(f"discount {config.config_id} requires approval "
                         "(discount_approved_by)")
    base = _basket_net(record.lines, config.applies_to_line_types)
    if config.kind == "percent":
        if not _ZERO <= config.value <= Decimal("100"):
            raise QuoteError(f"percent discount out of range: {config.value}")
        discount = base * config.value / Decimal("100")
    elif config.kind == "amount_net":
        discount = min(config.value, base)   # never drive the quote negative
    else:
        raise QuoteError(f"unknown discount kind {config.kind!r}")
    return dataclasses.replace(
        record, discount_net=discount, discount_config_id=config.config_id,
        discount_approved_by=approved_by)


def clear_discount(record: QuoteRecord) -> QuoteRecord:
    _require_editable(record)
    return dataclasses.replace(record, discount_net=_ZERO,
                               discount_config_id=None,
                               discount_approved_by=None)


# ------------------------------------------------------------------ payer (D1)
def validate_payer(payer: PayerInfo) -> None:
    if payer.payer_type not in ("person", "health_fund"):
        raise QuoteError(f"unknown payer_type {payer.payer_type!r}")
    if payer.payer_type == "health_fund":
        if not payer.payer_name or not payer.payer_member_id:
            raise QuoteError("health_fund payer requires payer_name and "
                             "payer_member_id (D1)")


def payer_invoice_ready(payer: PayerInfo) -> bool:
    """Full D1 block needed before the Szamlazz invoice can go to the fund."""
    if payer.payer_type != "health_fund":
        return True
    return all((payer.payer_name, payer.payer_member_name,
                payer.payer_member_id, payer.payer_billing_address))


# ------------------------------------------------------------------- lifecycle
def transition(record: QuoteRecord, new_status: QuoteStatus,
               *, order_id: str | None = None) -> QuoteRecord:
    if new_status not in _TRANSITIONS[record.status]:
        raise QuoteError(f"illegal transition {record.status} -> {new_status}")
    if new_status is QuoteStatus.CONVERTED:
        if not order_id:
            raise QuoteError("converted requires the order_id")
        return dataclasses.replace(record, status=new_status,
                                   converted_order_id=order_id)
    return dataclasses.replace(record, status=new_status)


# --------------------------------------------------------------- BQ (de)serde
def to_bq_row(record: QuoteRecord) -> dict:
    """JSON-load-ready row for szempont.quotes (NUMERIC as strings)."""
    t = totals(record)
    p = record.payer
    return {
        "quote_id": record.quote_id,
        "catalog_version": record.catalog_version,
        "quote_date": record.quote_date,
        "person_id": record.person_id,
        "status": str(record.status),
        "lines": [{
            "line_type": l.line_type, "sku": l.sku, "name": l.name,
            "qty": l.qty, "unit_retail_net": str(l.unit_retail_net),
            "auto_added": l.auto_added, "removed": l.removed,
            "source": l.source,
        } for l in record.lines],
        "payer_type": p.payer_type,
        "payer_name": p.payer_name,
        "payer_member_name": p.payer_member_name,
        "payer_member_id": p.payer_member_id,
        "payer_billing_address": p.payer_billing_address,
        "offer_set_id": record.offer_set_id,
        "variant_label": record.variant_label,
        "vat_rate": str(record.vat_rate),
        "total_retail_net": str(t.total_retail_net),
        "total_retail_gross": str(t.total_retail_gross),
        "discount_net": str(record.discount_net),
        "discount_config_id": record.discount_config_id,
        "discount_approved_by": record.discount_approved_by,
        "revision": record.revision,
        "saved_at": record.saved_at or None,
        "created_by": record.created_by,
        "created_at": record.created_at,
        "converted_order_id": record.converted_order_id,
    }


def from_bq_row(row: dict) -> QuoteRecord:
    return QuoteRecord(
        quote_id=row["quote_id"],
        catalog_version=row["catalog_version"],
        quote_date=str(row["quote_date"]),
        status=QuoteStatus(row["status"]),
        lines=tuple(QuoteLineRec(
            line_type=l["line_type"], sku=l["sku"], name=l["name"],
            qty=int(l["qty"]), unit_retail_net=Decimal(str(l["unit_retail_net"])),
            auto_added=bool(l["auto_added"]), removed=bool(l["removed"]),
            source=l.get("source"),
        ) for l in row["lines"]),
        vat_rate=Decimal(str(row["vat_rate"])),
        created_by=row["created_by"],
        created_at=str(row["created_at"]),
        person_id=row.get("person_id"),
        payer=PayerInfo(
            payer_type=row.get("payer_type") or "person",
            payer_name=row.get("payer_name"),
            payer_member_name=row.get("payer_member_name"),
            payer_member_id=row.get("payer_member_id"),
            payer_billing_address=row.get("payer_billing_address"),
        ),
        offer_set_id=row.get("offer_set_id"),
        variant_label=row.get("variant_label"),
        discount_net=Decimal(str(row.get("discount_net") or "0")),
        discount_config_id=row.get("discount_config_id"),
        discount_approved_by=row.get("discount_approved_by"),
        revision=int(row.get("revision") or 0),
        saved_at=str(row.get("saved_at") or ""),
        converted_order_id=row.get("converted_order_id"),
    )
