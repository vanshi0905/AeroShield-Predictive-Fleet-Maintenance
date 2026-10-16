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

def test_api_dispatch_work_order():
    # Fetch an order from work_orders
    wo_res = client.get("/api/work-orders?subset=FD001")
    orders = wo_res.json()["work_orders"]
    if orders:
        first_order = orders[0]
        oid = first_order["order_id"]
        res = client.post("/api/work-orders/dispatch", json={
            "subset": "FD001",
            "order_id": oid,
            "new_status": "DISPATCHED",
            "operator": "Fleet Maintenance Controller"
        })
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["status"] == "DISPATCHED"

        # Verify audit chain remains cryptographically valid after dispatch
        v_res = client.get("/api/audit-verify?subset=FD001")
        assert v_res.status_code == 200
        assert v_res.json()["verified"] is True

