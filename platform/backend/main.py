"""Tata Elxsi Case Study 1 - AeroShield Predictive Maintenance Platform
High-Performance FastAPI Backend for Autonomous Fleet Maintenance & NASA C-MAPSS Digital Twin.
"""

import os
import sys
import json
import math
import re
import uuid
import hmac
import hashlib
import threading
from typing import Dict, List, Any, Optional, Literal

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="AeroShield Avionics Maintenance Platform",
    description="Tata Elxsi TELIPORT Case Study 1 - Autonomous Industrial Fleet Predictive Maintenance",
    version="3.5.0",
)

allowed_origins_env = os.environ.get("AEROSHIELD_CORS_ORIGINS", "")
ALLOWED_ORIGINS = [
    origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()
] if allowed_origins_env else [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

from .data_bridge import DataBridge

bridge = DataBridge()

VALID_SUBSETS = ("FD001", "FD002", "FD003", "FD004")
SubsetType = Literal["FD001", "FD002", "FD003", "FD004"]
StatusType = Literal["DISPATCHED", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
ScenarioType = Literal["gentle", "strong", "adaptive", "both", "all"]

PUBLISHED_DEV_API_KEY = "aeroshield-dev-key"
_api_key_env = os.environ.get("AEROSHIELD_API_KEY", "").strip()
ACTIVE_API_KEY = _api_key_env if _api_key_env else PUBLISHED_DEV_API_KEY


def verify_write_access(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """Validates the operator API key for state-mutating write routes.
    Rejects unauthorized requests with 401 Unauthorized.
    """
    if not x_api_key or not hmac.compare_digest(x_api_key.encode("utf-8"), ACTIVE_API_KEY.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing or invalid X-API-Key header. Provide a valid operator key to authorize write actions."
        )
    return "authorized-operator"


def _validate_subset(subset: str) -> str:
    """Guarantees unknown subsets return 404 rather than falling back to unvetted defaults."""
    if subset not in VALID_SUBSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Subset '{subset}' not found. Valid NASA C-MAPSS subsets are: {list(VALID_SUBSETS)}",
        )
    return subset


class OrderActionRequest(BaseModel):
    subset: SubsetType = "FD001"
    order_id: str
    new_status: StatusType
    operator: str = "Chief Fleet Reliability Officer"

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 60:
            raise ValueError("Operator name must be between 1 and 60 characters.")
        if not re.match(r"^[a-zA-Z0-9 _./#-]+$", v):
            raise ValueError("Operator name contains invalid characters. Only alphanumeric, spaces, and safe punctuation are allowed.")
        return v


class RetrainRequest(BaseModel):
    subset: SubsetType = "FD001"
    scenario: ScenarioType = "adaptive"


class PredictTelemetryRequest(BaseModel):
    subset: SubsetType = "FD001"
    unit: int = Field(1, ge=1, le=1000, description="Engine Unit ID (1..1000)")
    cycle: int = Field(1, ge=1, le=1000, description="Flight cycle (1..1000)")
    op1: float = Field(0.0, ge=-1000.0, le=1000.0, description="Operating condition 1")
    op2: float = Field(0.0, ge=-1000.0, le=1000.0, description="Operating condition 2")
    op3: float = Field(100.0, ge=-1000.0, le=1000.0, description="Operating condition 3")
    sensors: Optional[Dict[str, float]] = None
    persist: bool = Field(False, description="Whether to persist work order and audit block")

    @field_validator("sensors")
    @classmethod
    def validate_sensors(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is None:
            return v
        valid_keys = {f"s{i}" for i in range(1, 22)}
        for k, val in v.items():
            if k not in valid_keys:
                raise ValueError(f"Invalid sensor channel '{k}'. Allowed channels are s1 through s21.")
            if not isinstance(val, (int, float)) or not math.isfinite(val) or abs(val) > 1e6:
                raise ValueError(f"Sensor '{k}' must be a finite numeric value within [-1,000,000, 1,000,000].")
        return v


# Retrain job tracker and concurrency control
retrain_jobs: Dict[str, Dict[str, Any]] = {}
retrain_lock = threading.Lock()


def _execute_retrain_task(job_id: str, subset: str, scenario: str, repo_root: str):
    import subprocess
    script_path = os.path.join(repo_root, "retrain_demo.py")
    try:
        proc = subprocess.run(
            [sys.executable, script_path, "--subset", subset, "--scenario", scenario],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=180,
        )

        # Parse promotion outcome from retrain_history.json
        hist_file = os.path.join(repo_root, "outputs", subset, "retrain_history.json")
        promoted = False
        reason = "evaluation_completed"
        if os.path.exists(hist_file):
            try:
                with open(hist_file, "r") as f:
                    history = json.load(f)
                    if history and isinstance(history, list):
                        latest = history[-1]
                        promoted = latest.get("promoted", False)
                        reason = latest.get("reason", "evaluation_completed")
            except Exception:
                pass

        if proc.returncode == 0:
            if promoted:
                summary_text = "Retraining completed successfully. Candidate approved and promoted to Champion."
            else:
                summary_text = f"Retraining evaluated candidate. Gate decision: Blocked by Promotion Gate ({reason}). Production model preserved."
        else:
            summary_text = f"Retraining execution failed with exit code {proc.returncode}."

        retrain_jobs[job_id] = {
            "job_id": job_id,
            "status": "completed" if proc.returncode == 0 else "failed",
            "success": proc.returncode == 0,
            "promoted": promoted,
            "subset": subset,
            "scenario": scenario,
            "stdout": proc.stdout[-1000:] if proc.stdout else "",
            "summary": summary_text,
            "error": proc.stderr[-500:] if proc.stderr else None,
        }
    except Exception as e:
        retrain_jobs[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "success": False,
            "promoted": False,
            "subset": subset,
            "scenario": scenario,
            "summary": "Subprocess execution error",
            "error": str(e),
        }
    finally:
        if retrain_lock.locked():
            try:
                retrain_lock.release()
            except RuntimeError:
                pass


@app.get("/healthz")
def healthz():
    """Liveness probe reporting database connectivity, model directories, and deployment state."""
    ready_subsets = bridge.get_available_subsets()
    is_vercel = bool(os.getenv("VERCEL"))
    return {
        "status": "healthy",
        "service": "AeroShield Predictive Maintenance Platform",
        "version": "3.5.0",
        "subsets": ready_subsets,
        "ready_subsets": ready_subsets,
        "mode": "read-only-serverless" if is_vercel else "stateful-read-write",
        "auth_enabled": True,
        "database_connected": len(ready_subsets) > 0,
    }


@app.get("/")
@app.get("/dashboard")
def get_dashboard():
    """Serves the standalone production frontend dashboard."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dashboard.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="Dashboard UI file not found")
    return FileResponse(html_path, media_type="text/html")


@app.get("/api/subsets")
def get_subsets():
    """Returns available NASA C-MAPSS subsets that have generated metrics."""
    return {"subsets": bridge.get_available_subsets()}


@app.get("/api/fleet/readiness")
def get_fleet_readiness(subset: str = Query("FD001")):
    """Returns aggregate fleet health KPIs, operational rate, and severity distribution."""
    _validate_subset(subset)
    return bridge.get_fleet_readiness(subset)


@app.get("/api/fleet/matrix")
def get_fleet_matrix(subset: str = Query("FD001")):
    """Returns complete engine status matrix with RUL quantiles and severity."""
    _validate_subset(subset)
    return bridge.get_fleet_matrix(subset)


@app.get("/api/engine/{unit}")
def get_engine_drilldown(unit: int, subset: str = Query("FD001")):
    """Returns degradation timeline, 80% conformal envelope, and live sensor traces."""
    _validate_subset(subset)
    data = bridge.get_engine_drilldown(subset, unit)
    if not data:
        raise HTTPException(status_code=404, detail=f"Engine {unit} not found in subset {subset}")
    return data


@app.get("/api/work-orders")
def get_work_orders(subset: str = Query("FD001"), status: Optional[str] = None, limit: int = Query(50, ge=1, le=500)):
    """Returns active work orders filtered by optional status."""
    _validate_subset(subset)
    orders = bridge.get_work_orders(subset=subset, status=status, limit=limit)
    return {"work_orders": orders, "orders": orders, "count": len(orders)}


@app.get("/api/exceptions")
def get_human_exceptions(subset: str = Query("FD001")):
    """Returns data-quality exceptions and primary-secondary model conflicts."""
    _validate_subset(subset)
    exceptions = bridge.get_human_exceptions(subset)
    return {"exceptions": exceptions, "count": len(exceptions)}


@app.get("/api/audit-log")
def get_audit_log(subset: str = Query("FD001"), limit: int = Query(30, ge=1, le=500)):
    """Returns tamper-evident HMAC-SHA256 audit ledger."""
    _validate_subset(subset)
    return bridge.get_audit_log(subset, limit)


@app.get("/api/audit-verify")
def verify_audit_chain(subset: str = Query("FD001")):
    """Verifies full cryptographic chain integrity from Genesis to Head."""
    _validate_subset(subset)
    result = bridge.get_audit_log(subset, limit=1000)
    return {
        "verified": result.get("verified", False),
        "total_entries": result.get("total_entries", 0),
        "message": result.get("message", ""),
    }


@app.get("/api/mlops")
def get_mlops_data(subset: str = Query("FD001")):
    """Returns MLOps drift monitor, model registry, and retraining history."""
    _validate_subset(subset)
    return bridge.get_mlops_data(subset)


@app.post("/api/work-orders/dispatch")
def dispatch_work_order(
    req: OrderActionRequest,
    auth: str = Depends(verify_write_access)
):
    """Dispatches or resolves a work order and appends to audit log."""
    if os.getenv("VERCEL"):
        raise HTTPException(
            status_code=503,
            detail="Read-only deployment: Work order dispatch is disabled on stateless Vercel edge functions. Please run locally or via Docker for ACID database writes."
        )
    _validate_subset(req.subset)
    res = bridge.dispatch_work_order(req.subset, req.order_id, req.new_status, req.operator)
    if not res.get("success"):
        error_msg = res.get("error", "Dispatch failed")
        status_code = 422 if ("transition" in error_msg.lower() or "status" in error_msg.lower()) else 400
        raise HTTPException(status_code=status_code, detail=error_msg)
    return res


@app.post("/api/predict")
def predict_live_telemetry(
    req: PredictTelemetryRequest,
    auth: str = Depends(verify_write_access)
):
    """Executes live dynamic inference on raw telemetry inputs, evaluates the triage agent, and manages work order state."""
    _validate_subset(req.subset)
    return bridge.predict_telemetry(
        subset=req.subset,
        unit=req.unit,
        cycle=req.cycle,
        op1=req.op1,
        op2=req.op2,
        op3=req.op3,
        sensors=req.sensors,
        persist=req.persist
    )


@app.post("/api/retrain/trigger")
def trigger_retrain(
    req: RetrainRequest,
    background_tasks: BackgroundTasks,
    sync: bool = Query(True),
    auth: str = Depends(verify_write_access)
):
    """Executes closed-loop retraining demo with preprocessor adaptation."""
    if os.getenv("VERCEL"):
        raise HTTPException(
            status_code=503,
            detail="Read-only deployment: Model retraining is disabled on stateless Vercel edge functions. Retraining requires local GPU/CPU compute."
        )
    _validate_subset(req.subset)
    subset = req.subset
    scenario = req.scenario

    if not retrain_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="A retraining run is currently active. Concurrency is locked to prevent state corruption."
        )

    # Prune in-memory dictionary to keep at most last 20 jobs
    if len(retrain_jobs) >= 20:
        oldest_keys = list(retrain_jobs.keys())[:-19]
        for k in oldest_keys:
            retrain_jobs.pop(k, None)

    job_id = f"retrain-{uuid.uuid4().hex[:8]}"
    retrain_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "subset": subset,
        "scenario": scenario,
        "summary": "Retraining job queued in background...",
    }

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    if sync:
        _execute_retrain_task(job_id, subset, scenario, repo_root)
        job_result = retrain_jobs[job_id]
        return {
            "job_id": job_id,
            "success": job_result.get("success", False),
            "promoted": job_result.get("promoted", False),
            "status": job_result.get("status"),
            "stdout": job_result.get("stdout", ""),
            "summary": job_result.get("summary", ""),
            "subset": subset,
            "scenario": scenario,
        }
    else:
        background_tasks.add_task(_execute_retrain_task, job_id, subset, scenario, repo_root)
        return {
            "job_id": job_id,
            "status": "started",
            "message": "Retraining initiated in background.",
            "status_url": f"/api/retrain/status/{job_id}",
            "subset": subset,
            "scenario": scenario,
        }


@app.get("/api/retrain/status/{job_id}")
def get_retrain_status(job_id: str):
    """Polls the status of an asynchronous retraining job."""
    if job_id not in retrain_jobs:
        raise HTTPException(status_code=404, detail=f"Retrain job '{job_id}' not found")
    return retrain_jobs[job_id]
