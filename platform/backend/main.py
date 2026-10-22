"""Tata Elxsi Case Study 1 - Predictive Maintenance Platform
FastAPI REST API Backend connecting the Vision UI cockpit to the SHIELD pipeline.
"""

import os
import sys
import uuid
import re
from typing import Optional, Dict, Any, Literal
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
FRONTEND_HTML = os.path.join(PLATFORM_DIR, "frontend", "dashboard.html")

app = FastAPI(
    title="Tata Elxsi Predictive Fleet Maintenance API (Case Study 1)",
    description="Autonomous Predictive Maintenance, Conformal RUL & Triage System for Industrial Connected Fleet (NASA C-MAPSS)",
    version="1.0.0",
)

# Enable CORS for local development
allowed_origins_env = os.getenv("AEROSHIELD_ALLOWED_ORIGINS", "")
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
    scenario: Optional[str] = "strong"


class PredictTelemetryRequest(BaseModel):
    subset: SubsetType = "FD001"
    unit: int = 1
    cycle: int = 100
    op1: float = 0.0
    op2: float = 0.0
    op3: float = 100.0
    sensors: Optional[Dict[str, float]] = None


# Retrain job tracker for asynchronous background retraining
retrain_jobs: Dict[str, Dict[str, Any]] = {}


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
        retrain_jobs[job_id] = {
            "job_id": job_id,
            "status": "completed" if proc.returncode == 0 else "failed",
            "success": proc.returncode == 0,
            "subset": subset,
            "scenario": scenario,
            "stdout": proc.stdout[-1000:] if proc.stdout else "",
            "summary": "Retraining completed successfully. Model passed promotion gates." if proc.returncode == 0 else "Retraining failed promotion gates.",
            "error": proc.stderr[-500:] if proc.stderr else None,
        }
    except Exception as e:
        retrain_jobs[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "success": False,
            "subset": subset,
            "scenario": scenario,
            "summary": "Subprocess execution error",
            "error": str(e),
        }


@app.get("/healthz")
def healthz():
    """Liveness and container health check probe."""
    return {
        "status": "healthy",
        "service": "AeroShield Avionics Fleet Command",
        "version": "1.0.0",
        "subsets": list(VALID_SUBSETS),
        "edge_mode": "read_only" if os.getenv("VERCEL") else "persistent"
    }


@app.get("/")
@app.get("/dashboard")
def serve_dashboard():
    """Serves the Vision UI Tactical Glassmorphic Cockpit"""
    if os.path.exists(FRONTEND_HTML):
        return FileResponse(FRONTEND_HTML)
    raise HTTPException(status_code=404, detail=f"Dashboard file not found at {FRONTEND_HTML}")


@app.get("/api/subsets")
def get_subsets():
    """Returns available C-MAPSS subsets."""
    return {"subsets": bridge.get_available_subsets()}


@app.get("/api/fleet/readiness")
def get_fleet_readiness(subset: str = Query("FD001")):
    """Returns fleet health KPIs and risk distribution."""
    _validate_subset(subset)
    return bridge.get_fleet_readiness(subset)


@app.get("/api/fleet/matrix")
def get_fleet_matrix(subset: str = Query("FD001"), status: Optional[str] = Query(None)):
    """Returns the matrix of all engines for the selected subset."""
    _validate_subset(subset)
    return {"engines": bridge.get_fleet_matrix(subset, status_filter=status)}


@app.get("/api/engine/{unit}")
def get_engine_drilldown(unit: int, subset: str = Query("FD001")):
    """Returns full cycle trajectory, RUL bands, anomaly scores, and aerodynamic ratios for replay."""
    _validate_subset(subset)
    res = bridge.get_engine_drilldown(subset, unit)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@app.get("/api/work-orders")
def get_work_orders(
    subset: str = Query("FD001"),
    limit: int = Query(50, ge=1, le=500)
):
    """Returns autonomous maintenance work orders with bounded limit query."""
    _validate_subset(subset)
    return {"work_orders": bridge.get_work_orders(subset, limit)}


@app.get("/api/exceptions")
def get_human_exceptions(subset: str = Query("FD001")):
    """Returns human exception queue."""
    _validate_subset(subset)
    return {"exceptions": bridge.get_human_exceptions(subset)}


@app.get("/api/audit-log")
def get_audit_log(
    subset: str = Query("FD001"),
    limit: int = Query(30, ge=1, le=500)
):
    """Returns cryptographic audit trail and hash chain status with bounded limit."""
    _validate_subset(subset)
    return bridge.get_audit_log(subset, limit)


@app.get("/api/audit-verify")
def verify_audit(subset: str = Query("FD001")):
    """Triggers live blockchain-style audit chain verification."""
    _validate_subset(subset)
    log = bridge.get_audit_log(subset, limit=1000)
    return {
        "verified": log.get("verified", False),
        "total_entries": log.get("total_entries", 0),
        "message": log.get("message", "Verification completed"),
    }


@app.get("/api/mlops")
def get_mlops_data(subset: str = Query("FD001")):
    """Returns MLOps drift monitor, model registry, and retraining history."""
    _validate_subset(subset)
    return bridge.get_mlops_data(subset)


@app.post("/api/work-orders/dispatch")
def dispatch_work_order(req: OrderActionRequest):
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
        status_code = 422 if "transition" in error_msg.lower() else 400
        raise HTTPException(status_code=status_code, detail=error_msg)
    return res


@app.post("/api/predict")
def predict_live_telemetry(req: PredictTelemetryRequest):
    """Executes live dynamic inference on raw telemetry inputs, evaluates the triage agent, and updates SQLite state."""
    _validate_subset(req.subset)
    return bridge.predict_telemetry(
        subset=req.subset,
        unit=req.unit,
        cycle=req.cycle,
        op1=req.op1,
        op2=req.op2,
        op3=req.op3,
        sensors=req.sensors
    )


@app.post("/api/retrain/trigger")
def trigger_retrain(
    req: RetrainRequest,
    background_tasks: BackgroundTasks,
    sync: bool = Query(True)
):
    """Executes closed-loop retraining demo with preprocessor adaptation."""
    if os.getenv("VERCEL"):
        raise HTTPException(
            status_code=503,
            detail="Read-only deployment: Model retraining is disabled on stateless Vercel edge functions. Retraining requires local GPU/CPU compute."
        )
    _validate_subset(req.subset)
    subset = req.subset
    scenario = req.scenario or "strong"
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    job_id = f"retrain-{uuid.uuid4().hex[:8]}"
    retrain_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "subset": subset,
        "scenario": scenario,
        "summary": "Retraining job queued in background...",
    }

    if sync:
        _execute_retrain_task(job_id, subset, scenario, repo_root)
        job_result = retrain_jobs[job_id]
        return {
            "job_id": job_id,
            "success": job_result.get("success", False),
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
