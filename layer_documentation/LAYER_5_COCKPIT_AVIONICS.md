# Layer 5: Operational Defense Cockpit & Edge Serving

**Primary Code Files**:
* [`platform/backend/main.py`](../platform/backend/main.py) — FastAPI REST service and route handlers
* [`platform/backend/data_bridge.py`](../platform/backend/data_bridge.py) — High-throughput parquet/SQLite bridge connecting UI to models
* [`platform/frontend/dashboard.html`](../platform/frontend/dashboard.html) — Vision UI defense glassmorphic cockpit
* [`public/index.html`](../public/index.html) — Vercel edge frontend asset (synchronized with dashboard)
* [`api/index.py`](../api/index.py) — Vercel serverless ASGI subpath rewrite middleware

---

## 1. System Role & Architecture

Layer 5 provides the human-in-the-loop operational interface and REST API gateway. The autonomous predictive maintenance agent and triage state machine execute deterministically in Layer 3 with zero external language model dependencies.

```
Tactical Flight Cockpit (dashboard.html / public/index.html)
   │
   ├───────────────────────────────┬───────────────────────────────┐
   ▼                               ▼                               ▼
1. Cycle scrubber             2. Demo hash chain             3. Visual Avionics
   • Time-travel replay          • Linear block continuum       • Silent visual status
   • Conformal P10-P90 glow      • 1-Click HMAC copy            • Scrub bar feedback
   • Real-time gauge needles     • Sealed state machine         • Zero external assets
   │                               │                               │
   └───────────────────────────────┼───────────────────────────────┘
                                   │
                                   ▼
4. FastAPI High-Throughput REST Gateway (platform/backend/main.py)
   • /api/fleet/readiness, /api/engine/{unit}, /api/work-orders, /api/audit-log, /api/mlops
   • /api/work-orders/dispatch, /api/retrain/trigger
                                   │
                                   ▼
5. Vercel Serverless Edge Cloud
   • Lean bundle (<350 MB)
   • VercelRouteMiddleware (api/index.py)
   • Production: aeroshield-phi.vercel.app
```

---

## 2. Interactive Avionics Cockpit Features

### A. Four Operational Flight Views
1. **Fleet Health Overview**:
   - Fleet-wide operational readiness rate ($0–100\%$).
   - Measured conformal coverage tracking badge ($80\%$ target).
   - High-density turbofan matrix with multi-column sorting, search filtering, and RUL distribution chips.
2. **Engine Drill-Down & Time-Travel Replay**:
   - Avionics timeline scrub bar ($1$ to max cycle).
   - Dynamic Chart.js trajectory with illuminated conformal prediction bands ($P_{10}$ lower to $P_{90}$ upper) and true RUL benchmarks.
   - Live telemetry meters: fan speed ratio ($s_8/s_9$), corrected speed ratio ($s_{13}/s_{14}$), compressor pressure ratio ($s_{11}/s_7$), and turbine temperature ratio ($s_4/s_3$).
3. **Autonomous Triage & Compliance Ledger**:
   - Industrial work order dispatch cards with barcode insignia, priority halos, and depot bay routing.
   - Human specialist exception queue with one-click approved overrides.
   - **Demo hash chain**: A timeline of ledger blocks with copy and a verify button.
4. **MLOps Governance & Retraining Gate**:
   - Champion vs. Challenger side-by-side metric comparison table.
   - Interactive Population Stability Index (PSI) distribution charts across the 4 flight stages.
   - Live streaming terminal console for retraining execution stdout.

---

## 3. Vercel Serverless Edge Architecture

### A. Lean Dependency Optimization
* Standard ML deployments bundling `scikit-learn`, `mlflow`, `streamlit`, and `plotly` consume $>750$ MB, failing Vercel's $500$ MB Lambda ceiling.
* AeroShield cleanly isolates runtime serving dependencies in [`requirements.txt`](../requirements.txt) (`fastapi`, `pydantic`, `pandas`, `pyarrow`, `numpy`) totaling **341 MB**, moving heavy training dependencies to [`requirements-dev.txt`](../requirements-dev.txt).

### B. Subpath Rewrite Middleware
* In modern Vercel serverless Python apps, path rewrites like `/api/(.*) -> api/index.py` pass the target script path to ASGI `scope["path"]`.
* [`api/index.py`](../api/index.py) wraps FastAPI in `VercelRouteMiddleware`, cleanly parsing `_route` query parameters to restore the true REST endpoint path (`/api/subsets`, `/api/fleet/readiness`).
* **Live Production URL**: [https://aeroshield-phi.vercel.app](https://aeroshield-phi.vercel.app).

---

## 4. Integration Verification & Test Proofs

Covered in automated test suites:
* [`platform/test_platform.py`](../platform/test_platform.py) (13 tests):
  - `test_serve_dashboard`: Validates tactical HTML delivery.
  - `test_api_subsets`, `test_api_fleet_readiness`, `test_api_fleet_matrix`, `test_api_engine_drilldown`: Validates core data endpoints.
  - `test_api_work_orders`, `test_api_exceptions`, `test_api_audit_log`, `test_api_audit_verify`: Validates triage and blockchain verification.
  - `test_api_dispatch_work_order`, `test_api_retrain_trigger`: Validates write authorization and retrain trigger.
  - `test_api_mlops`: Validates MLOps drift and gate metrics.
  - `test_legacy_endpoints_decommissioned`: Validates that all legacy external endpoints return 404 Not Found.
