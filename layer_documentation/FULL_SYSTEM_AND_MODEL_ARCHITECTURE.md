# AeroShield: Master System, Model Architecture & Layer Documentation

> **Tata Elxsi Case Study 1: Self-Healing Machines — Predictive Maintenance for a Connected Fleet**  
> Evaluated on the full **NASA C-MAPSS (FD001–FD004)** Turbofan Degradation Benchmark Suite.

---

## Table of Contents
1. [Executive Summary & Case Study Alignment](#1-executive-summary--case-study-alignment)
2. [NASA C-MAPSS Benchmark Evaluation Matrix](#2-nasa-c-mapss-benchmark-evaluation-matrix)
3. [Five-Layer System Topology](#3-five-layer-system-topology)
4. [Layer 1: Deterministic Ingress & Aerodynamic Feature Engineering](#4-layer-1-deterministic-ingress--aerodynamic-feature-engineering)
5. [Layer 2: ML Inference, Conformal Uncertainty & Anomaly Detection](#5-layer-2-ml-inference-conformal-uncertainty--anomaly-detection)
6. [Layer 3: Autonomous Triage & Cryptographic Audit Ledger](#6-layer-3-autonomous-triage--cryptographic-audit-ledger)
7. [Layer 4: Continuous MLOps Governance & Drift Protection](#7-layer-4-continuous-mlops-governance--drift-protection)
8. [Layer 5: Flight Cockpit, Sarvam Voice Agent & Edge Serving](#8-layer-5-flight-cockpit-sarvam-voice-agent--edge-serving)
9. [Project Code Map & Component Index](#9-project-code-map--component-index)
10. [Verification & Automated Test Suite (60/60 Tests)](#10-verification--automated-test-suite-6060-tests)

---

## 1. Executive Summary & Case Study Alignment

AeroShield is an industrial predictive maintenance and digital twin platform built to fulfill **Tata Elxsi Case Study 1: Self-Healing Machines**. The system monitors connected fleets of high-bypass turbofans, high-pressure compressors (HPC), and aeroderivative gas turbines.

### Core Objectives Solved:
* **Zero Unplanned Engine Groundings**: Eliminates Aircraft on Ground (AOG) events by detecting mechanical degradation $\approx 45$ cycles before functional failure.
* **Asymmetric Risk Mitigation**: Optimizes predictions against the official NASA exponential scoring metric, severely penalizing delayed maintenance over-predictions ($d > 0$) that risk catastrophic in-flight shutdowns (IFSD).
* **Guaranteed Confidence Bounds**: Quantifies remaining useful life (RUL) uncertainty through calibrated non-parametric **Conformal Prediction ($P_{10}, P_{50}, P_{90}$)** with guaranteed empirical coverage ($84\%–88\%$).
* **Closed-Loop Execution & Compliance**: Replaces ungrounded LLM hallucinations with a deterministic 4-tier decision matrix, human exception routing, and an immutable **SHA-256 cryptographic audit ledger** conforming to FAA Part 145 and EASA M.A.306 standards.
* **Continuous Drift Protection**: Scans age-matched Population Stability Index (PSI) drift across flight phases, protecting serving pipelines through a strict 4-condition statistical promotion gate.

---

## 2. NASA C-MAPSS Benchmark Evaluation Matrix

Evaluated across all four benchmark subsets of the NASA Commercial Modular Aero-Propulsion System Simulation (C-MAPSS):

| Metric | FD001 | FD002 | FD003 | FD004 |
| :--- | :---: | :---: | :---: | :---: |
| **Operating Regimes** | Single (Sea Level) | 6 Multi-Altitude/Mach | Single (Sea Level) | 6 Multi-Altitude/Mach |
| **Fault Modes** | HPC Degradation | HPC Degradation | HPC + Fan Degradation | HPC + Fan Degradation |
| **Fleet Test Engines** | 100 units | 259 units | 100 units | 248 units |
| **Capped Test RMSE** | **11.30 cycles** | **13.97 cycles** | **11.23 cycles** | **14.85 cycles** |
| **NASA Asymmetric Loss** | **2,779** | **14,520** | **2,680** | **16,840** |
| **Conformal Coverage (80% Target)** | **84.0%** | **88.4%** | **86.0%** | **87.5%** |
| **Anomaly Detection Rate** | **100.0%** | **100.0%** | **100.0%** | **100.0%** |
| **False Alarm Rate (FAR)** | **4.0%** | **5.0%** | **3.5%** | **4.8%** |
| **Mean Warning Lead Time** | **38 cycles** | **43 cycles** | **40 cycles** | **46 cycles** |

---

## 3. Five-Layer System Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│             NASA C-MAPSS Telemetry Ingress (FD001–FD004)               │
│         (21 Sensors, 3 Operational Settings, Multi-Flight Regimes)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Deterministic Data Engineering                                │
│ • Causal Running Median Noise Filter (W=5, zero lookahead bias)        │
│ • Gas-Path Interaction Ratios: s8/s9, s13/s14, s11/s7, s4/s3           │
│ • 6-Regime Operating Envelope Clustering (K-Means on Settings)         │
│ • Robust Winsorizing & Exponential Smoothing (EWMA alpha=0.10)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Machine Learning & Conformal Uncertainty Quantification       │
│ • Baseline-Subtracted Anomaly Detection (100% Detection, <=5% FAR)     │
│ • Quantile HistGradientBoosting Estimator (P10, P50, P90)              │
│ • Non-Linear Secondary Consensus Estimator (Prevents false divergence) │
│ • Non-Parametric Conformal Prediction (80% Empirical Coverage Gate)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Autonomous Triage & Regulatory Audit Ledger                   │
│ • Deterministic 4-Tier Operational Decision Matrix (Critical to Normal)│
│ • Human Review Queue for Sensor Faults & Model Disagreements           │
│ • SQLite Work Order State Machine (DRAFT -> DISPATCHED -> COMPLETED)   │
│ • Tamper-Evident SHA-256 Cryptographic Chain (FAA/EASA Part 145)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 4: Continuous MLOps Governance & Model Registry                  │
│ • Age-Matched Population Stability Index (PSI) (0-40, 40-80, 80-140, 140+)│
│ • 4-Gate Champion/Challenger Production Promotion Policy               │
│ • Drift-Adaptive Robust Preprocessor Normalization                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 5: Operational Defense Telemetry Cockpit & Edge Serving          │
│ • FastAPI Async REST Backend & Vercel Serverless Edge Integration      │
│ • Interactive Avionics Flight Cycle Scrubber & 60fps Replay            │
│ • Sarvam AI Voice Copilot (sarvam-105b-conversations + Bulbul v3 TTS)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Layer 1: Deterministic Ingress & Aerodynamic Feature Engineering

**Source Code**: [`shield/src/smoother.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/smoother.py), [`shield/src/data.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/data.py), [`shield/src/features.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/features.py)

### 1. Causal Running Median Smoothing
Turbofan gas-path sensor streams exhibit significant high-frequency noise caused by aerodynamic turbulence and instrument vibration. Standard two-sided filters introduce lookahead bias (data leakage). AeroShield applies a strictly causal running median filter over window $W=5$:
$$\tilde{x}_t = \text{Median}(x_{t-W+1}, x_{t-W+2}, \dots, x_t)$$
This eliminates sensor spikes without leaking future flight degradation states.

### 2. Aerodynamic Gas-Path Thermodynamic Ratios
To capture mechanical and aerodynamic component efficiency regardless of environmental throttling, four domain-specific gas-path interaction ratios are synthesized:
1. **Fan-to-Core Speed Ratio**:
   $$\text{Ratio}_{s_8/s_9} = \frac{s_8 \text{ (Physical Fan Speed)}}{s_9 \text{ (Physical Core Speed)}}$$
2. **Corrected Speed Ratio**:
   $$\text{Ratio}_{s_{13}/s_{14}} = \frac{s_{13} \text{ (Corrected Fan Speed)}}{s_{14} \text{ (Corrected Core Speed)}}$$
3. **Compressor Static-to-Total Pressure Ratio**:
   $$\text{Ratio}_{s_{11}/s_7} = \frac{s_{11} \text{ (HPC Outlet Static Pressure)}}{s_7 \text{ (HPC Outlet Total Pressure)}}$$
4. **Turbine Temperature Ratio**:
   $$\text{Ratio}_{s_4/s_3} = \frac{s_4 \text{ (LPT Outlet Temperature)}}{s_3 \text{ (HPC Outlet Temperature)}}$$

### 3. Operating Regime Clustering
In FD002 and FD004, turbofans traverse 6 distinct flight conditions across altitude ($0–40,000$ ft), Mach number ($0.0–0.84$), and throttle resolver angle ($20–100^{\circ}$). A K-Means model ($K=6$) segments these regimes, allowing the system to compute regime-specific baseline statistics.

---

## 5. Layer 2: ML Inference, Conformal Uncertainty & Anomaly Detection

**Source Code**: [`shield/src/anomaly.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/anomaly.py), [`shield/src/calibrate.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/calibrate.py)

### 1. Baseline-Subtracted Sensor Anomaly Detection
* **The Root Problem**: In raw rolling mean features, flight regime transitions look identical to degradation. As a consequence, anomaly detection on FD002/FD004 historically achieved $<6\%$ true detection.
* **The Solution**: AeroShield computes baseline-subtracted sensor deviations ($d_{\text{base}}$) relative to each unit's initial healthy cruise baseline ($t \le 20$ cycles):
  $$d_{\text{base}}(s_{j, t}) = \frac{s_{j, t} - \mu_{j, \text{healthy}}}{\sigma_{j, \text{healthy}}}$$
  An anomaly is confirmed when the composite Mahalanobis deviation exceeds threshold $\tau = 3.0$ across consecutive cycles. This elevated true detection to **100.0%** while maintaining false alarms $\le 5.0\%$.

### 2. Piecewise Linear Target & Quantile Pinball Loss
Degradation in turbofans is negligible during initial operational cycles. Thus, Remaining Useful Life (RUL) is modeled as a piecewise constant capped target ($RUL_{\text{cap}} = 125$ cycles):
$$y_t = \min(RUL_t, 125)$$
Primary inference utilizes `HistGradientBoostingRegressor` trained with pinball loss at quantiles $\alpha \in \{0.10, 0.50, 0.90\}$:
$$L_\alpha(y, \hat{y}) = \max(\alpha(y - \hat{y}), (1 - \alpha)(\hat{y} - y))$$

### 3. Non-Linear Secondary Model Consensus
To ensure model robustness, a secondary independent non-linear estimator (`RandomForestRegressor` / `GradientBoosting`) provides a second opinion. If the primary and secondary models diverge by more than 25 cycles:
$$|\hat{y}_{\text{primary}} - \hat{y}_{\text{secondary}}| > 25$$
the prediction is flagged as a model disagreement exception and routed to the Human Specialist Queue.

### 4. Non-Parametric Conformal Prediction
To provide mathematically rigorous safety bounds without Gaussian normality assumptions, conformal prediction computes non-conformity scores on held-out calibration engines:
$$E_i = \max(q_{0.1}(x_i) - y_i, \, y_i - q_{0.9}(x_i))$$
Using the finite-sample empirical $(1 - \alpha)$-quantile $\hat{q}$, calibrated prediction bands are constructed:
$$C(x_{\text{test}}) = [q_{0.1}(x_{\text{test}}) - \hat{q}, \;\; q_{0.9}(x_{\text{test}}) + \hat{q}]$$
Across all four datasets, validated empirical coverage achieves $84.0\%–88.4\%$, safely surpassing the $75.0\%$ lower gate bound.

### 5. NASA Asymmetric Loss Formulation
$$S = \sum_{i=1}^N s_i \quad \text{where} \quad s_i = \begin{cases} 
\exp\left(-\frac{d_i}{13}\right) - 1 & \text{for } d_i < 0 \quad (\text{Early Prediction}) \\[6pt]
\exp\left(\frac{d_i}{10}\right) - 1 & \text{for } d_i \ge 0 \quad (\text{Late Prediction})
\end{cases}$$
where $d_i = \hat{y}_i - y_i$. Late over-prediction is exponentially penalized with base $1/10$.

---

## 6. Layer 3: Autonomous Triage & Cryptographic Audit Ledger

**Source Code**: [`shield/src/agent_rules.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/agent_rules.py), [`shield/src/orders.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/orders.py), [`shield/src/exceptions.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/exceptions.py), [`shield/src/audit_chain.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/audit_chain.py)

### 1. Deterministic 4-Tier Severity Matrix
Rather than relying on non-deterministic LLMs for physical dispatch, triage decisions execute via a deterministic rule matrix:
* **Tier 1 (CRITICAL — $P_{50} \le 25$ cycles)**: Immediate AOG grounding, emergency shop visit authorization.
* **Tier 2 (HIGH — $P_{50} \le 50$ cycles)**: Priority depot slot booking, spares allocation (HPC blisk, LPT blades).
* **Tier 3 (MEDIUM — $P_{50} \le 80$ cycles OR Anomaly Active + $P_{50} \le 100$)**: Turnaround borescope inspection scheduled within maintenance budget guardrails (max 10 work orders per window).
* **Tier 4 (NORMAL — $P_{50} > 80$ cycles)**: Unit cleared for flight operations envelope.

### 2. Human Exception Review Queue
The autonomous engine isolates edge cases and routes them to human reliability engineers:
* **Sensor Quality Spike**: Any raw sensor deviating beyond $|z| > 4.5\sigma$.
* **Model Disagreement**: Divergence between primary quantile and secondary non-linear model $> 25$ cycles.
Work orders remain in status `NEEDS_HUMAN` until a certified technician records an authorized override.

### 3. FAA Part 145 & EASA M.A.306 Cryptographic Audit Ledger
Every state transition (`DRAFT` $\to$ `DISPATCHED` $\to$ `COMPLETED`) appends a cryptographically sealed block to an immutable SHA-256 chain:
$$\text{Hash}_i = \text{SHA256}(\text{EntryID} \parallel \text{PrevHash} \parallel \text{Timestamp} \parallel \text{OrderID} \parallel \text{Action} \parallel \text{Operator})$$
Chain integrity is verifiable in $\mathcal{O}(N)$ sub-second time via `/api/audit-verify`. Any bit-level modification to historical maintenance records breaks the parent digest continuum and triggers immediate integrity alerts.

---

## 7. Layer 4: Continuous MLOps Governance & Drift Protection

**Source Code**: [`shield/src/mlops.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/mlops.py), [`shield/src/retrain_demo.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/shield/src/retrain_demo.py)

### 1. Age-Matched Population Stability Index (PSI)
Standard drift detection confounds natural wear degradation with operational covariate shift. AeroShield partitions the flight cycle timeline into 4 distinct age stages:
1. **Stage 1**: $[0, 40]$ cycles (Break-in baseline)
2. **Stage 2**: $[40, 80]$ cycles (Nominal cruise)
3. **Stage 3**: $[80, 140]$ cycles (Accelerated degradation)
4. **Stage 4**: $\ge 140$ cycles (Depot wear boundary)

For sensor $j$ across 10 baseline quantile bins $P$ and incoming batch distribution $Q$:
$$\text{PSI}_j = \sum_{k=1}^{10} (q_k - p_k) \times \ln\left(\frac{q_k + \epsilon}{p_k + \epsilon}\right)$$
* $\text{PSI} < 0.10$: Distribution Stable.
* $0.10 \le \text{PSI} \le 0.20$: Moderate Drift (Telemetry warning).
* $\text{PSI} > 0.20$: Significant Drift (Triggers automated preprocessor adaptation and retraining).

### 2. 4-Gate Champion/Challenger Promotion Policy
Challenger models trained on drifted incoming telemetry must pass four non-negotiable invariant checks before promotion to production serving:
1. **RMSE Parity**: $RMSE_{\text{challenger}} \le RMSE_{\text{champion}}$ (Zero-degradation SLA).
2. **NASA Loss Constraint**: $Loss_{\text{challenger}} \le 1.05 \times Loss_{\text{champion}}$ ($\le +5.0\%$ rise).
3. **Conformal Coverage Lower Bound**: $\text{Coverage}_{\text{challenger}} \ge 75.0\%$ (1-sided safety boundary).
4. **Late Over-Prediction Gate**: $\Delta \text{LateShare} \le +5.0$ percentage points over active champion.
If any condition fails, the challenger is retained in staging (`gated=true`) and the active champion remains in production.

---

## 8. Layer 5: Flight Cockpit, Sarvam Voice Agent & Edge Serving

**Source Code**: [`platform/backend/main.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/platform/backend/main.py), [`platform/backend/voice_agent.py`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/platform/backend/voice_agent.py), [`platform/frontend/dashboard.html`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/platform/frontend/dashboard.html), [`public/index.html`](file:///c:/Users/Asus/Desktop/Misc%20_Projects/DUMB%20SENIOR%20PROJECT/AeroShield-Predictive-Fleet-Maintenance/public/index.html)

### 1. Interactive Flight Telemetry Cockpit
* **Tactile Glassmorphism**: High-contrast, anti-slop defense avionics styling with Plus Jakarta Sans and monospace tabular numerals.
* **60fps Time-Travel Scrubber**: Smooth replay slider allowing flight controllers to scrub back to any historical cycle and inspect sensor deviations at the exact degradation inflection knee.
* **Glow Conformal Prediction Envelope**: Visualizes $P_{10}$–$P_{90}$ uncertainty bands with gradient fills and live crosshairs.

### 2. Sarvam AI Conversational Voice Copilot
* **Reasoning Agent (`sarvam-105b-conversations`)**: Grounded in live fleet telemetry. When asked a question, it queries active fleet readiness, single-engine RUL quantiles, and open work orders to produce concise (2–3 sentence), tactical briefings.
* **Neural Speech Synthesis (`bulbul:v3`)**: Generates studio-grade WAV audio in $\approx 250$ms across 4 distinct voice personas:
  * **Shubh**: Lead Tactical Commander (Authoritative default).
  * **Priya**: Avionics Systems Officer (Tactical operational clarity).
  * **Aditya**: Chief Fleet Engineer (Technical analysis).
  * **Neha**: Flight Controller (Clear monitoring alerts).
* **Live Speech-to-Text**: Web Speech API microphone integration allows hands-free voice queries in the cockpit.

### 3. Serverless Edge Deployment (Vercel)
* Optimized dependency architecture: Lean runtime dependencies (`fastapi`, `pydantic`, `pandas`, `pyarrow`) packaged under $341$ MB (well below Vercel's $500$ MB Lambda limit).
* ASGI rewrite middleware (`api/index.py`) ensuring clean subpath routing on edge serverless functions.
* Live deployment: [https://aeroshield-phi.vercel.app](https://aeroshield-phi.vercel.app).

---

## 9. Project Code Map & Component Index

```
AeroShield-Predictive-Fleet-Maintenance/
├── README.md                          # Concise executive README with live demo badges
├── LICENSE                            # MIT License
├── pytest.ini                         # Test runner configuration (60 automated tests)
├── requirements.txt                   # Lean production runtime dependencies (<350 MB)
├── requirements-dev.txt               # Development & training dependencies (mlflow, scikit-learn)
├── vercel.json                        # Vercel serverless edge routing & Python 3.12 runtime
│
├── api/
│   └── index.py                       # Vercel ASGI rewrite middleware & serverless handler
│
├── data/                              # NASA C-MAPSS Turbofan Benchmark Datasets
│   ├── train_FD001.txt .. FD004.txt   # Run-to-failure degradation trajectories
│   ├── test_FD001.txt .. FD004.txt    # Operational test trajectories
│   ├── RUL_FD001.txt .. FD004.txt     # True end-of-test Remaining Useful Life labels
│   └── readme.txt                     # Official NASA C-MAPSS dataset documentation
│
├── shield/                            # Core Algorithmic & MLOps Engine
│   ├── config/
│   │   └── thresholds.yaml            # Operational bounds, SLA limits, and regime parameters
│   ├── src/
│   │   ├── smoother.py                # Layer 1: Causal running median noise filter
│   │   ├── data.py                    # Layer 1: C-MAPSS ingress & regime clustering
│   │   ├── features.py                # Layer 1: Gas-path interaction ratios & EWMA
│   │   ├── anomaly.py                 # Layer 2: Baseline-subtracted sensor anomaly detector
│   │   ├── calibrate.py               # Layer 2: Conformal prediction & non-linear consensus
│   │   ├── agent_rules.py             # Layer 3: Deterministic 4-tier triage matrix
│   │   ├── orders.py                  # Layer 3: SQLite work order lifecycle state machine
│   │   ├── exceptions.py              # Layer 3: Sensor spike & model divergence review queue
│   │   ├── audit_chain.py             # Layer 3: SHA-256 tamper-evident cryptographic ledger
│   │   ├── mlops.py                   # Layer 4: Age-matched PSI profiler & 4-condition gate
│   │   └── retrain_demo.py            # Layer 4: Drift-adaptive preprocessor retraining demo
│   └── tests/                         # Core unit test suite (47 tests)
│
├── platform/                          # Interactive Flight Telemetry Cockpit
│   ├── backend/
│   │   ├── main.py                    # FastAPI REST API endpoints
│   │   ├── data_bridge.py             # High-throughput data bridge connecting models & SQLite
│   │   └── voice_agent.py             # Sarvam AI Voice Copilot & Bulbul neural TTS engine
│   ├── frontend/
│   │   └── dashboard.html             # Tactical cockpit UI (FAA Part 145 compliance ledger)
│   ├── run_platform.py                # Local standalone platform launcher (Port 8050)
│   └── test_platform.py               # Platform integration test suite (13 tests)
│
├── public/
│   └── index.html                     # Vercel edge frontend asset (synchronized with dashboard)
│
├── outputs/                           # Precomputed Benchmark Weights & Telemetry Parquets
│   ├── registry.json                  # Production model registry metadata
│   ├── benchmark_summary.csv          # Quantitative metrics across FD001-FD004
│   └── FD001/ .. FD004/               # Calibrated joblib weights, parquets, SQLite databases
│
└── docs/                              # Technical Specifications & Formulations
    ├── Case_Study_1_Requirements.md   # Exact Tata Elxsi problem brief
    ├── ARCHITECTURE.md                # System topology and component flow
    ├── MATHEMATICAL_FORMULATION.md    # Formulations for NASA Loss, Conformal Bounds & PSI
    └── MODEL_AND_SYSTEM_DOCUMENTATION.md # Comprehensive master technical reference (this doc)
```

---

## 10. Verification & Automated Test Suite (60/60 Tests)

All algorithms, models, and platform endpoints are covered by automated unit and integration tests:

```bash
pytest -v
```

### Test Coverage Breakdown:
* **`shield/tests/test_agent_rules.py` (6 tests)**: Verifies all 4 tiers of the deterministic triage matrix and budget limits.
* **`shield/tests/test_audit_chain.py` (3 tests)**: Verifies SHA-256 cryptographic parent-hash linkage and detects simulated block tampering.
* **`shield/tests/test_calibration.py` (5 tests)**: Verifies conformal quantile bounds, non-conformity scores, and coverage guarantees.
* **`shield/tests/test_exceptions.py` (10 tests)**: Validates sensor spike isolation ($z > 4.5$) and model divergence exceptions ($|\Delta| > 25$).
* **`shield/tests/test_features_parity.py` (3 tests)**: Verifies gas-path interaction ratios and causal median smoothing.
* **`shield/tests/test_improvements.py` (7 tests)**: Verifies anomaly detection rate ($>80\%$) and non-linear secondary opinion consensus.
* **`shield/tests/test_orders_lifecycle.py` (5 tests)**: Verifies SQLite state transitions (`DRAFT` $\to$ `DISPATCHED` $\to$ `COMPLETED`).
* **`shield/tests/test_schema.py` (4 tests)**: Verifies data ingress schema validation and missing-value rejection.
* **`shield/tests/test_smoother.py` (4 tests)**: Verifies zero lookahead bias and causal median filter properties.
* **`platform/test_platform.py` (13 tests)**:
  - `test_dashboard_endpoint`: Validates tactical HTML serving.
  - `test_api_subsets`: Validates C-MAPSS subset ingress (`FD001`–`FD004`).
  - `test_api_fleet_readiness`: Validates fleet health KPIs and conformal metrics.
  - `test_api_fleet_matrix`: Validates high-density fleet matrix with quantiles.
  - `test_api_engine_drilldown`: Validates cycle trajectories and aerodynamic ratios.
  - `test_api_work_orders`: Validates active work order retrieval.
  - `test_api_exceptions`: Validates human specialist queue.
  - `test_api_audit_log_and_verify`: Validates live SHA-256 chain verification.
  - `test_api_mlops`: Validates PSI drift thresholds and champion metrics.
  - `test_api_dispatch_work_order`: Validates status updates and blockchain block appending.
  - `test_api_voice_status`: Validates Sarvam AI engine connectivity and speaker personas.
  - `test_api_voice_synthesize`: Validates Sarvam Bulbul neural speech synthesis.
  - `test_api_voice_copilot`: Validates grounded Sarvam 105B conversational reasoning.

**Result**: `60 passed in 17.83s (100% Green)`.
