"""Szempont M5 — staff identity on a shared terminal (W3-2).

R6: the terminal's Google account passes IAP (perimeter); the acting HUMAN
is picked in-app and proves presence with a short PIN. current_operator()
reads the session operator everywhere. IAP identity is trusted ONLY via
the verified x-goog-iap-jwt-assertion JWT (auth/iap.py), never the plain
email header.

R7: role vocabulary extends the audited ClearVis set with Optikus and
Látszerész; gated-discount approvers are Üzletvezető + Cégvezető; order
cancel needs NO role (any staff, audited).
"""
from .staff import (APPROVER_ROLES, ROLES, SEED_STAFF, InMemoryStaffStore,  # noqa: F401
                    PinLocked, StaffError, StaffMember, hash_pin)
