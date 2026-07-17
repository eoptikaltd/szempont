"""Szempont M5 — munkatársak, szerepkörök, PIN (R6/R7).

Design constraints:
  * PINs are SHORT (4–6 digits) — presence proof at a shared terminal, not
    a password. Security comes from IAP at the perimeter + PBKDF2 hashing
    + hard rate limiting here (5 misses → 15 minute lock, per member), and
    from every sensitive action being audited with the acting person.
  * Roles are Hungarian vocabulary verbatim (R7); one member may hold
    several (Benyó Krisztina: Optometrista + Kontaktológus).
  * Store is revisioned like quotes/orders (append-only; BQ reads QUALIFY
    latest) so role/PIN changes keep their history.
  * Bootstrap: the seed ships WITHOUT PINs. While NO approver-role member
    has a PIN yet, PINs may be set freely (deploy-time setup); once any
    approver has one, changing PINs requires an approver's PIN.
"""

from __future__ import annotations

import dataclasses
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

ROLES = ("Cégvezető", "Üzletvezető", "Optometrista", "Kontaktológus",
         "Ügyfélszolgálatos", "Bolti eladó", "Optikus", "Látszerész")

# R7: gated-discount approvers.
APPROVER_ROLES = frozenset({"Cégvezető", "Üzletvezető"})

# R7 seed, verbatim.
SEED_STAFF: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("valner.szabolcs", "Valner Szabolcs", ("Cégvezető",)),
    ("bozo.klaudia", "Bozó Klaudia", ("Üzletvezető",)),
    ("benyo.krisztina", "Benyó Krisztina", ("Optometrista", "Kontaktológus")),
    ("tall.krisztina", "Táll Krisztina", ("Optometrista", "Kontaktológus")),
    ("vithalm.zsofia", "Vithalm Zsófia", ("Optikus",)),
    ("almadi-bartha.mariann", "Almádi-Bartha Mariann", ("Látszerész",)),
    ("szabo.greti", "Szabó Gréti", ("Látszerész",)),
    ("varga.orsolya", "Varga Orsolya", ("Bolti eladó",)),
)

_PBKDF2_ITERS = 200_000
_LOCK_AFTER = 5           # failed attempts...
_LOCK_MINUTES = 15        # ...lock the member's PIN for this long


class StaffError(Exception):
    """Unknown member, bad PIN format, missing role, invalid change."""


class PinLocked(StaffError):
    """Too many failed attempts — locked until the given time."""

    def __init__(self, until_iso: str):
        super().__init__(f"PIN zárolva eddig: {until_iso[:16].replace('T', ' ')}")
        self.until_iso = until_iso


@dataclass(frozen=True, slots=True)
class StaffMember:
    """One revision of one member (= one szempont.staff row)."""
    operator_id: str                  # 'bozo.klaudia' — the audit actor id
    display_name: str
    roles: tuple[str, ...]
    pin_hash: str | None = None       # hex PBKDF2-SHA256; None = no PIN yet
    pin_salt: str | None = None
    active: bool = True
    revision: int = 0
    updated_at: str = ""
    updated_by: str = ""

    @property
    def has_pin(self) -> bool:
        return bool(self.pin_hash and self.pin_salt)

    @property
    def is_approver(self) -> bool:
        return bool(APPROVER_ROLES & set(self.roles))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_pin(pin: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"),
                               bytes.fromhex(salt_hex),
                               _PBKDF2_ITERS).hex()


def validate_pin_format(pin: str) -> None:
    if not (pin.isdigit() and 4 <= len(pin) <= 6):
        raise StaffError("a PIN 4–6 számjegy")


