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

TEST_KEY = "test-only-private-key"
os.environ["AEROSHIELD_API_KEY"] = TEST_KEY   # must be set before the app module is imported

try:
    import platform.backend.main as main_mod
except ImportError:
    import backend.main as main_mod
app = main_mod.app

client = TestClient(app)

@pytest.fixture(autouse=True, scope="session")
def preserve_work_orders_db():
    """Ensures test writes do not dirty the committed outputs/FD001/work_orders.db."""
    db_path = os.path.join(REPO_ROOT, "outputs", "FD001", "work_orders.db")
    backup_data = None
    if os.path.exists(db_path):
        with open(db_path, "rb") as f:
            backup_data = f.read()
    yield
    if backup_data is not None and os.path.exists(db_path):
        with open(db_path, "wb") as f:
            f.write(backup_data)


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
    engines = data if isinstance(data, list) else data.get("engines", [])
    assert len(engines) > 0
    first = engines[0]
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


def test_api_dispatch_work_order_auth():
    # 1. Without API key -> 401 Unauthorized
    res_no_key = client.post(
        "/api/work-orders/dispatch",
        json={"subset": "FD001", "order_id": "WO-1", "new_status": "DISPATCHED"}
    )
    assert res_no_key.status_code == 401
    assert "X-API-Key" in res_no_key.json()["detail"]

    # 2. With valid API key -> 200 OK
    wo_res = client.get("/api/work-orders?subset=FD001")
    orders = wo_res.json()["work_orders"]
    if orders:
        oid = orders[0]["order_id"]
        res = client.post(
            "/api/work-orders/dispatch",
            json={
                "subset": "FD001",
                "order_id": oid,
                "new_status": "DISPATCHED",
                "operator": "Fleet Maintenance Controller"
            },
            headers={"X-API-Key": TEST_KEY}
        )
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["status"] == "DISPATCHED"

        v_res = client.get("/api/audit-verify?subset=FD001")
        assert v_res.status_code == 200
        assert v_res.json()["verified"] is True


