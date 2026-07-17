"""Tharanis ERP adapter (hard rule 2) — Szempont→Tharanis store orders (R1).

DRY-RUN ONLY. F-W3-01 verified that the existing connector
(eoptikaltd/erp-connector) implements only `leker` (read); the `berak`
write payloads for bejovo_megrendeles / cikk are documented to exist but
their schemas are UNVERIFIED and the per-forrás/cél API permissions are
not granted. Until the findings log gains a "berak verified" follow-up:

  * build_berak_order_xml renders the CANDIDATE payload (field names taken
    from the connector's live-proven READ schema for bejovo_megrendeles —
    strong hypothesis, not doc-verified);
  * TharanisOrderSink.send() in dry_run mode returns the XML for the
    eseménynapló and NEVER opens a connection;
  * live mode raises TharanisWriteBlocked unconditionally — flipping it on
    is a separate flagged commit gated by the doc + permission grant + the
    live-write tripwire.

Proven transport conventions mirrored from the connector (F-W3-01): CDATA-
wrapped inner XML, entity-escaped values (the WAF rejects CDATA-wrapped
operators), <hiba> anything-but-"0" error semantics, éééé.hh.nn dates.
Credentials (when live ever comes): Secret Manager tharanis-ugyfelkod /
tharanis-cegkod / tharanis-apikulcs — never in the repo.
"""

from __future__ import annotations

import datetime as dt
import os
from xml.sax.saxutils import escape

from orders.records import OrderRecord, order_totals


class TharanisWriteBlocked(RuntimeError):
    """Live berak is blocked pending F-W3-01 follow-up (doc + permission +
    tripwire). Dry-run remains available."""


def fmt_date_dot(iso_date: str) -> str:
    """ISO YYYY-MM-DD -> Tharanis éééé.hh.nn."""
    return dt.date.fromisoformat(iso_date).strftime("%Y.%m.%d")


def _el(tag: str, value: str | None) -> str:
    return f"<{tag}>{escape(value)}</{tag}>" if value else f"<{tag}/>"


def build_berak_order_xml(order: OrderRecord, *,
                          customer_name: str = "",
                          customer_email: str = "",
                          customer_phone: str = "",
                          raktar: str = "1") -> str:
    """CANDIDATE <berak> payload for forrascel=bejovo_megrendeles.

    Field names follow the connector's live-verified READ schema (fej/
    tetelek) — the write schema is UNVERIFIED against the Tharanis doc
    (F-W3-01). This XML is a dry-run artifact for the eseménynapló and for
    the doc-verification conversation; it is never POSTed by this module.
    """
    t = order_totals(order)
    lines: list[str] = ['<?xml version="1.0" encoding="UTF-8"?>', "<berak>",
                        "  <elem>", "    <fej>"]
    fej = [
        ("hivszam", order.order_id),          # Szempont SZP- id as reference
        ("kelt", fmt_date_dot(order.order_date)),
        ("kert_telj", fmt_date_dot(order.due_date)),
        ("valuta", "HUF"),
        ("fiz_mod", ""),                      # M8 wires payment (W4)
        ("szall_mod", "szemelyes_atvetel"),
        ("uzletag", "bolt"),
        ("shop", order.channel),
        ("email", customer_email),
        ("telefon", customer_phone),
        ("szla_nev", customer_name),
        ("megjegyzes", f"Szempont megrendelés {order.order_id}"
                       + (f" (quote {order.quote_id})" if order.quote_id
                          else "")),
        ("netto", str(t.total_retail_net)),
        ("brutto", str(t.total_retail_gross)),
    ]
    lines += [f"      {_el(tag, val)}" for tag, val in fej]
    lines += ["    </fej>", "    <tetelek>"]
    for line in order.lines:
        if line.removed or line.line_type == "discount":
            continue                          # discounts ride in the totals
        lines += ["      <tetel>",
                  f"        {_el('cikksz', line.sku or '')}",
                  f"        {_el('raktar', raktar)}",
                  f"        <menny>{line.qty}</menny>",
                  f"        <netto_ar>{line.unit_retail_net}</netto_ar>",
                  f"        {_el('tmegjegy', line.name)}",
                  "      </tetel>"]
    lines += ["    </tetelek>", "  </elem>", "</berak>"]
    return "\n".join(lines)


class TharanisOrderSink:
    """Order write adapter. Modes (SZEMPONT_THARANIS_WRITE env):
      off      — default; send() refuses politely.
      dry_run  — send() returns {'mode','xml','sent':False}; no network.
      live     — HARD-BLOCKED (TharanisWriteBlocked) until the F-W3-01
                 follow-up lands; enabling it is a separate flagged commit
                 AND a tripwire stop.
    """

    MODES = ("off", "dry_run", "live")

    def __init__(self, mode: str | None = None):
        self.mode = (mode if mode is not None
                     else os.environ.get("SZEMPONT_THARANIS_WRITE", "off"))
        if self.mode not in self.MODES:
            raise ValueError(f"SZEMPONT_THARANIS_WRITE must be one of "
                             f"{self.MODES}, got {self.mode!r}")

    def send(self, order: OrderRecord, **customer_fields) -> dict:
        if self.mode == "off":
            raise TharanisWriteBlocked(
                "Tharanis order write is off (SZEMPONT_THARANIS_WRITE=off)")
        xml = build_berak_order_xml(order, **customer_fields)
        if self.mode == "live":
            raise TharanisWriteBlocked(
                "LIVE berak blocked: unverified write schema + missing "
                "permission grant (F-W3-01); first live write is a tripwire")
        return {"mode": self.mode, "xml": xml, "sent": False}