class InMemoryStaffStore:
    """Dev/test store, R7-seeded; BQStaffStore mirrors the API in staging."""

    def __init__(self, now_fn=_utc_now, seed=SEED_STAFF):
        self._revs: dict[str, list[StaffMember]] = {}
        self._fails: dict[str, list[str]] = {}     # op -> fail timestamps
        self._locked_until: dict[str, str] = {}
        self._now = now_fn
        for op, name, roles in seed:
            for r in roles:
                if r not in ROLES:
                    raise StaffError(f"unknown role {r!r} in seed")
            self._revs[op] = [StaffMember(op, name, tuple(roles),
                                          updated_at=self._now(),
                                          updated_by="seed")]

    # ------------------------------------------------------------------ reads
    def get(self, operator_id: str) -> StaffMember | None:
        revs = self._revs.get(operator_id)
        return revs[-1] if revs else None

    def active_members(self) -> tuple[StaffMember, ...]:
        return tuple(revs[-1] for revs in self._revs.values()
                     if revs and revs[-1].active)

    def display_name(self, operator_id: str) -> str | None:
        m = self.get(operator_id)
        return m.display_name if m else None

    def any_approver_has_pin(self) -> bool:
        return any(m.has_pin and m.is_approver for m in self.active_members())

    # ------------------------------------------------------------------- PIN
    def set_pin(self, operator_id: str, pin: str, *, updated_by: str) -> None:
        m = self.get(operator_id)
        if m is None or not m.active:
            raise StaffError(f"ismeretlen munkatárs: {operator_id}")
        validate_pin_format(pin)
        salt = secrets.token_hex(16)
        self._append(m, pin_hash=hash_pin(pin, salt), pin_salt=salt,
                     updated_by=updated_by)
        self._fails.pop(operator_id, None)
        self._locked_until.pop(operator_id, None)

    def verify_pin(self, operator_id: str, pin: str) -> bool:
        """True on match. Rate-limited: 5 misses lock for 15 minutes
        (raises PinLocked while locked). Members without a PIN never match."""
        m = self.get(operator_id)
        if m is None or not m.active or not m.has_pin:
            return False
        now = self._now()
        locked = self._locked_until.get(operator_id)
        if locked and now < locked:
            raise PinLocked(locked)
        if secrets.compare_digest(hash_pin(pin, m.pin_salt), m.pin_hash):
            self._fails.pop(operator_id, None)
            self._locked_until.pop(operator_id, None)
            return True
        fails = self._fails.setdefault(operator_id, [])
        fails.append(now)
        if len(fails) >= _LOCK_AFTER:
            from datetime import datetime as _dt, timedelta
            base = _dt.fromisoformat(now)
            self._locked_until[operator_id] = (
                base + timedelta(minutes=_LOCK_MINUTES)).isoformat()
            self._fails.pop(operator_id, None)
        return False

    # ------------------------------------------------------------------ edits
    def set_active(self, operator_id: str, active: bool, *,
                   updated_by: str) -> None:
        m = self.get(operator_id)
        if m is None:
            raise StaffError(f"ismeretlen munkatárs: {operator_id}")
        self._append(m, active=active, updated_by=updated_by)

    def _append(self, m: StaffMember, **changes) -> None:
        rev = dataclasses.replace(m, **changes,
                                  revision=m.revision + 1,
                                  updated_at=self._now())
        self._revs[m.operator_id].append(rev)


def to_bq_row(m: StaffMember) -> dict:
    return {"operator_id": m.operator_id, "display_name": m.display_name,
            "roles": list(m.roles), "pin_hash": m.pin_hash,
            "pin_salt": m.pin_salt, "active": m.active,
            "revision": m.revision, "updated_at": m.updated_at or None,
            "updated_by": m.updated_by}


class BQStaffStore(InMemoryStaffStore):  # pragma: no cover — staging only
    """szempont.staff (DDL 004) with the in-memory semantics: loads the
    QUALIFY-latest revisions at construction, appends on change. PIN
    attempt counters stay process-local (single terminal; a restart
    resetting the lock window is acceptable and documented)."""

    TABLE = "szempont.staff"

    def __init__(self, client, now_fn=_utc_now):
        super().__init__(now_fn=now_fn, seed=())
        self.client = client
        from google.cloud import bigquery
        job = client.query(
            f"SELECT * FROM `{self.TABLE}` QUALIFY ROW_NUMBER() OVER ("
            "PARTITION BY operator_id ORDER BY IFNULL(revision,0) DESC) = 1",
            job_config=bigquery.QueryJobConfig(labels={"tool": "szempont"}))
        for r in job.result():
            d = dict(r)
            self._revs[d["operator_id"]] = [StaffMember(
                operator_id=d["operator_id"],
                display_name=d["display_name"],
                roles=tuple(d["roles"]), pin_hash=d.get("pin_hash"),
                pin_salt=d.get("pin_salt"), active=bool(d["active"]),
                revision=int(d.get("revision") or 0),
                updated_at=str(d.get("updated_at") or ""),
                updated_by=d.get("updated_by") or "")]

    def _append(self, m: StaffMember, **changes) -> None:
        super()._append(m, **changes)
        from google.cloud import bigquery
        rev = self._revs[m.operator_id][-1]
        job = self.client.load_table_from_json(
            [to_bq_row(rev)], self.TABLE,
            job_config=bigquery.LoadJobConfig(
                labels={"tool": "szempont"},
                write_disposition="WRITE_APPEND"))
        job.result()
