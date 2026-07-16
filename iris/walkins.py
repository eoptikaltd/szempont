"""M3 — Z1 walk-in fallback (write side of the IRIS contract).

Szempont NEVER mints person IDs (hard rule 4). An unresolved walk-in gets a
`Z1-<uuid>` token — the prefix makes non-person status unmistakable — in the
szempont-owned table szempont.walkin_persons. IRIS ingests nightly,
resolves-or-mints, and writes szempont.walkin_resolutions
(z1_token -> person_id). Szempont ATTRIBUTES THROUGH THE MAPPING: quotes and
orders created under a Z1 token keep their original person_id forever; the
join re-attributes them (attributed_person_id), rows are never rewritten.

Unresolved > 7 days is IRIS's merge_review_queue problem (contract SLO),
not Szempont's.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

Z1_PREFIX = "Z1-"


def is_z1(token_or_person_id: str | None) -> bool:
    return bool(token_or_person_id
                and token_or_person_id.startswith(Z1_PREFIX))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_token() -> str:
    return Z1_PREFIX + str(uuid.uuid4())


@dataclass(frozen=True, slots=True)
class WalkinPerson:
    """One szempont.walkin_persons row (DDL 001 §walkin)."""
    z1_token: str
    display_name: str
    phone_raw: str | None
    email_raw: str | None
    birth_date: str | None          # ISO date
    ep_member: bool                 # D1 capture at desk
    ep_fund_name: str | None
    ep_member_id: str | None
    gdpr_signed: bool
    dm_ok: bool
    created_by: str
    created_at: str                 # ISO timestamp


def new_walkin(*, display_name: str, created_by: str,
               phone_raw: str | None = None, email_raw: str | None = None,
               birth_date: str | None = None, ep_member: bool = False,
               ep_fund_name: str | None = None, ep_member_id: str | None = None,
               gdpr_signed: bool = False, dm_ok: bool = False,
               token_fn=_new_token, now_fn=_utc_now) -> WalkinPerson:
    name = display_name.strip()
    if not name:
        raise ValueError("walk-in needs at least a display_name")
    return WalkinPerson(
        z1_token=token_fn(), display_name=name, phone_raw=phone_raw or None,
        email_raw=email_raw or None, birth_date=birth_date or None,
        ep_member=ep_member, ep_fund_name=ep_fund_name or None,
        ep_member_id=ep_member_id or None, gdpr_signed=gdpr_signed,
        dm_ok=dm_ok, created_by=created_by, created_at=now_fn())


def walkin_to_bq_row(w: WalkinPerson) -> dict:
    return {
        "z1_token": w.z1_token, "display_name": w.display_name,
        "phone_raw": w.phone_raw, "email_raw": w.email_raw,
        "birth_date": w.birth_date,
        "ep_member": w.ep_member, "ep_fund_name": w.ep_fund_name,
        "ep_member_id": w.ep_member_id,
        "gdpr_signed": w.gdpr_signed, "dm_ok": w.dm_ok,
        "created_by": w.created_by, "created_at": w.created_at,
    }


def attributed_person_id(person_id: str | None, store) -> str | None:
    """Re-attribution join: a Z1 token whose resolution has landed reads as
    the canonical person_id; everything else passes through unchanged. The
    stored row is never rewritten — this is applied at read time."""
    if not is_z1(person_id):
        return person_id
    resolved = store.resolve(person_id)
    return resolved or person_id


class InMemoryWalkinStore:
    """Dev/UI/test store. Resolutions are written by IRIS in production;
    the fake exposes add_resolution() so tests can play IRIS's part."""

    def __init__(self):
        self._walkins: dict[str, WalkinPerson] = {}
        self._resolutions: dict[str, str] = {}   # z1_token -> person_id

    def save(self, w: WalkinPerson) -> WalkinPerson:
        if w.z1_token in self._walkins:
            raise ValueError(f"walk-in {w.z1_token} already exists "
                             "(rows are never rewritten)")
        self._walkins[w.z1_token] = w
        return w

    def get(self, z1_token: str) -> WalkinPerson | None:
        return self._walkins.get(z1_token)

    def resolve(self, z1_token: str) -> str | None:
        return self._resolutions.get(z1_token)

    def add_resolution(self, z1_token: str, person_id: str) -> None:
        """Test/IRIS-side helper — Szempont itself never calls this."""
        self._resolutions[z1_token] = person_id


class BQWalkinStore:  # pragma: no cover — staging, real BQ
    """walkin_persons is append-only via batch load (same rationale as the
    quote store); resolutions are READ-ONLY here — IRIS writes them."""

    WALKINS = "szempont.walkin_persons"
    RESOLUTIONS = "szempont.walkin_resolutions"

    def __init__(self, client):
        self.client = client

    def save(self, w: WalkinPerson) -> WalkinPerson:
        from google.cloud import bigquery
        if self.get(w.z1_token) is not None:   # F-W2-07: never rewrite/dupe
            raise ValueError(f"walk-in {w.z1_token} already exists")
        job = self.client.load_table_from_json(
            [walkin_to_bq_row(w)], self.WALKINS,
            job_config=bigquery.LoadJobConfig(
                labels={"tool": "szempont"},
                write_disposition="WRITE_APPEND"))
        job.result()
        if job.errors:
            raise RuntimeError(f"BQ load errors: {job.errors[:5]}")
        return w

    def get(self, z1_token: str) -> WalkinPerson | None:
        from google.cloud import bigquery
        sql = f"SELECT * FROM `{self.WALKINS}` WHERE z1_token = @t"
        job = self.client.query(sql, job_config=bigquery.QueryJobConfig(
            labels={"tool": "szempont"},
            query_parameters=[
                bigquery.ScalarQueryParameter("t", "STRING", z1_token)]))
        rows = list(job.result())
        if not rows:
            return None
        r = rows[0]
        return WalkinPerson(
            z1_token=r["z1_token"], display_name=r["display_name"],
            phone_raw=r["phone_raw"], email_raw=r["email_raw"],
            birth_date=str(r["birth_date"]) if r["birth_date"] else None,
            ep_member=bool(r["ep_member"]), ep_fund_name=r["ep_fund_name"],
            ep_member_id=r["ep_member_id"],
            gdpr_signed=bool(r["gdpr_signed"]), dm_ok=bool(r["dm_ok"]),
            created_by=r["created_by"], created_at=str(r["created_at"]))

    def resolve(self, z1_token: str) -> str | None:
        from google.cloud import bigquery
        sql = f"""
        SELECT person_id FROM `{self.RESOLUTIONS}`
        WHERE z1_token = @t
        QUALIFY ROW_NUMBER() OVER (ORDER BY resolved_at DESC) = 1
        """
        job = self.client.query(sql, job_config=bigquery.QueryJobConfig(
            labels={"tool": "szempont"},
            query_parameters=[
                bigquery.ScalarQueryParameter("t", "STRING", z1_token)]))
        rows = list(job.result())
        return rows[0]["person_id"] if rows else None
