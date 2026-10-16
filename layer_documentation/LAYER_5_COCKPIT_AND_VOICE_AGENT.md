# Layer 5: Operational Defense Cockpit, Sarvam Voice Agent & Edge Serving

**Primary Code Files**:
* [`platform/backend/main.py`](../platform/backend/main.py) — FastAPI REST service and route handlers
* [`platform/backend/voice_agent.py`](../platform/backend/voice_agent.py) — Sarvam AI Copilot (`sarvam-105b-conversations`) and Bulbul v3 neural speech synthesis
* [`platform/backend/data_bridge.py`](../platform/backend/data_bridge.py) — High-throughput parquet/SQLite bridge connecting UI to models
* [`platform/frontend/dashboard.html`](../platform/frontend/dashboard.html) — Vision UI defense glassmorphic cockpit
* [`public/index.html`](../public/index.html) — Vercel edge frontend asset (synchronized with dashboard)
* [`api/index.py`](../api/index.py) — Vercel serverless ASGI subpath rewrite middleware

---

## 1. System Role & Architecture

Layer 5 delivers the human-machine interface (HMI), conversational intelligence, and cloud edge deployment for the AeroShield platform. It translates complex telemetry matrices, conformal prediction intervals, and cryptographic ledgers into an intuitive, 60fps tactile defense cockpit. It integrates the Sarvam AI voice engine, allowing flight controllers and maintenance chiefs to interact with the fleet via natural voice.

```
Tactical Flight Cockpit (dashboard.html / public/index.html)
   │
   ├───────────────────────────────┬───────────────────────────────┐
   ▼                               ▼                               ▼
1. 60fps Avionics Scrubber    2. FAA Part 145 Ledger         3. Sarvam Voice Copilot
   • Time-travel replay          • Linear block continuum       • Speech-to-text mic
   • Conformal P10-P90 glow      • 1-Click SHA-256 copy         • Quick prompt chips
   • Real-time gauge needles     • Sealed state machine         • Waveform visualizer
   │                               │                               │
   └───────────────────────────────┼───────────────────────────────┘
                                   │
                                   ▼
4. FastAPI High-Throughput REST Gateway (platform/backend/main.py)
   • /api/fleet/readiness, /api/engine/{unit}, /api/work-orders, /api/audit-log, /api/mlops
   • /api/voice/status, /api/voice/synthesize, /api/voice/copilot
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
5. Sarvam AI Voice Engine                        6. Vercel Serverless Edge Cloud
   • sarvam-105b-conversations (Reasoning)           • Lean bundle (<350 MB)
   • bulbul:v3 Neural TTS (~200ms latency)           • VercelRouteMiddleware (api/index.py)
   • Personas: Shubh, Priya, Aditya, Neha            • Production: aeroshield-phi.vercel.app
```

---

## 2. Interactive Avionics Cockpit Features

### A. Four Operational Flight Views
1. **Fleet Health Overview**:
   - Fleet-wide operational readiness rate ($0–100\%$).
   - Conformal coverage tracking badge ($80\%$ target).
   - High-density turbofan matrix with multi-column sorting, search filtering, and RUL distribution chips.
2. **Engine Drill-Down & Time-Travel Replay**:
   - Avionics timeline scrub bar ($1$ to max cycle).
   - Dynamic Chart.js trajectory with illuminated conformal prediction bands ($P_{10}$ lower to $P_{90}$ upper) and true RUL benchmarks.
   - Live telemetry meters: fan speed ratio ($s_8/s_9$), corrected speed ratio ($s_{13}/s_{14}$), compressor pressure ratio ($s_{11}/s_7$), and turbine temperature ratio ($s_4/s_3$).
3. **Autonomous Triage & Compliance Ledger**:
   - Industrial work order dispatch cards with barcode insignia, priority halos, and depot bay routing.
   - Human specialist exception queue with one-click approved overrides.
   - **FAA Part 145 / EASA M.A.306 Regulatory Ledger**: A clean, linear block continuum timeline with 1-click clipboard hash copy and cryptographic verification.
4. **MLOps Governance & Retraining Gate**:
   - Champion vs. Challenger side-by-side metric comparison table.
   - Interactive Population Stability Index (PSI) distribution charts across the 4 flight stages.
   - Live streaming terminal console for retraining execution stdout.

---

## 3. Sarvam AI Voice Copilot & Speech Synthesis

### A. Domain-Grounded Reasoning (`sarvam-105b-conversations`)
* When a voice or text query is submitted, the backend extracts the current fleet partition readiness, target engine telemetry (cycle, RUL quantiles, anomaly score, suspect subsystem), and open work orders.
* Injects telemetry context into `sarvam-105b-conversations` with a strict aerospace flight controller prompt.
* Produces authoritative, 2-to-3 sentence briefings containing exact numerical data.

### B. Studio-Grade Neural Text-to-Speech (`bulbul:v3`)
* Converts briefings into crisp, natural 22.05 kHz WAV audio in sub-second latency ($\approx 200–250$ms).
* **Four Selectable Voice Personas**:
  * **Shubh**: Lead Tactical Commander (Authoritative default).
  * **Priya**: Avionics Systems Officer (Tactical operational clarity).
  * **Aditya**: Chief Fleet Engineer (Technical analysis).
  * **Neha**: Flight Controller (Clear monitoring alerts).
* **Automatic Fallback**: If the API is unreachable or rate-limited, the system seamlessly falls back to the local browser Web Speech API.

---

## 4. Vercel Serverless Edge Architecture

### A. Lean Dependency Optimization
* Standard ML deployments bundling `scikit-learn`, `mlflow`, `streamlit`, and `plotly` consume $>750$ MB, failing Vercel's $500$ MB Lambda ceiling.
* AeroShield cleanly isolates runtime serving dependencies in [`requirements.txt`](../requirements.txt) (`fastapi`, `pydantic`, `pandas`, `pyarrow`, `numpy`) totaling **341 MB**, moving heavy training dependencies to [`requirements-dev.txt`](../requirements-dev.txt).

### B. Subpath Rewrite Middleware
* In modern Vercel serverless Python apps, path rewrites like `/api/(.*) -> api/index.py` pass the target script path to ASGI `scope["path"]`.
* [`api/index.py`](../api/index.py) wraps FastAPI in `VercelRouteMiddleware`, cleanly parsing `_route` query parameters to restore the true REST endpoint path (`/api/subsets`, `/api/fleet/readiness`, `/api/voice/status`).
* **Live Production URL**: [https://aeroshield-phi.vercel.app](https://aeroshield-phi.vercel.app).

---

## 5. Integration Verification & Test Proofs

Covered in automated test suites:
* [`platform/test_platform.py`](../platform/test_platform.py) (13 tests):
  - `test_dashboard_endpoint`: Validates tactical HTML delivery.
  - `test_api_subsets`, `test_api_fleet_readiness`, `test_api_fleet_matrix`, `test_api_engine_drilldown`: Validates core data endpoints.
  - `test_api_work_orders`, `test_api_exceptions`, `test_api_audit_log_and_verify`, `test_api_dispatch_work_order`: Validates triage and blockchain verification.
  - `test_api_mlops`: Validates MLOps drift and gate metrics.
  - `test_api_voice_status`, `test_api_voice_synthesize`, `test_api_voice_copilot`: Validates Sarvam AI voice engine, persona catalog, and conversational loop.
