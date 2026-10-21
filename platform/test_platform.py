"""Automated Test Suite for Tata Elxsi Predictive Fleet Maintenance Platform Backend
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "platform"))

try:
    from platform.backend.main import app
except ImportError:
    from backend.main import app

client = TestClient(app)

def test_dashboard_endpoint():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Autonomous Predictive Fleet Maintenance" in response.text

def test_api_subsets():
    response = client.get("/api/subsets")
    assert response.status_code == 200
    data = response.json()
    assert "subsets" in data
    assert len(data["subsets"]) > 0

def test_api_fleet_readiness():
    response = client.get("/api/fleet/readiness?subset=FD001")
    assert response.status_code == 200
    data = response.json()
    assert data["total_engines"] > 0
    assert "health_rate_pct" in data
    assert "status_counts" in data
    assert "CRITICAL" in data["status_counts"]
    assert "NORMAL" in data["status_counts"]

def test_api_fleet_matrix():
    response = client.get("/api/fleet/matrix?subset=FD001")
    assert response.status_code == 200
    data = response.json()
    assert "engines" in data
    assert len(data["engines"]) > 0
    first = data["engines"][0]
    assert "unit" in first
    assert "p50_rul" in first
    assert "p10_rul" in first
    assert "p90_rul" in first
    assert "status" in first

def test_api_engine_drilldown():
    response = client.get("/api/engine/1?subset=FD001")
    assert response.status_code == 200
    data = response.json()
    assert data["unit"] == 1
    assert "timeline" in data
    tl = data["timeline"]
    assert len(tl["cycles"]) > 0
    assert len(tl["p50"]) == len(tl["cycles"])
    assert "ratios" in tl
    assert "fan_core_s8_s9" in tl["ratios"]

def test_api_work_orders():
    response = client.get("/api/work-orders?subset=FD001")
    assert response.status_code == 200
    data = response.json()
    assert "work_orders" in data

def test_api_exceptions():
    response = client.get("/api/exceptions?subset=FD001")
    assert response.status_code == 200
    data = response.json()
    assert "exceptions" in data

def test_api_audit_log_and_verify():
    response = client.get("/api/audit-log?subset=FD001")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "verified" in data
    assert data["verified"] is True

    # Test live verification endpoint
    v_res = client.get("/api/audit-verify?subset=FD001")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["verified"] is True
    assert "100% intact" in v_data["message"]

def test_api_mlops():
    response = client.get("/api/mlops?subset=FD001")
    assert response.status_code == 200
    data = response.json()
    assert "thresholds" in data
    assert data["thresholds"]["psi_limit"] == 0.20
    assert data["thresholds"]["coverage_target"] == 0.80

PRIVATE_TEST_KEY = "local-test-key-not-the-published-one"


def test_published_dev_key_cannot_dispatch(monkeypatch):
    monkeypatch.setenv("AEROSHIELD_API_KEY", "aeroshield-dev-key")
    res = client.post(
        "/api/work-orders/dispatch",
        json={
            "subset": "FD001",
            "order_id": "WO-DOES-NOT-NEED-TO-EXIST",
            "new_status": "DISPATCHED",
        },
        headers={"X-API-Key": "aeroshield-dev-key"},
    )
    assert res.status_code == 401


def test_api_dispatch_work_order(monkeypatch):
    monkeypatch.setenv("AEROSHIELD_API_KEY", PRIVATE_TEST_KEY)
    # Fetch an order from work_orders
    wo_res = client.get("/api/work-orders?subset=FD001")
    orders = wo_res.json()["work_orders"]
    if orders:
        first_order = orders[0]
        oid = first_order["order_id"]

        # 1. Unauthenticated request must be rejected (401 Unauthorized)
        res_unauth = client.post("/api/work-orders/dispatch", json={
            "subset": "FD001",
            "order_id": oid,
            "new_status": "DISPATCHED",
            "operator": "Fleet Maintenance Controller"
        })
        assert res_unauth.status_code == 401, "Write endpoint must reject unauthenticated requests"

        # 2. Authenticated request with valid API key succeeds
        res = client.post(
            "/api/work-orders/dispatch",
            json={
                "subset": "FD001",
                "order_id": oid,
                "new_status": "DISPATCHED",
                "operator": "Fleet Maintenance Controller"
            },
            headers={"X-API-Key": PRIVATE_TEST_KEY}
        )
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["status"] == "DISPATCHED"

        # Verify audit chain remains cryptographically valid after dispatch
        v_res = client.get("/api/audit-verify?subset=FD001")
        assert v_res.status_code == 200
        assert v_res.json()["verified"] is True


def test_api_retrain_trigger_security_and_execution(monkeypatch):
    monkeypatch.setenv("AEROSHIELD_API_KEY", PRIVATE_TEST_KEY)
    # 1. Unauthenticated request must be rejected (401)
    res_unauth = client.post("/api/retrain/trigger", json={"subset": "FD001"})
    assert res_unauth.status_code == 401

    # 2. Authenticated request verifies parameter forwarding to retrain_demo.py
    import subprocess
    captured_args = []
    class MockCompletedProcess:
        returncode = 0
        stdout = "[demo] scenario 'strong' completed successfully. Gate passed."
        stderr = ""

    def mock_run(cmd, **kwargs):
        captured_args.append(cmd)
        return MockCompletedProcess()

    monkeypatch.setattr(subprocess, "run", mock_run)

    res = client.post(
        "/api/retrain/trigger",
        json={"subset": "FD001", "scenario": "strong"},
        headers={"X-API-Key": PRIVATE_TEST_KEY}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Gate passed" in data["stdout"]
    assert data["subset"] == "FD001"
    assert len(captured_args) == 1
    assert "--subset" in captured_args[0]
    assert "FD001" in captured_args[0]
    assert "--scenario" in captured_args[0]
    assert "strong" in captured_args[0]

def test_legacy_endpoints_decommissioned():
    """Confirms all legacy external endpoints are excised (404 Not Found)."""
    assert client.get("/api/voice/status").status_code == 404
    assert client.post("/api/voice/synthesize").status_code == 404
    assert client.post("/api/voice/copilot").status_code == 404





def test_api_predict_live_inference():
    """Tests end-to-end live raw telemetry ingestion, dynamic ratios, and non-LLM triage evaluation."""
    payload = {
        "subset": "FD001",
        "unit": 99,
        "cycle": 140,
        "op1": 0.001,
        "op2": 0.0002,
        "op3": 100.0,
        "sensors": {
            "s2": 642.5,
            "s3": 1595.0,
            "s4": 1410.0,
            "s7": 552.0,
            "s8": 2388.1,
            "s9": 9052.0,
            "s11": 47.8,
            "s13": 2388.0,
            "s14": 8132.0
        }
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    trace = data["pipeline_trace"]
    assert trace["engine_unit"] == 99
    assert trace["cycle"] == 140
    assert "fan_speed_ratio" in trace["aerodynamic_features"]
    assert "compressor_pressure_ratio" in trace["aerodynamic_features"]
    assert "p10_lower_bound" in trace["conformal_rul_bounds"]
    assert "p50_median_rul" in trace["conformal_rul_bounds"]
    assert trace["rule_triage_decision"]["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "NORMAL")
