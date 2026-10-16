# AeroShield: Autonomous Predictive Fleet Maintenance Platform

[![Live Demo: Vercel](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://aeroshield-phi.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Tests: 60/60 Passed](https://img.shields.io/badge/Tests-60%2F60%20Passed-emerald.svg)](pytest.ini)
[![Voice Agent: Sarvam AI](https://img.shields.io/badge/Voice%20Agent-Sarvam%20AI-orange.svg)](https://sarvam.ai)
[![Conformal Coverage: 80%](https://img.shields.io/badge/Conformal%20Coverage-80%25%20Calibrated-sky.svg)](docs/MATHEMATICAL_FORMULATION.md)

> **Autonomous predictive maintenance, conformal Remaining Useful Life (RUL) estimation, deterministic triage dispatch, and cryptographic audit ledgers for connected industrial turbofans.**  
> Built for **Tata Elxsi Case Study 1: Self-Healing Machines** evaluated on the full **NASA C-MAPSS (FD001–FD004)** turbofan benchmark suite.

🌐 **Live Cockpit**: **[https://aeroshield-phi.vercel.app](https://aeroshield-phi.vercel.app)**

---

## Key Capabilities

* **Gas-Path Physics Features**: Attenuates raw sensor noise via causal running medians and computes thermodynamic interaction ratios ($s_8/s_9$ fan/core speed, $s_{13}/s_{14}$ corrected speed, $s_{11}/s_7$ pressure drop, $s_4/s_3$ temperature ratio).
* **Baseline-Subtracted Anomaly Detection**: Tracks sensor deviations against operating-regime baselines to detect degradation $\approx 45$ cycles before failure with $\le 5\%$ False Alarm Rate across all 6 flight regimes.
* **Conformal RUL Uncertainty**: Predicts remaining useful life intervals ($P_{10}, P_{50}, P_{90}$) with calibrated empirical coverage guarantees and secondary non-linear consensus.
* **Deterministic Triage Agent**: Evaluates an automated 4-tier decision matrix, routes sensor anomalies to human review queues, and commits work-order state transitions to a **tamper-evident SHA-256 cryptographic audit ledger**.
* **MLOps Drift Governance**: Scans age-matched Population Stability Index (PSI) drift and enforces a 4-condition statistical promotion gate to prevent performance regressions.
* **Sarvam AI Voice Copilot & Neural Annunciator**: Features conversational telemetry reasoning powered by Sarvam 105B (`sarvam-105b-conversations`) with studio-grade neural speech synthesis (`bulbul:v3`) across multiple persona voices (*Shubh*, *Priya*, *Aditya*, *Neha*) and live speech-to-text mic input.
* **Tactile Defense Cockpit**: Anti-slop glassmorphic interface with 60fps flight cycle replay scrubber and interactive flight controller copilot.

---

## NASA C-MAPSS Benchmark Evaluation

Across all four benchmark subsets (single-condition to complex 6-regime multi-fault degradation):

| Dataset | Operating Conditions | Fault Modes | Engines | Test Capped RMSE | NASA Asymmetric Loss | 80% Conformal Coverage | Anomaly Detection Rate | False Alarm Rate | Mean Warning Lead |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FD001** | Single (Sea Level) | HPC Wear | 100 | **11.30** | **2,779** | **84.0%** | **100.0%** | 4.0% | 38 cycles |
| **FD002** | 6 Complex Regimes | HPC Wear | 259 | **13.97** | **14,520** | **88.4%** | **100.0%** | 5.0% | 43 cycles |
| **FD003** | Single (Sea Level) | HPC + Fan Wear | 100 | **11.23** | **2,680** | **86.0%** | **100.0%** | 3.5% | 40 cycles |
| **FD004** | 6 Complex Regimes | HPC + Fan Wear | 248 | **14.85** | **16,840** | **87.5%** | **100.0%** | 4.8% | 46 cycles |

*Evaluated under NASA asymmetric scoring exponentially penalizing late over-prediction.*

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

### 2. Run Automated Verification (60 Tests)
```bash
pytest
```
*60 tests passed across all core algorithms, platform, and Sarvam AI voice endpoints.*

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
| `/api/work-orders/dispatch` | `POST` | Authorizes status transition and appends SHA-256 block |
| `/api/exceptions` | `GET` | Human review queue for sensor spikes and model disagreement |
| `/api/audit-log` | `GET` | Cryptographic blockchain ledger entries |
| `/api/audit-verify` | `GET` | Verifies cryptographic hash chain integrity across all blocks |
| `/api/mlops` | `GET` | Champion vs. Challenger metrics, PSI drift, and gate status |
| `/api/retrain/trigger` | `POST` | Executes automated retraining pipeline and promotion gate |
| `/api/voice/status` | `GET` | Sarvam AI engine status and persona catalog (*Shubh*, *Priya*, etc.) |
| `/api/voice/synthesize` | `POST` | Synthesizes cockpit speech using Sarvam Bulbul neural TTS |
| `/api/voice/copilot` | `POST` | Grounded conversational copilot using Sarvam 105B + Bulbul audio |

---

## License

This project is licensed under the [MIT License](LICENSE).
