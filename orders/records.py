"""Szempont M4 — order records (pure domain layer, W3-1).

Same discipline as quotes/records.py: frozen dataclasses, no I/O, no clock —
ids and timestamps come in as arguments. An order is born from a saved quote
(build_order_from_quote): it COPIES the quote's non-removed lines, payer and
discount state, so later catalog changes can never reprice a taken order
(reproducibility anchor = the quote's catalog_version, carried along).

Rulings applied (Mega Review 2026-07-18, frozen):
  R4   order ids are SZP- prefixed (orders/ids.py); migrated ClearVisio
       orders keep their SO- id in legacy_order_id (R18) — Szempont never
       mints SO- ids.
  R7   cancel (lemondás) is allowed to ANY staff member from any non-terminal
       status; every cancel is audited with the actor (store layer emits the
       szempont.audit_log event — cancel_order here only enforces the machine).
  R10  lab statuses beérkezett→csiszolás→kész→QC-kész. QC-kész is a PLAIN
       status: no digital enforcement of who performs QC — the two-person
       rule lives on the paper munkalap.
  R1   nothing here talks to Tharanis; the sink adapter is dry-run only.

Line shape is quotes.records.QuoteLineRec, unchanged — orders and quotes
stay serde-symmetric and quotes.records.totals()/invoice_lines()/
gross_line_allocation() work on OrderRecord too (same attribute names).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from quotes.records import (PayerInfo, QuoteLineRec, QuoteRecord, Totals,
                            totals as _quote_totals, validate_payer)

_ZERO = Decimal("0")


class OrderError(Exception):
    """Invalid order construction, edit, or status transition."""


class OrderStatus(StrEnum):
    FELVETT = "felvett"            # recorded, nothing ordered yet
    MEGRENDELVE = "megrendelve"    # lens ordered from supplier
    BEERKEZETT = "beerkezett"      # lens arrived (or taken from stock)
    CSISZOLAS = "csiszolas"        # M7 lab: glazing in progress
    KESZ = "kesz"                  # M7 lab: glasses finished
    QC_KESZ = "qc_kesz"            # M7 lab: QC done (plain status, R10)
    ATADVA = "atadva"              # handed over to the customer
    LEMONDVA = "lemondva"          # cancelled (any staff, audited — R7)


# ClearVis vocabulary for pills and chips (IA map: same Hungarian word).
STATUS_HU: dict[OrderStatus, str] = {
    OrderStatus.FELVETT: "Felvett",
    OrderStatus.MEGRENDELVE: "Megrendelve",
    OrderStatus.BEERKEZETT: "Beérkezett",
    OrderStatus.CSISZOLAS: "Csiszolás",
    OrderStatus.KESZ: "Kész",
    OrderStatus.QC_KESZ: "QC-kész",
    OrderStatus.ATADVA: "Átadva",
    OrderStatus.LEMONDVA: "Lemondva",
}

_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    # stock lenses skip the supplier leg: felvett -> beerkezett directly
    OrderStatus.FELVETT: {OrderStatus.MEGRENDELVE, OrderStatus.BEERKEZETT},
    OrderStatus.MEGRENDELVE: {OrderStatus.BEERKEZETT},
    OrderStatus.BEERKEZETT: {OrderStatus.CSISZOLAS, OrderStatus.KESZ},
    OrderStatus.CSISZOLAS: {OrderStatus.KESZ},
    OrderStatus.KESZ: {OrderStatus.QC_KESZ, OrderStatus.ATADVA},
    OrderStatus.QC_KESZ: {OrderStatus.ATADVA},
    OrderStatus.ATADVA: set(),
    OrderStatus.LEMONDVA: set(),
}

TERMINAL = {OrderStatus.ATADVA, OrderStatus.LEMONDVA}

# Parity checklist §2: lens fulfilment source — Rendelésből / Készletről.
LENS_SOURCES = ("rendeles", "keszlet")


@dataclass(frozen=True, slots=True)
class OrderRecord:
    """One revision of one order (= one szempont.orders row).

    Totals derive from the lines (order_totals), never stored stale.
    person_id is an IRIS id or Z1 token — never minted here (rule 4).
    tharanis_sorszam stays None until a verified LIVE berak succeeds
    (F-W3-01 follow-up + tripwire); dry-run artifacts live on the event log.
    """
    order_id: str                     # SZP-YYMM-NNNN (R4)
    quote_id: str
    catalog_version: str
    order_date: str                   # ISO date
    status: OrderStatus
    lines: tuple[QuoteLineRec, ...]
    vat_rate: Decimal
    lens_source: str                  # rendeles | keszlet
    due_date: str                     # ISO date (vállalt határidő)
    created_by: str
    created_at: str                   # ISO timestamp
    person_id: str | None = None
    payer: PayerInfo = PayerInfo()
    discount_net: Decimal = _ZERO
    discount_config_id: str | None = None
    discount_approved_by: str | None = None
    legacy_order_id: str | None = None   # R18: migrated ClearVisio SO- id
    channel: str = "store-terez50"
    munkalap_gcs_uri: str | None = None  # R11 (W3-3)
    tharanis_sorszam: str | None = None  # set only by a verified live write
    cancel_reason: str | None = None
    revision: int = 0
    saved_at: str = ""


def order_totals(order: OrderRecord) -> Totals:
    """Same money path as quotes (A1 rounding, F-W2-01 allocation reuse)."""
    return _quote_totals(order)  # duck-typed: same attribute names


def build_order_from_quote(
    quote: QuoteRecord,
    *,
    order_id: str,
    created_by: str,
    created_at: str,
    order_date: str,
    due_date: str,
    lens_source: str = "rendeles",
) -> OrderRecord:
    """Convert a quote into a new order (status felvett).

    Copies the quote's NON-REMOVED lines (D2: removed lines are quote
    history, not order content), payer block and discount state verbatim.
    The caller transitions the quote to CONVERTED and persists both.
    """
    if lens_source not in LENS_SOURCES:
        raise OrderError(f"unknown lens_source {lens_source!r}")
    if not order_id.startswith("SZP-"):
        raise OrderError(f"order ids are SZP- prefixed (R4), got {order_id!r}")
    lines = tuple(l for l in quote.lines if not l.removed)
    if not any(l.line_type in ("lens", "frame") for l in lines):
        raise OrderError("an order needs at least one lens or frame line")
    if due_date < order_date:
        raise OrderError(f"due_date {due_date} is before order_date {order_date}")
    validate_payer(quote.payer)
    return OrderRecord(
        order_id=order_id, quote_id=quote.quote_id,
        catalog_version=quote.catalog_version, order_date=order_date,
        status=OrderStatus.FELVETT, lines=lines, vat_rate=quote.vat_rate,
        lens_source=lens_source, due_date=due_date,
        created_by=created_by, created_at=created_at,
        person_id=quote.person_id, payer=quote.payer,
        discount_net=quote.discount_net,
        discount_config_id=quote.discount_config_id,
        discount_approved_by=quote.discount_approved_by,
    )


def transition_order(order: OrderRecord, new_status: OrderStatus) -> OrderRecord:
    """Forward status changes. Cancel goes through cancel_order (R7 audit)."""
    if new_status is OrderStatus.LEMONDVA:
        raise OrderError("use cancel_order for lemondás (R7: audited path)")
    if new_status not in _TRANSITIONS[order.status]:
        raise OrderError(f"illegal transition {order.status} -> {new_status}")
    return dataclasses.replace(order, status=new_status)


def cancel_order(order: OrderRecord, *, reason: str) -> OrderRecord:
    """R7: ANY staff member may cancel any non-terminal order. The store
    layer MUST write the audit_log event with the actor for every cancel —
    this function only enforces the machine and records the reason."""
    if order.status in TERMINAL:
        raise OrderError(f"order {order.order_id} is {order.status} — "
                         "terminal, cannot cancel")
    if not reason.strip():
        raise OrderError("cancel requires a reason (audit trail)")
    return dataclasses.replace(order, status=OrderStatus.LEMONDVA,
                               cancel_reason=reason.strip())


def allowed_next(order: OrderRecord) -> tuple[OrderStatus, ...]:
    """Forward transitions available from the current status (UI buttons)."""
    return tuple(sorted(_TRANSITIONS[order.status], key=list(OrderStatus).index))


# --------------------------------------------------------------- BQ (de)serde
def to_bq_row(order: OrderRecord) -> dict:
    """JSON-load-ready row for szempont.orders (DDL 003; NUMERIC as strings)."""
    t = order_totals(order)
    p = order.payer
    return {
        "order_id": order.order_id,
        "legacy_order_id": order.legacy_order_id,
        "quote_id": order.quote_id,
        "catalog_version": order.catalog_version,
        "order_date": order.order_date,
        "person_id": order.person_id,
        "status": str(order.status),
        "lines": [{
            "line_type": l.line_type, "sku": l.sku, "name": l.name,
            "qty": l.qty, "unit_retail_net": str(l.unit_retail_net),
            "auto_added": l.auto_added, "removed": l.removed,
            "source": l.source,
        } for l in order.lines],
        "payer_type": p.payer_type,
        "payer_name": p.payer_name,
        "payer_member_name": p.payer_member_name,
        "payer_member_id": p.payer_member_id,
        "payer_billing_address": p.payer_billing_address,
        "vat_rate": str(order.vat_rate),
        "total_retail_net": str(t.total_retail_net),
        "total_retail_gross": str(t.total_retail_gross),
        "discount_net": str(order.discount_net),
        "discount_config_id": order.discount_config_id,
        "discount_approved_by": order.discount_approved_by,
        "lens_source": order.lens_source,
        "due_date": order.due_date,
        "channel": order.channel,
        "munkalap_gcs_uri": order.munkalap_gcs_uri,
        "tharanis_sorszam": order.tharanis_sorszam,
        "cancel_reason": order.cancel_reason,
        "revision": order.revision,
        "saved_at": order.saved_at or None,
        "created_by": order.created_by,
        "created_at": order.created_at,
    }


def from_bq_row(row: dict) -> OrderRecord:
    return OrderRecord(
        order_id=row["order_id"],
        quote_id=row["quote_id"],
        catalog_version=row["catalog_version"],
        order_date=str(row["order_date"]),
        status=OrderStatus(row["status"]),
        lines=tuple(QuoteLineRec(
            line_type=l["line_type"], sku=l["sku"], name=l["name"],
            qty=int(l["qty"]), unit_retail_net=Decimal(str(l["unit_retail_net"])),
            auto_added=bool(l["auto_added"]), removed=bool(l["removed"]),
            source=l.get("source"),
        ) for l in row["lines"]),
        vat_rate=Decimal(str(row["vat_rate"])),
        lens_source=row["lens_source"],
        due_date=str(row["due_date"]),
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
        discount_net=Decimal(str(row.get("discount_net") or "0")),
        discount_config_id=row.get("discount_config_id"),
        discount_approved_by=row.get("discount_approved_by"),
        legacy_order_id=row.get("legacy_order_id"),
        channel=row.get("channel") or "store-terez50",
        munkalap_gcs_uri=row.get("munkalap_gcs_uri"),
        tharanis_sorszam=row.get("tharanis_sorszam"),
        cancel_reason=row.get("cancel_reason"),
        revision=int(row.get("revision") or 0),
        saved_at=str(row.get("saved_at") or ""),
    )
