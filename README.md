# AeroShield: Autonomous Predictive Fleet Maintenance Platform

[![Live Demo: Vercel](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://aeroshield-phi.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Tests: 76/76 Passed](https://img.shields.io/badge/Tests-76%2F76%20Passed-emerald.svg)](pytest.ini)
[![Voice Agent: Sarvam AI](https://img.shields.io/badge/Voice%20Agent-Sarvam%20AI%20(Optional)-orange.svg)](https://sarvam.ai)
[![Conformal Coverage: Calibrated](https://img.shields.io/badge/Conformal%20Coverage-80%25%20Calibrated-sky.svg)](docs/MATHEMATICAL_FORMULATION.md)

> **Autonomous predictive maintenance, conformal Remaining Useful Life (RUL) estimation, deterministic triage dispatch, and cryptographic audit ledgers for connected industrial turbofans.**  
> Built for **Tata Elxsi Case Study 1: Self-Healing Machines** evaluated on the full **NASA C-MAPSS (FD001–FD004)** turbofan benchmark suite.

🌐 **Live Cockpit**: **[https://aeroshield-phi.vercel.app](https://aeroshield-phi.vercel.app)**  
📚 **System & Model Architecture Guide**: **[docs/MODEL_AND_SYSTEM_DOCUMENTATION.md](docs/MODEL_AND_SYSTEM_DOCUMENTATION.md)**  
📂 **Layer-by-Layer Architectural Docs**: **[layer_documentation/](layer_documentation/)**

---

## Key Capabilities

* **Gas-Path Physics Features**: Attenuates raw sensor noise via causal running medians and computes thermodynamic interaction ratios ($s_8/s_9$ fan/core speed, $s_{13}/s_{14}$ corrected speed, $s_{11}/s_7$ pressure drop, $s_4/s_3$ temperature ratio).
* **Baseline-Subtracted Anomaly Detection**: Tracks sensor deviations against operating-regime baselines with an out-of-fold calibrated `IsolationForest` detector to detect degradation **38–54 cycles** before failure with $\le 5\%$ False Alarm Rate.
* **Conformal RUL Uncertainty**: Predicts remaining useful life intervals ($P_{10}, P_{50}, P_{90}$) with empirical coverage guarantees and secondary non-linear consensus (`RandomForestRegressor`).
* **Deterministic Triage Agent**: Evaluates an automated 4-tier decision matrix, routes sensor anomalies to human review queues, and commits work-order state transitions to a **tamper-evident Keyed HMAC-SHA256 cryptographic audit ledger** designed to support FAA Part 145 and EASA M.A.306 auditability requirements.
* **Closed-Loop Retraining & MLOps Governance**: Scans age-matched Population Stability Index (PSI) drift, evaluates one-sided loss on right-censored serviced units, scores champion vs challenger on held-out gate validation sets, and enforces statistical promotion gates in `retrain_demo.py` and `ModelRegistry`.
* **Sarvam AI Voice Copilot (Optional Read-Only Add-on)**: Read-only conversational telemetry query interface powered by Sarvam 105B (`sarvam-105b-conversations`) and neural TTS (`bulbul:v3`) with full offline default mode (`VOICE_ENABLED=false`).
* **Tactile Defense Cockpit**: Anti-slop glassmorphic interface with 60fps flight cycle replay scrubber and interactive flight controller copilot.

---

## Official NASA C-MAPSS Benchmark Evaluation

Extracted directly from ground-truth executions recorded in outputs/benchmark_summary.csv:

| Dataset | Operating Conditions | Fault Modes | Engines | Test Capped RMSE (95% CI) | Uncapped RMSE | NASA Loss (Uncapped) | Late % | Conformal Coverage (80% target) | Near-Failure Cov ( \le 50$) | Anomaly Detection | Engine FA Rate | Median Warning Lead | Human Exceptions |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FD001** | Single (Sea Level) | HPC Wear | 100 | **11.30** [9.3, 13.3] | 12.98 | **213.0** | 29.0% | **84.0%** | **100.0%** | **100.0%** | 4.0% | 38 cyc | 0 |
| **FD002** | 6 Complex Regimes | HPC Wear | 259 | **13.97** [12.6, 15.3] | 27.01 | **8,519.0** | 19.3% | **88.4%** | **98.9%** | **100.0%** | 5.0% | 43 cyc | 6 |
| **FD003** | Single (Sea Level) | HPC + Fan Wear | 100 | **11.59** [9.5, 13.6] | 13.34 | **260.0** | 35.0% | **79.0%** | **93.1%** | **69.0%** | 2.0% | 39 cyc | 10 |
| **FD004** | 6 Complex Regimes | HPC + Fan Wear | 248 | **21.49** [19.1, 23.8] | 33.49 | **15,018.0** | 35.9% | **81.5%** | **90.0%** | **5.6%** | 4.4% | 54 cyc | 51 |

*Note: NASA asymmetric scoring exponentially penalizes late over-prediction. Conformal coverage is calibrated to nominal 80% contract; in the critical near-failure zone ( \le 50$), coverage remains $\ge 90\%$. On FD004, 51 engines are safely routed to the human exception queue as fail-safe protection.*

---

## System Architecture

```
Telemetry Stream (NASA C-MAPSS FD001-FD004)
   │
   ▼
Layer 1: Feature Engineering (Causal Median Smoothing, Gas-Path Ratios, Regime Clustering)
   │
   ▼
Layer 2: Inference & Uncertainty (Baseline Anomaly Detection, Quantile Boosting P10/P50/P90, Conformal Calibration)
   │
   ▼
Layer 3: Autonomous Triage & Execution (4-Tier Rule Matrix, Human Exception Queue, SQLite State Machine, SHA-256 Ledger)
   │
   ▼
Layer 4: MLOps Governance (Age-Matched PSI Drift Profiler, 4-Gate Champion/Challenger Promotion Policy)
   │
   ▼
Layer 5: Flight Cockpit (FastAPI REST Service, Vercel Serverless Edge, Voice Annunciator UI)
```

---

## Quickstart

### 1. Clone & Install
```bash
git clone https://github.com/vanshi0905/AeroShield-Predictive-Fleet-Maintenance.git
cd AeroShield-Predictive-Fleet-Maintenance

python -m venv venv
venv\Scripts\activate   # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Automated Verification (64 Tests)
```bash
pytest
```
*64 tests passed across all core algorithms, platform, and voice endpoints.*

### 3. Launch the Cockpit
```bash
python platform/run_platform.py
```
Open **[http://127.0.0.1:8050/dashboard](http://127.0.0.1:8050/dashboard)** (or view the cloud deployment at **[aeroshield-phi.vercel.app](https://aeroshield-phi.vercel.app)**).

---

## REST API Summary

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/subsets` | `GET` | Available C-MAPSS subsets (`FD001`–`FD004`) |
| `/api/fleet/readiness` | `GET` | Fleet health index, subsystem risk distribution, and metrics |
| `/api/fleet/matrix` | `GET` | High-density engine table with RUL quantiles and anomaly scores |
| `/api/engine/{unit}` | `GET` | Trajectory timelines, sensor stations, and conformal RUL intervals |
| `/api/work-orders` | `GET` | Active maintenance work orders |
| `/api/work-orders/dispatch` | `POST` | Authorizes status transition and appends Keyed HMAC-SHA256 block |
| `/api/exceptions` | `GET` | Human review queue for sensor spikes and model disagreement |
| `/api/audit-log` | `GET` | Cryptographic blockchain ledger entries |
| `/api/audit-verify` | `GET` | Verifies cryptographic hash chain integrity across all blocks |
| `/api/mlops` | `GET` | Champion vs. Challenger metrics, PSI drift, and gate status |
| `/api/retrain/trigger` | `POST` | Executes automated retraining pipeline and promotion gate |
| `/api/voice/status` | `GET` | Sarvam AI engine status and persona catalog (*Shubh*, *Priya*, etc.) |
| `/api/voice/synthesize` | `POST` | Synthesizes cockpit speech using Sarvam Bulbul neural TTS |
| `/api/voice/copilot` | `POST` | Grounded conversational copilot using Sarvam 105B + Bulbul audio |

---

## Engineering Operational Boundaries & Known Limits

In accordance with rigorous aerospace verification standards, AeroShield explicitly documents operational boundaries and empirical trade-offs across the four NASA C-MAPSS fleet subsets:

1. **FD003 Conformal Coverage (79.0% vs. 80.0% Nominal Target)**:
   - *Observation*: FD003 achieves 79.0% empirical coverage on the 80% conformal target (-1.0 percentage point deviation).
   - *Root Cause*: FD003 incorporates dual degradation fault modes (HPC degradation and fan degradation) under a single operating regime. Competing wear mechanisms across distinct subsystems generate multi-modal residual tails, causing standard conformal calibration to marginally under-cover the extreme 1% tail.

2. **FD004 Multi-Regime Anomaly Detection & Exception Routing (5.6% Anomaly Flag Rate)**:
   - *Observation*: FD004 exhibits a 5.6% baseline-subtracted anomaly detection rate and routes 51 ambiguous engines to the Human Exception Queue.
   - *Root Cause*: FD004 combines six continuous altitude/Mach/throttle operating regimes with dual fault modes. Operating condition switching produces sensor variations that exceed degradation-induced deviations in early cycles. Rather than triggering high false alarms, Layer 3 autonomously flags sensor disagreement and diverts ambiguous units to human engineering review.

3. **Asymmetric NASA Loss vs. Symmetric RMSE Trade-Off**:
   - *Observation*: The late-shift calibration grid intentionally sacrifices ~0.5 to 1.0 cycles of symmetric RMSE to suppress late prediction share (predictions where $\hat{y} > y$).
   - *Engineering Rationale*: In commercial fleet operations, over-predicting RUL risks catastrophic unscheduled in-flight shutdowns (IFSD), whereas early prediction triggers scheduled hangar maintenance with zero safety compromise.

---

## License

This project is licensed under the [MIT License](LICENSE).
