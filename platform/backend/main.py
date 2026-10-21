"""Tata Elxsi Case Study 1 - Predictive Maintenance Platform
FastAPI REST API Backend connecting the Vision UI cockpit to the SHIELD pipeline.
"""

import os
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
FRONTEND_HTML = os.path.join(PLATFORM_DIR, "frontend", "dashboard.html")

app = FastAPI(
    title="Tata Elxsi Predictive Fleet Maintenance API (Case Study 1)",
    description="Autonomous Predictive Maintenance, Conformal RUL & Triage System for Industrial Connected Fleet (NASA C-MAPSS)",
    version="1.0.0",
)

# Enable CORS for local development
# Configure secure CORS: restrict to local dashboard origins by default
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
from .voice_agent import SarvamVoiceEngine, AVAILABLE_SPEAKERS

bridge = DataBridge()
voice_engine = SarvamVoiceEngine()

# The string below used to be the development default, and it is in git history.
# It is not a secret. Every mode rejects it. Writes stay closed until
# AEROSHIELD_API_KEY is set to some other value.
PUBLISHED_DEV_API_KEY = "aeroshield-dev-key"
AEROSHIELD_ENV = os.getenv("AEROSHIELD_ENV", "development").lower()


def _admin_api_key() -> str:
    return os.getenv("AEROSHIELD_API_KEY", "").strip()


def _writes_configured() -> bool:
    key = _admin_api_key()
    return bool(key) and key != PUBLISHED_DEV_API_KEY


if AEROSHIELD_ENV in ("production", "prod") and not _writes_configured():
    raise RuntimeError(
        "AEROSHIELD_API_KEY must be set to a private value in production. "
        "The published development key is rejected."
    )


def verify_write_access(x_api_key: Optional[str] = Header(None)):
    """Dispatch, retrain, and voice posts need a private X-API-Key.

    Read at request time so a missing or published key cannot authorize a call.
    """
    key = _admin_api_key()
    if not key or key == PUBLISHED_DEV_API_KEY or not x_api_key or x_api_key != key:
        raise HTTPException(
            status_code=401,
            detail=(
                "Unauthorized. Set AEROSHIELD_API_KEY to a private value and send it "
                "as X-API-Key. The published development key is rejected."
            ),
        )

class OrderActionRequest(BaseModel):
    subset: str = "FD001"
    order_id: str
    new_status: str
    operator: str = "Chief Fleet Reliability Officer"

class RetrainRequest(BaseModel):
    subset: str = "FD001"
    scenario: Optional[str] = "strong"

class VoiceSynthesizeRequest(BaseModel):
    text: str
    speaker: str = "shubh"
    model: str = "bulbul:v3"

class VoiceCopilotRequest(BaseModel):
    query: str
    subset: str = "FD001"
    unit: Optional[int] = None
    speaker: str = "shubh"

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
    return bridge.get_fleet_readiness(subset)

@app.get("/api/fleet/matrix")
def get_fleet_matrix(subset: str = Query("FD001"), status: Optional[str] = Query(None)):
    """Returns the matrix of all engines for the selected subset."""
    return {"engines": bridge.get_fleet_matrix(subset, status_filter=status)}

@app.get("/api/engine/{unit}")
def get_engine_drilldown(unit: int, subset: str = Query("FD001")):
    """Returns full cycle trajectory, RUL bands, anomaly scores, and aerodynamic ratios for replay."""
    res = bridge.get_engine_drilldown(subset, unit)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.get("/api/work-orders")
def get_work_orders(subset: str = Query("FD001"), limit: int = Query(50)):
    """Returns autonomous maintenance work orders."""
    return {"work_orders": bridge.get_work_orders(subset, limit)}

@app.get("/api/exceptions")
def get_human_exceptions(subset: str = Query("FD001")):
    """Returns human exception queue."""
    return {"exceptions": bridge.get_human_exceptions(subset)}

@app.get("/api/audit-log")
def get_audit_log(subset: str = Query("FD001"), limit: int = Query(30)):
    """Returns cryptographic audit trail and hash chain status."""
    return bridge.get_audit_log(subset, limit)

@app.get("/api/audit-verify")
def verify_audit(subset: str = Query("FD001")):
    """Triggers live blockchain-style audit chain verification."""
    log = bridge.get_audit_log(subset, limit=1000)
    return {
        "verified": log.get("verified", False),
        "total_entries": log.get("total_entries", 0),
        "message": log.get("message", "Verification completed"),
    }

@app.get("/api/mlops")
def get_mlops_data(subset: str = Query("FD001")):
    """Returns MLOps drift monitor, model registry, and retraining history."""
    return bridge.get_mlops_data(subset)

@app.post("/api/work-orders/dispatch", dependencies=[Depends(verify_write_access)])
def dispatch_work_order(req: OrderActionRequest):
    """Dispatches or resolves a work order and appends to audit log."""
    res = bridge.dispatch_work_order(req.subset, req.order_id, req.new_status, req.operator)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Dispatch failed"))
    return res

@app.post("/api/retrain/trigger", dependencies=[Depends(verify_write_access)])
def trigger_retrain(req: RetrainRequest):
    """Executes closed-loop retraining demo with preprocessor adaptation."""
    import subprocess, sys
    subset = req.subset or "FD001"
    scenario = req.scenario or "strong"
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    script_path = os.path.join(repo_root, "retrain_demo.py")

    try:
        proc = subprocess.run(
            [sys.executable, script_path, "--subset", subset, "--scenario", scenario],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "subset": subset,
            "scenario": scenario,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Subprocess execution error: {str(e)}",
            "subset": subset,
            "scenario": scenario,
        }

@app.get("/api/voice/status")
def get_voice_status():
    """Returns Sarvam AI voice engine status and available speaker personas."""
    return {
        "configured": voice_engine.is_configured(),
        "provider": "Sarvam AI",
        "chat_model": "sarvam-105b-conversations",
        "tts_model": "bulbul:v3",
        "speakers": AVAILABLE_SPEAKERS,
        "default_speaker": "shubh"
    }

@app.post("/api/voice/synthesize", dependencies=[Depends(verify_write_access)])
def synthesize_voice(req: VoiceSynthesizeRequest):
    """Synthesizes tactical cockpit audio using Sarvam Bulbul neural TTS."""
    clean_text = req.text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    audio = voice_engine.synthesize_speech(clean_text, speaker=req.speaker, model=req.model)
    return {
        "success": bool(audio),
        "audio_base64": audio,
        "speaker": req.speaker,
        "format": "audio/wav"
    }

@app.post("/api/voice/copilot", dependencies=[Depends(verify_write_access)])
def query_voice_copilot(req: VoiceCopilotRequest):
    """Interacts with the grounded AeroShield Voice Copilot (Sarvam 105B + Bulbul)."""
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    res = voice_engine.query_copilot(
        query=clean_query,
        subset=req.subset,
        unit=req.unit,
        speaker=req.speaker,
        bridge=bridge
    )
    return res