def test_api_retrain_trigger_execution(monkeypatch):
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

    # Without key -> 401
    res_unauth = client.post(
        "/api/retrain/trigger",
        json={"subset": "FD001", "scenario": "strong"}
    )
    assert res_unauth.status_code == 401

    # With invalid scenario -> 422
    res_invalid = client.post(
        "/api/retrain/trigger",
        json={"subset": "FD001", "scenario": "malicious"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res_invalid.status_code == 422

    # With valid key -> 200
    res = client.post(
        "/api/retrain/trigger",
        json={"subset": "FD001", "scenario": "strong"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Gate passed" in data["stdout"]
    assert data["subset"] == "FD001"
    assert len(captured_args) == 1
    assert "--subset" in captured_args[0]
    assert "FD001" in captured_args[0]


def test_unknown_endpoints_return_404():
    """Confirms all undefined or unsupported endpoints return 404 Not Found."""
    assert client.get("/api/unknown_service/status").status_code == 404
    assert client.post("/api/unknown_service/process").status_code == 404
    assert client.get("/api/external/chat").status_code == 404


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
    # 1. Unauthenticated -> 401
    res_unauth = client.post("/api/predict", json=payload)
    assert res_unauth.status_code == 401

    # 2. Absurd input bounds testing (Senior N2) -> 422
    assert client.post("/api/predict", json={**payload, "unit": -5}, headers={"X-API-Key": TEST_KEY}).status_code == 422
    assert client.post("/api/predict", json={**payload, "cycle": 1000000000}, headers={"X-API-Key": TEST_KEY}).status_code == 422
    assert client.post("/api/predict", json={**payload, "op1": 1e300}, headers={"X-API-Key": TEST_KEY}).status_code == 422
    assert client.post("/api/predict", json={**payload, "sensors": {"s99": 10.0}}, headers={"X-API-Key": TEST_KEY}).status_code == 422

    # 3. Valid authenticated request -> 200
    res = client.post("/api/predict", json=payload, headers={"X-API-Key": TEST_KEY})
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


def test_senior_audit_subset_allowlist_returns_404():
    res = client.get("/api/fleet/readiness?subset=FD9")
    assert res.status_code == 404
    assert "FD9" in res.json()["detail"]


def test_senior_audit_invalid_status_returns_422():
    res = client.post(
        "/api/work-orders/dispatch",
        json={"subset": "FD001", "order_id": "WO-1", "new_status": "HACKED"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res.status_code == 422


def test_senior_audit_operator_sanitization_returns_422():
    # XSS attempt
    res_xss = client.post(
        "/api/work-orders/dispatch",
        json={"subset": "FD001", "order_id": "WO-1", "new_status": "DISPATCHED", "operator": "<script>alert(1)</script>"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res_xss.status_code == 422

    # String length > 60 chars
    res_len = client.post(
        "/api/work-orders/dispatch",
        json={"subset": "FD001", "order_id": "WO-1", "new_status": "DISPATCHED", "operator": "A" * 61},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res_len.status_code == 422


def test_senior_audit_healthz_endpoint():
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "FD001" in data["subsets"]


def test_senior_audit_vercel_readonly_mode(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    res_dispatch = client.post(
        "/api/work-orders/dispatch",
        json={"subset": "FD001", "order_id": "WO-1", "new_status": "DISPATCHED"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res_dispatch.status_code == 503
    assert "read-only" in res_dispatch.json()["detail"].lower()

    res_retrain = client.post(
        "/api/retrain/trigger",
        json={"subset": "FD001"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res_retrain.status_code == 503


def test_senior_audit_retrain_async_status_flow(monkeypatch):
    import subprocess
    class MockProcess:
        returncode = 0
        stdout = "[demo] training champion v1... Gate passed."
        stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: MockProcess())

    res = client.post(
        "/api/retrain/trigger?sync=false",
        json={"subset": "FD001", "scenario": "strong"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "started"
    job_id = data["job_id"]

    # Query status endpoint
    poll_res = client.get(f"/api/retrain/status/{job_id}")
    assert poll_res.status_code == 200
    poll_data = poll_res.json()
    assert poll_data["job_id"] == job_id
    assert poll_data["status"] in ("running", "completed", "failed")


def test_published_dev_key_is_rejected():
    res = client.post("/api/work-orders/dispatch",
                      json={"subset": "FD001", "order_id": "X", "new_status": "DISPATCHED"},
                      headers={"X-API-Key": "aeroshield-dev-key"})
    assert res.status_code == 401


def test_write_routes_closed_without_private_key(monkeypatch):
    monkeypatch.setattr(main_mod, "ACTIVE_API_KEY", "")
    for key in (None, "aeroshield-dev-key", TEST_KEY):
        headers = {"X-API-Key": key} if key else {}
        res = client.post("/api/work-orders/dispatch",
                          json={"subset": "FD001", "order_id": "X", "new_status": "DISPATCHED"}, headers=headers)
        assert res.status_code == 503


def test_demo_mode_is_opt_in_and_reported(monkeypatch):
    assert client.get("/healthz").json()["demo_mode"] is False
    monkeypatch.setattr(main_mod, "ACTIVE_API_KEY", main_mod.PUBLISHED_DEV_API_KEY)
    assert client.get("/healthz").json()["demo_mode"] is True
    res = client.post("/api/work-orders/dispatch",
                      json={"subset": "FD001", "order_id": "NOPE", "new_status": "DISPATCHED"},
                      headers={"X-API-Key": "aeroshield-dev-key"})
    assert res.status_code != 401 and res.status_code != 503   # auth passed; order simply does not exist


def test_api_predict_production_and_simulator_modes():
    """Validates real production champion pipeline execution vs calibrated simulator."""
    # Production champion execution
    payload_prod = {
        "subset": "FD001",
        "unit": 1,
        "cycle": 31,
        "mode": "production"
    }
    res_prod = client.post("/api/predict", json=payload_prod, headers={"X-API-Key": TEST_KEY})
    assert res_prod.status_code == 200
    data_prod = res_prod.json()
    assert data_prod["status"] == "success"
    assert data_prod["model_type"] == "production_champion_bundle"
    assert data_prod["inference_mode"] == "production_champion"
    trace = data_prod["pipeline_trace"]
    assert "ridge_consensus_p50" in trace["conformal_rul_bounds"]
    assert trace["conformal_rul_bounds"]["p50_median_rul"] > 0

    # Calibrated simulator execution
    payload_sim = {
        "subset": "FD001",
        "unit": 1,
        "cycle": 31,
        "mode": "simulator"
    }
    res_sim = client.post("/api/predict", json=payload_sim, headers={"X-API-Key": TEST_KEY})
    assert res_sim.status_code == 200
    data_sim = res_sim.json()
    assert data_sim["status"] == "success"
    assert data_sim["model_type"] == "simplified_what_if_simulator"
    assert data_sim["inference_mode"] == "calibrated_simulator"


def test_api_stream_telemetry_events():
    """Validates Server-Sent Events (SSE) telemetry streaming for real-time sensor processing."""
    res = client.get("/api/stream/telemetry/1?subset=FD001&speed_ms=10&max_cycles=4")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "data:" in text
    assert "critical_flag" in text
    assert "p50" in text

    # Unknown unit returns 404
    res_404 = client.get("/api/stream/telemetry/9999?subset=FD001")
    assert res_404.status_code == 404


def test_api_self_healing_prescriptions():
    """Validates closed-loop prescriptive self-healing recommendations."""
    res = client.get("/api/self-healing/1?subset=FD001")
    assert res.status_code == 200
    data = res.json()
    assert data["unit"] == 1
    assert data["subset"] == "FD001"
    assert "thrust_derate_prescription" in data
    assert "derate_percentage" in data["thrust_derate_prescription"]
    assert "thermal_relief_deg_c" in data["thrust_derate_prescription"]
    assert "extended_safe_cycles" in data["thrust_derate_prescription"]
    assert "sensor_fault_isolation" in data
    assert "flight_envelope_advisory" in data
    assert "depot_routing_and_logistics" in data

    # Unknown unit returns 404
    res_404 = client.get("/api/self-healing/9999?subset=FD001")
    assert res_404.status_code == 404


def test_api_fleet_survival_analytics():
    """Validates Kaplan-Meier fleet survival distribution and hazard reliability modeling."""
    res = client.get("/api/fleet/survival?subset=FD001")
    assert res.status_code == 200
    data = res.json()
    assert data["subset"] == "FD001"
    assert data["total_fleet_units"] == 100
    assert data["fleet_mttf_cycles"] > 0
    assert len(data["survival_curve"]) == 12

    # Survival probability is monotonically non-increasing
    probs = [step["survival_probability"] for step in data["survival_curve"]]
    for i in range(len(probs) - 1):
        assert probs[i] >= probs[i + 1]

    assert "subsystem_reliability_indices" in data
    assert "high_pressure_compressor" in data["subsystem_reliability_indices"]


def test_api_batch_work_order_dispatch():
    """Validates batch work order transitions and HMAC-SHA256 audit chaining."""
    # 1. Unauthenticated -> 401
    res_unauth = client.post(
        "/api/work-orders/batch-dispatch",
        json={"subset": "FD001", "order_ids": ["EX-0036-001"], "new_status": "DISPATCHED"}
    )
    assert res_unauth.status_code == 401

    # 2. Invalid status -> 422
    res_inv = client.post(
        "/api/work-orders/batch-dispatch",
        json={"subset": "FD001", "order_ids": ["EX-0036-001"], "new_status": "INVALID_STATUS"},
        headers={"X-API-Key": TEST_KEY}
    )
    assert res_inv.status_code == 422

    # 3. Valid authenticated batch action
    res = client.post(
        "/api/work-orders/batch-dispatch",
        json={
            "subset": "FD001",
            "order_ids": ["EX-0036-001"],
            "new_status": "DISPATCHED",
            "operator": "Chief Reliability Officer",
            "root_cause": "HPC_FOULING"
        },
        headers={"X-API-Key": TEST_KEY}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["processed_count"] == 1
    assert len(data["audit_hashes"]) == 1
    assert "head_audit_hash" in data
