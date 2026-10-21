import sqlite3
import pytest
from shield.src.orders import OrderManager

def mk(tmp_path):
    om = OrderManager(str(tmp_path / "t.db"), model_version="v9", rule_version="r1")
    d = {"unit": 1, "cycle": 100, "severity": "HIGH", "status": "AUTO_CREATED", "exception_reason": None, "p10": 30, "p50": 45, "p90": 60, "due_in_cycles": 10, "action": "a"}
    om.process_agent_decision(d); om.process_agent_decision({**d, "cycle": 105, "severity": "CRITICAL", "due_in_cycles": 0}); om.conn.commit()
    return om

def test_chain_valid_then_tamper_detected(tmp_path):
    om = mk(tmp_path); ok, msg = om.verify_audit_chain(); assert ok and "100% intact" in msg
    om.conn.execute("UPDATE audit_log SET details='{\"tampered\": true}' WHERE entry_id=1"); om.conn.commit()
    ok, msg = om.verify_audit_chain(); assert not ok and "mismatch" in msg

def test_deleted_row_detected(tmp_path):
    om = mk(tmp_path); om.conn.execute("DELETE FROM audit_log WHERE entry_id=1"); om.conn.commit()
    assert not om.verify_audit_chain()[0]

def test_provenance_in_every_audit_row(tmp_path):
    om = mk(tmp_path)
    for (d,) in om.conn.execute("SELECT details FROM audit_log"):
        assert '"model_version": "v9"' in d and '"rule_version": "r1"' in d

def test_production_refuses_published_demo_key(tmp_path, monkeypatch):
    monkeypatch.setenv("AEROSHIELD_ENV", "production")
    monkeypatch.delenv("AEROSHIELD_HMAC_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OrderManager(str(tmp_path / "prod.db"))
    monkeypatch.setenv("AEROSHIELD_HMAC_KEY", "aeroshield-v3-secret-key")
    with pytest.raises(RuntimeError):
        OrderManager(str(tmp_path / "prod2.db"))


def test_keyed_hmac_tamper_forgery_resistance(tmp_path):
    """An attacker with write access to SQLite cannot forge hashes without the secret HMAC key."""
    om = OrderManager(str(tmp_path / "forgery.db"), model_version="v9", rule_version="r1", hmac_key="correct-key")
    d = {"unit": 1, "cycle": 100, "severity": "HIGH", "status": "AUTO_CREATED", "exception_reason": None, "p10": 30, "p50": 45, "p90": 60, "due_in_cycles": 10, "action": "a"}
    om.process_agent_decision(d)
    om.conn.commit()
    ok, msg = om.verify_audit_chain()
    assert ok and "100% intact" in msg

    # Attacker attempts to verify with a different HMAC key
    attacker_om = OrderManager(str(tmp_path / "forgery.db"), model_version="v9", rule_version="r1", hmac_key="attacker-key")
    ok_att, msg_att = attacker_om.verify_audit_chain()
    assert not ok_att and "recomputed hash mismatch" in msg_att
