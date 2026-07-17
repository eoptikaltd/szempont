"""M5 staff/PIN tests (W3-2) — R7 seed, hashing, lockout, roles."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from auth.staff import (APPROVER_ROLES, ROLES, SEED_STAFF, InMemoryStaffStore,
                        PinLocked, StaffError, hash_pin)


def clock(start_min=0):
    n = [start_min]
    def now():
        n[0] += 1
        return f"2026-07-18T10:{n[0]:02d}:00+00:00"
    return now


def test_r7_seed_roster_and_roles():
    s = InMemoryStaffStore()
    members = {m.operator_id: m for m in s.active_members()}
    assert len(members) == 8
    assert members["valner.szabolcs"].roles == ("Cégvezető",)
    assert members["benyo.krisztina"].roles == ("Optometrista",
                                                "Kontaktológus")
    assert members["szabo.greti"].roles == ("Látszerész",)
    # extended vocabulary present (R7)
    assert "Optikus" in ROLES and "Látszerész" in ROLES
    assert APPROVER_ROLES == {"Cégvezető", "Üzletvezető"}
    assert members["bozo.klaudia"].is_approver
    assert not members["varga.orsolya"].is_approver
    # seed ships without PINs (bootstrap)
    assert not s.any_approver_has_pin()


def test_pin_set_verify_and_format():
    s = InMemoryStaffStore()
    s.set_pin("bozo.klaudia", "4321", updated_by="valner.szabolcs")
    assert s.verify_pin("bozo.klaudia", "4321") is True
    assert s.verify_pin("bozo.klaudia", "0000") is False
    assert s.any_approver_has_pin()
    # revisioned change with provenance
    m = s.get("bozo.klaudia")
    assert m.revision == 1 and m.updated_by == "valner.szabolcs"
    # member without a PIN never verifies; unknown member never verifies
    assert s.verify_pin("varga.orsolya", "1234") is False
    assert s.verify_pin("senki.sincs", "1234") is False
    for bad in ("12", "12345678", "abcd", "12a4"):
        with pytest.raises(StaffError):
            s.set_pin("bozo.klaudia", bad, updated_by="x")
    # hash is salted: same PIN, different member -> different hash
    s.set_pin("valner.szabolcs", "4321", updated_by="x")
    a, b = s.get("bozo.klaudia"), s.get("valner.szabolcs")
    assert a.pin_hash != b.pin_hash
    assert hash_pin("4321", a.pin_salt) == a.pin_hash


def test_pin_lockout_after_five_misses():
    s = InMemoryStaffStore(now_fn=clock())
    s.set_pin("bozo.klaudia", "4321", updated_by="x")
    for _ in range(5):
        assert s.verify_pin("bozo.klaudia", "9999") is False
    with pytest.raises(PinLocked):           # locked even with the RIGHT pin
        s.verify_pin("bozo.klaudia", "4321")
    # a successful verify resets the counter after the lock expires
    s2 = InMemoryStaffStore(now_fn=clock())
    s2.set_pin("bozo.klaudia", "4321", updated_by="x")
    for _ in range(4):
        s2.verify_pin("bozo.klaudia", "9999")
    assert s2.verify_pin("bozo.klaudia", "4321") is True
    for _ in range(4):                        # counter restarted
        assert s2.verify_pin("bozo.klaudia", "9999") is False
    assert s2.verify_pin("bozo.klaudia", "4321") is True
    # setting a new PIN clears any lock
    s3 = InMemoryStaffStore(now_fn=clock())
    s3.set_pin("bozo.klaudia", "4321", updated_by="x")
    for _ in range(5):
        s3.verify_pin("bozo.klaudia", "9999")
    s3.set_pin("bozo.klaudia", "5678", updated_by="x")
    assert s3.verify_pin("bozo.klaudia", "5678") is True


def test_deactivated_member_cannot_verify_or_be_pinned():
    s = InMemoryStaffStore()
    s.set_pin("varga.orsolya", "1111", updated_by="x")
    s.set_active("varga.orsolya", False, updated_by="bozo.klaudia")
    assert s.verify_pin("varga.orsolya", "1111") is False
    assert all(m.operator_id != "varga.orsolya" for m in s.active_members())
    with pytest.raises(StaffError):
        s.set_pin("varga.orsolya", "2222", updated_by="x")


def test_bq_row_shape_matches_ddl_004():
    import re
    from pathlib import Path
    from auth.staff import to_bq_row
    s = InMemoryStaffStore()
    row = to_bq_row(s.get("bozo.klaudia"))
    ddl = (Path(__file__).resolve().parents[1] /
           "infra/ddl/004_w3_auth.sql").read_text()
    block = re.search(r"CREATE TABLE IF NOT EXISTS `szempont\.staff` \((.*?)\n\)",
                      ddl, re.S).group(1)
    cols = set(re.findall(
        r"^\s*([a-z_]+)\s+(?:STRING|BOOL|INT64|TIMESTAMP|ARRAY<STRING>)",
        block, re.M))
    assert set(row) == cols
