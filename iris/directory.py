"""M3 — customer read side over the IRIS contract (contracts/iris_contract.md,
APPROVED 2026-07-16).

IRIS owns identity (hard rule 4). Szempont reads exactly two views and
nothing else from crm_*:

  crm_core.v_person_search   — normalized search keys (A-grade, in-zone only)
  crm_core.v_person_lookup_a — card columns by person_id

The interface columns are FROZEN; the views may not be published yet, so the
live client is a thin adapter whose view names come from env — publishing the
views is a config change, not a code change. FixturePersonDirectory backs
dev/tests and reproduces the contract's population + search semantics
(search_key prefix/equality) from card data, using the same normalizers.

No Rx/health data flows through here (hard rule 5); ep_member_hint is a
membership hint (D1 payer tie-in), not health data.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol

# Contract defaults; staging can repoint without a code change.
DEFAULT_SEARCH_VIEW = "crm_core.v_person_search"
DEFAULT_LOOKUP_VIEW = "crm_core.v_person_lookup_a"

_PAYROLL_PREFIX = re.compile(r"^\d+\s+")   # hard rule 10: "123 Kovács Éva"
_NON_DIGITS = re.compile(r"\D")
_PHONEISH = re.compile(r"^[\d+\s\-/()]+$")


@dataclass(frozen=True, slots=True)
class PersonCard:
    """One crm_core.v_person_lookup_a row (frozen contract columns)."""
    person_id: str
    display_name: str
    phone_e164: str | None
    email: str | None
    birth_date: str | None          # ISO date
    ep_member_hint: bool
    dm_blocked: bool
    gdpr_signed: bool
    last_activity_at: str | None    # ISO timestamp


def strip_accents(s: str) -> str:
    decomposed = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_name(raw: str) -> str:
    """Contract name key: payroll prefix stripped, accent-stripped,
    lowercase, single-spaced (hard rule 10)."""
    s = _PAYROLL_PREFIX.sub("", raw.strip())
    return " ".join(strip_accents(s).lower().split())


def normalize_query(raw: str) -> tuple[str, str]:
    """Free-text desk input -> (id_kind, search_key) exactly as
    v_person_search stores keys: name | phone | email."""
    s = raw.strip()
    if "@" in s:
        return "email", s.lower()
    if _PHONEISH.fullmatch(s) and len(_NON_DIGITS.sub("", s)) >= 6:
        return "phone", _NON_DIGITS.sub("", s)
    return "name", normalize_name(s)


class PersonDirectory(Protocol):
    def search(self, raw_query: str) -> list[PersonCard]: ...

    def lookup(self, person_id: str) -> PersonCard | None: ...


class FixturePersonDirectory:
    """Contract-faithful fake: derives v_person_search rows from the cards
    with the same normalizers IRIS specifies, then answers searches by
    prefix/equality on the derived keys. Cards ARE the A-grade in-zone
    population by construction."""

    def __init__(self, cards: tuple[PersonCard, ...] = ()):
        self._cards = {c.person_id: c for c in (cards or DEMO_PERSONS)}
        self._keys: list[tuple[str, str, str]] = []   # (id_kind, key, pid)
        for c in self._cards.values():
            self._keys.append(("name", normalize_name(c.display_name),
                               c.person_id))
            if c.phone_e164:
                self._keys.append(("phone", _NON_DIGITS.sub("", c.phone_e164),
                                   c.person_id))
            if c.email:
                self._keys.append(("email", c.email.lower(), c.person_id))

    def search(self, raw_query: str) -> list[PersonCard]:
        kind, key = normalize_query(raw_query)
        if not key:
            return []
        pids = {pid for k, sk, pid in self._keys
                if k == kind and sk.startswith(key)}
        return sorted((self._cards[p] for p in pids),
                      key=lambda c: (c.display_name, c.person_id))

    def lookup(self, person_id: str) -> PersonCard | None:
        return self._cards.get(person_id)


DEMO_PERSONS = (
    PersonCard("P-1001", "Kovács Éva", "+36301234567",
               "kovacs.eva@example.com", "1985-04-12",
               ep_member_hint=True, dm_blocked=False, gdpr_signed=True,
               last_activity_at="2026-06-02T09:15:00+00:00"),
    PersonCard("P-1002", "Nagy Péter", "+36209876543",
               "nagy.peter@example.com", "1978-11-30",
               ep_member_hint=False, dm_blocked=True, gdpr_signed=True,
               last_activity_at="2025-12-19T14:40:00+00:00"),
    PersonCard("P-1003", "Szabó Ágnes", "+36705551122", None, "1992-02-07",
               ep_member_hint=False, dm_blocked=False, gdpr_signed=False,
               last_activity_at=None),
)


class BQPersonDirectory:  # pragma: no cover — needs the published IRIS views
    """Thin read-only adapter over the two contract views. View names come
    from env (IRIS_SEARCH_VIEW / IRIS_LOOKUP_VIEW) with contract defaults."""

    def __init__(self, client, search_view: str = DEFAULT_SEARCH_VIEW,
                 lookup_view: str = DEFAULT_LOOKUP_VIEW):
        self.client = client
        self.search_view = search_view
        self.lookup_view = lookup_view

    def _card(self, r) -> PersonCard:
        return PersonCard(
            person_id=r["person_id"], display_name=r["display_name"],
            phone_e164=r["phone_e164"], email=r["email"],
            birth_date=str(r["birth_date"]) if r["birth_date"] else None,
            ep_member_hint=bool(r["ep_member_hint"]),
            dm_blocked=bool(r["dm_blocked"]),
            gdpr_signed=bool(r["gdpr_signed"]),
            last_activity_at=(str(r["last_activity_at"])
                              if r["last_activity_at"] else None),
        )

    def search(self, raw_query: str) -> list[PersonCard]:
        from google.cloud import bigquery
        kind, key = normalize_query(raw_query)
        if not key:
            return []
        sql = f"""
        SELECT l.* FROM `{self.lookup_view}` l
        JOIN (
          SELECT DISTINCT person_id FROM `{self.search_view}`
          WHERE id_kind = @kind AND STARTS_WITH(search_key, @key)
        ) USING (person_id)
        ORDER BY l.display_name, l.person_id
        LIMIT 25
        """
        job = self.client.query(sql, job_config=bigquery.QueryJobConfig(
            labels={"tool": "szempont"},
            query_parameters=[
                bigquery.ScalarQueryParameter("kind", "STRING", kind),
                bigquery.ScalarQueryParameter("key", "STRING", key),
            ]))
        return [self._card(r) for r in job.result()]

    def lookup(self, person_id: str) -> PersonCard | None:
        from google.cloud import bigquery
        sql = f"SELECT * FROM `{self.lookup_view}` WHERE person_id = @pid"
        job = self.client.query(sql, job_config=bigquery.QueryJobConfig(
            labels={"tool": "szempont"},
            query_parameters=[
                bigquery.ScalarQueryParameter("pid", "STRING", person_id)]))
        rows = list(job.result())
        return self._card(rows[0]) if rows else None
