# AeroShield: Autonomous Predictive Fleet Maintenance Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Tests: 57/57 Passed](https://img.shields.io/badge/Tests-57%2F57%20Passed-emerald.svg)](pytest.ini)
[![Conformal Coverage: 80%](https://img.shields.io/badge/Conformal%20Coverage-80%25%20Calibrated-sky.svg)](docs/MATHEMATICAL_FORMULATION.md)
[![Zero-LLM Agent: Deterministic](https://img.shields.io/badge/Agent-Deterministic%20Non--LLM-indigo.svg)](shield/src/agent_rules.py)

> **Autonomous predictive maintenance, conformal Remaining Useful Life (RUL) estimation, deterministic triage dispatch, and cryptographic audit ledgers for connected industrial turbofans and aeroderivative engines.**  
> Built for **Tata Elxsi Case Study 1: Self-Healing Machines** using the full **NASA C-MAPSS (FD001–FD004)** turbofan benchmark suite.

---

## Executive Summary & Problem Statement

Modern connected fleets (commercial aircraft, industrial compressors, high-speed rail, heavy transport) continuously stream multi-channel sensor telemetry across operational regimes. Breakdown-reactive or rigid scheduled maintenance models result in catastrophic unplanned downtime, excessive parts consumption, and in-flight emergency shutdowns.

**AeroShield** delivers an end-to-end, closed-loop autonomous digital twin platform that:
1. **Cleans & Featurizes Telemetry**: Attenuates noise with causal running median filters and injects aerodynamic thermodynamic ratios directly from the gas path ($s_8/s_9$, $s_{13}/s_{14}$, $s_{11}/s_7$, $s_4/s_3$).
2. **Detects Early Anomaly Onset**: Utilizes baseline-subtracted sensor deviations to trigger early warnings $\approx 45$ cycles before failure with $\le 5.0\%$ False Alarm Rate across complex 6-regime fleets.
3. **Quantifies Conformal RUL Uncertainty**: Predicts remaining useful life intervals ($P_{10}, P_{50}, P_{90}$) backed by non-parametric conformal guarantees and secondary non-linear `HistGradientBoosting` consensus.
4. **Dispatches Work Orders Autonomously (Non-LLM)**: Evaluates a 4-tier severity matrix, assigns depot bays, routes sensor disagreements to human exception queues, and records every event in a **tamper-evident SHA-256 cryptographic audit ledger**.
5. **Governs MLOps & Retraining**: Evaluates age-matched Population Stability Index (PSI) drift and enforces a **1-sided, 4-condition statistical promotion gate** to prevent performance regressions.

---

## Benchmark Evaluation Results

Across all four NASA C-MAPSS subsets—ranging from single-regime sea-level operation (FD001) to 6-regime multi-fault degradation (FD004)—AeroShield achieves world-class predictive accuracy and safety guarantees:

| Dataset | Operating Conditions | Fault Modes | Turbofan Engines | Test Capped RMSE | NASA Asymmetric Loss | 80% Conformal Coverage | Anomaly Detection Rate | False Alarm Rate (FAR) | Mean Lead Warning |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FD001** | Single (Sea Level) | HPC Degradation | 100 | **11.30** | **2,779** | **84.0%** | **100.0%** | 4.0% | 38 cycles |
| **FD002** | Six Complex Regimes | HPC Degradation | 259 | **13.97** | **14,520** | **88.4%** | **100.0%** | 5.0% | 43 cycles |
| **FD003** | Single (Sea Level) | HPC + Fan Degradation | 100 | **11.23** | **2,680** | **86.0%** | **100.0%** | 3.5% | 40 cycles |
| **FD004** | Six Complex Regimes | HPC + Fan Degradation | 248 | **14.85** | **16,840** | **87.5%** | **100.0%** | 4.8% | 46 cycles |

*Evaluation methodology strictly enforces NASA asymmetric scoring where late over-predictions are exponentially penalized.*

---

## Platform Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        NASA C-MAPSS Turbofan Telemetry Stream                          │
│                   (21 Sensors, 3 Operational Settings, Multi-Regime)                   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Deterministic Data Engineering                                                │
│  - Single-Pass Running Median Filter (Window=5, noise attenuation)                    │
│  - Gas-Path Interaction Ratios: s8/s9, s13/s14, s11/s7, s4/s3                          │
│  - Regime-Aware Baseline Normalization (K-Means Clustering on Op Settings)             │
│  - Exponentially Weighted Moving Average (EWMA alpha=0.1)                              │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Machine Learning & Conformal Uncertainty Quantification                      │
│  - Baseline-Subtracted Sensor Anomaly Detector (Threshold tau=3.0, <=5% FAR)           │
│  - Primary Quantile Regressor: P10 / P50 / P90 Lifetime Estimator                      │
│  - Secondary Non-Linear Opinion: HistGradientBoosting (Model Agreement Gate)           │
│  - Conformal Prediction Calibration: 80% Validated Empirical Coverage Envelope         │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Autonomous Non-LLM Triage & Execution Engine                                  │
│  - 4-Tier Deterministic Rule Evaluator:                                                │
│    * Tier 1 (Critical): RUL <= 25 cyc  --> AOG Grounding & Immediate Shop Visit        │
│    * Tier 2 (High):     RUL <= 50 cyc  --> Priority Depot Spares Provisioning          │
│    * Tier 3 (Medium):   RUL <= 80 cyc  --> Scheduled Inspection at Turnaround          │
│    * Tier 4 (Healthy):  RUL > 80 cyc   --> Cleared for Sortie Envelope                 │
│  - Human Exception Queue: Sensor Spikes & Primary/Secondary Model Disagreements        │
│  - SQLite Order Lifecycle State Machine (DRAFT -> DISPATCHED -> COMPLETED)             │
│  - Tamper-Evident SHA-256 Blockchain Audit Chain (Immutable Event Provenance)          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 4: Continuous MLOps Governance & Drift Protection                                │
│  - Age-Matched Population Stability Index (PSI) Profiler (0-40, 40-80, 80-140, 140+)   │
│  - 4-Condition Statistical Invariance Gate:                                            │
│    1. Test RMSE <= Champion (Zero Degradation)                                        │
│    2. NASA Asymmetric Loss <= +5.0% Rise                                              │
│    3. 80% Conformal Coverage >= 75.0% Min (1-Sided Boundary)                           │
│    4. Late Over-Prediction Share <= +5.0 pts Over Champion                             │
│  - Live Retraining Trigger & Drift-Adaptive Preprocessor Statistics                    │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 5: Operational Defense Telemetry Cockpit                                         │
│  - FastAPI High-Throughput Async REST Service                                          │
│  - Vision UI Tactical Glassmorphic Cockpit (Plus Jakarta Sans, Tabular Numerals)       │
│  - 60fps Avionics Scrubber, Interactive Time-Travel Replay & Real-Time Audio Feedback   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Interactive Cockpit Highlights

The platform includes a tactile, aerospace-grade cockpit served via FastAPI at `http://127.0.0.1:8050/dashboard`:

* **Fleet Health Overview**: High-density KPI Bento grid, smooth Cubic Bézier sparklines with boundary clipping protection, real-time subsystem wear indicators, and an interactive 100–259 engine health matrix.
* **Engine Drill-Down & Time-Travel Replay**: 60fps avionics flight scrubber with automated milestone tracking (`Cycle 1`, `Anomaly Onset`, `Degradation Knee`, `Critical Cutoff`), P10–P90 conformal confidence envelopes, and live normalized sensor stations.
* **Autonomous Triage & Work Orders**: Tactical industrial dispatch tickets with depot bay assignment, technician work orders, human exception approvals, and interactive SHA-256 cryptographic blockchain audit ledger verification.
* **MLOps Governance & Retraining**: Side-by-side Champion vs. Challenger evaluation matrices, age-matched PSI drift histograms, and real-time retraining stdout execution streaming.
* **Human-Centered Aerospace Design**: Zero AI-slop typography standardized on **Plus Jakarta Sans** with `tabular-nums`, low-contrast tonal semantic status badges, and subtle synthetic Web Audio API acoustic feedback.

---

## Repository Structure

```
AeroShield-Predictive-Fleet-Maintenance/
├── .gitignore                         # Comprehensive exclusion of all cache, temp, and logs
├── LICENSE                            # MIT License
├── README.md                          # Defense-grade architectural and benchmark documentation
├── requirements.txt                   # Production & testing dependencies
├── pytest.ini                         # Pytest configuration
├── docker-compose.yml                 # Container orchestration
├── Dockerfile                         # Production FastAPI container
│
├── data/                              # NASA C-MAPSS Turbofan Benchmark Files
│   ├── train_FD001.txt .. FD004.txt  # Run-to-failure degradation trajectories
│   ├── test_FD001.txt .. FD004.txt   # Fleet operational test trajectories
│   ├── RUL_FD001.txt .. FD004.txt    # True end-of-test Remaining Useful Life labels
│   └── readme.txt                     # Official NASA dataset specification
│
├── shield/                            # Core ML, Data Engineering & Triage Engine
│   ├── config/
│   │   └── thresholds.yaml            # Operational bounds, SLA limits, and regime parameters
│   ├── src/
│   │   ├── agent_rules.py             # Deterministic 4-tier severity matrix
│   │   ├── anomaly.py                 # Baseline-subtracted sensor anomaly detector
│   │   ├── audit_chain.py             # SHA-256 tamper-evident cryptographic hash chain
│   │   ├── calibrate.py               # Conformal calibration & HistGradientBoosting consensus
│   │   ├── data.py                    # C-MAPSS ingress & operational regime clustering
│   │   ├── exceptions.py              # Sensor spike & model disagreement exception queue
│   │   ├── features.py                # Aerodynamic gas-path interaction ratios & EWMA features
│   │   ├── mlops.py                   # Age-matched PSI drift profiler & 1-sided promotion gate
│   │   ├── orders.py                  # SQLite work order state machine
│   │   ├── retrain_demo.py            # Live retraining demonstration with preprocessor adaptation
│   │   └── smoother.py                # Causal running median noise filter
│   └── tests/                         # Core automated test suite (47 unit tests)
│
├── platform/                          # Operational Web Cockpit & Telemetry Server
│   ├── backend/
│   │   ├── main.py                    # FastAPI async REST endpoints
│   │   └── data_bridge.py             # High-throughput bridge connecting UI to models and SQLite
│   ├── frontend/
│   │   └── dashboard.html             # Tactical glassmorphism cockpit (anti-AI slop typography & audio)
│   ├── run_platform.py                # Production launch script
│   └── test_platform.py               # Platform integration test suite (10 API tests)
│
├── outputs/                           # Pretrained Weights & Pre-calculated Telemetry
│   ├── registry.json                  # Production model registry metadata
│   ├── benchmark_summary.csv          # Comprehensive evaluation metrics across FD001-FD004
│   ├── FD001/ .. FD004/               # Calibrated joblib weights, parquet predictions, SQLite DBs
│
└── docs/                              # Technical Specifications & Formulations
    ├── Case_Study_1_Requirements.md   # Exact requirements brief from Tata Elxsi
    ├── ARCHITECTURE.md                # System topology and component interaction flow
    └── MATHEMATICAL_FORMULATION.md    # Formulations for NASA Loss, Conformal Bounds & PSI
```

---

## Quickstart & Local Installation

### 1. Clone the Repository
```bash
git clone https://github.com/vanshi0905/AeroShield-Predictive-Fleet-Maintenance.git
cd AeroShield-Predictive-Fleet-Maintenance
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the Automated Test Suite (57 Tests)
```bash
pytest
```
*Expected: 57 passed tests in ~11 seconds across all core engine and platform modules.*

### 4. Launch the Interactive Telemetry Cockpit
```bash
python platform/run_platform.py
```
Open **[http://127.0.0.1:8050/dashboard](http://127.0.0.1:8050/dashboard)** in your browser to inspect the fleet, test time-travel replay, authorize work order dispatches, and trigger MLOps retraining runs.

---

## API Reference

The FastAPI service exposes comprehensive REST endpoints documented automatically via Swagger at `http://127.0.0.1:8050/docs`:

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/subsets` | `GET` | Returns list of available C-MAPSS subsets (`FD001`–`FD004`) |
| `/api/fleet/readiness` | `GET` | Returns fleet health score, risk distribution, and conformal coverage |
| `/api/fleet/matrix` | `GET` | Returns high-density engine table with RUL quantiles and anomaly scores |
| `/api/engine/{unit}` | `GET` | Returns full flight cycle trajectory, sensor stations, and RUL bands |
| `/api/work-orders` | `GET` | Returns active autonomous maintenance work orders |
| `/api/work-orders/dispatch` | `POST` | Authorizes work order status change and appends SHA-256 block |
| `/api/exceptions` | `GET` | Returns human review queue for sensor spikes and model disagreement |
| `/api/audit-log` | `GET` | Returns cryptographic blockchain ledger entries |
| `/api/audit-verify` | `GET` | Executes live hash-chain verification across all blocks |
| `/api/mlops` | `GET` | Returns champion vs. challenger metrics, PSI drift, and gate status |
| `/api/retrain/trigger` | `POST` | Dispatches live model retraining with preprocessor drift adaptation |

---

## Author & Licensing

* **Author**: Vanshika Diwan ([@vanshi0905](https://github.com/vanshi0905))
* **Project**: Tata Elxsi Case Study 1 — *Self-Healing Machines: Predictive Maintenance for a Connected Fleet*
* **License**: Open-source under the [MIT License](LICENSE).
