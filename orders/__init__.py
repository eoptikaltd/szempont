"""Szempont M4 — store orders (W3-1).

Order records mint SZP- ids (R4); ClearVisio-migrated orders keep their
legacy SO- id in legacy_order_id (R18). Orders flow Szempont→Tharanis via
the SOAP adapter in vendors/tharanis.py — DRY-RUN ONLY until F-W3-01 gains
a "berak verified" follow-up (R1); the first live write is a tripwire.
"""
from .records import (OrderError, OrderRecord, OrderStatus, STATUS_HU,  # noqa: F401
                      LENS_SOURCES, build_order_from_quote, cancel_order,
                      order_totals, transition_order)
from .ids import format_order_id, next_order_id                         # noqa: F401
from .store import (InMemoryOrderStore, OrderEvent,                     # noqa: F401
                    order_cancel_audit_event)
from .promotions import (InMemoryPromotionRegistry, daily_digest,       # noqa: F401
                         register_first_sale)
