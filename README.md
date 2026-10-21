# AeroShield: Autonomous Predictive Fleet Maintenance Platform

[![Live Demo: Vercel](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://aeroshield-phi.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Tests: 78/78 Passed](https://img.shields.io/badge/Tests-78%2F78%20Passed-emerald.svg)](pytest.ini)

[![Conformal Coverage: Calibrated](https://img.shields.io/badge/Conformal%20Coverage-80%25%20Calibrated-sky.svg)](docs/MATHEMATICAL_FORMULATION.md)

> **Predictive maintenance on NASA C-MAPSS: features, a remaining-useful-life model, a rule-based triage agent, a work order, and a retrain demo.**  
> Built for **Tata Elxsi Case Study 1: Self-Healing Machines**, on **FD001–FD004**.

The graded path is Layers 1–4. The triage agent is a deterministic threshold matrix in plain Python without external language model dependencies.

🌐 **Live Cockpit**: **[https://aeroshield-phi.vercel.app](https://aeroshield-phi.vercel.app)**  
📚 **System & Model Architecture Guide**: **[docs/MODEL_AND_SYSTEM_DOCUMENTATION.md](docs/MODEL_AND_SYSTEM_DOCUMENTATION.md)**  
📂 **Layer-by-Layer Architectural Docs**: **[layer_documentation/](layer_documentation/)**

---

## Key Capabilities

* **Gas-Path Physics Features**: Attenuates raw sensor noise via causal running medians and computes thermodynamic interaction ratios ($s_8/s_9$ fan/core speed, $s_{13}/s_{14}$ corrected speed, $s_{11}/s_7$ pressure drop, $s_4/s_3$ temperature ratio).
* **Baseline-Subtracted Anomaly Detection**: Tracks sensor deviations against operating-regime baselines with an out-of-fold calibrated `IsolationForest`. On the training folds the median warning is 38–54 cycles at about a 2–5% engine false-alarm rate. On the held-out test engines the same detector flags 29%, 38%, 19%, and 2% of FD001–FD004. Those two numbers are not interchangeable.
* **Conformal RUL Uncertainty**: Predicts remaining useful life intervals ($P_{10}, P_{50}, P_{90}$) with empirical coverage guarantees and secondary non-linear consensus (`RandomForestRegressor`).
* **Deterministic Triage Agent**: A 4-tier rule matrix writes a work order or sends the unit to a human queue. Each change is appended to an HMAC-SHA256 hash chain. The sample databases in `outputs/` were sealed with a key that is published in this repo, so the chain shows whether a demo file was edited. It is not an FAA Part 145 or EASA M.A.306 record, and it is not tamper-proof against someone who has that key.
* **Closed-Loop Retraining & MLOps Governance**: Scans age-matched Population Stability Index (PSI) drift, evaluates one-sided loss on right-censored serviced units, scores champion vs challenger on held-out gate validation sets, and enforces statistical promotion gates in `retrain_demo.py` and `ModelRegistry`.

* **Tactile Defense Cockpit**: Anti-slop glassmorphic interface with 60fps flight cycle replay scrubber and interactive flight controller copilot.

---

## Scores

Two different checks were previously printed in one table. They are split here. Both come from `outputs/benchmark_summary.csv` and `outputs/FD00x/metrics.json`.

RUL columns are the last cycle of each test engine. Capped RMSE compares the prediction with the RUL clipped at 125. Uncapped RMSE compares it with the raw truth. NASA score uses the uncapped truth and penalizes late predictions more than early ones.

| Dataset | Conditions | Faults | Engines | Capped RMSE (95% CI) | Uncapped RMSE | NASA score (uncapped) | Late % | Coverage (80% target) | Coverage when RUL ≤ 50 | Human exceptions |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| FD001 | 1 regime | HPC | 100 | 11.30 [9.3, 13.3] | 12.98 | 213 | 29% | 84% | 100% | 0 |
| FD002 | 6 regimes | HPC | 259 | 13.97 [12.6, 15.3] | 27.01 | 8,519 | 19% | 88% | 99% | 6 |
| FD003 | 1 regime | HPC + fan | 100 | 11.59 [9.5, 13.6] | 13.34 | 260 | 35% | 79% | 93% | 10 |
| FD004 | 6 regimes | HPC + fan | 248 | 21.49 [19.1, 23.8] | 33.49 | 15,018 | 36% | 81% | 90% | 51 |

Anomaly numbers below are not from that same test cut.

Out-of-fold, on the training engines:

| Dataset | Engines flagged | Engine false-alarm rate | Median lead (cycles) |
| :--- | :---: | :---: | :---: |
| FD001 | 100% | 4% | 38 |
| FD002 | 100% | 5% | 43 |
| FD003 | 69% | 2% | 39 |
| FD004 | 5.6% | 4.4% | 54 |

On the test engines (`anomaly_test` in each `metrics.json`):

| Dataset | Engines flagged | Engine false-alarm rate | Median lead (cycles) | Flagged / engines |
| :--- | :---: | :---: | :---: | :---: |
| FD001 | 29% | 2% | 42 | 29 / 100 |
| FD002 | 38% | 2% | 50 | 98 / 259 |
| FD003 | 19% | 1% | 45 | 19 / 100 |
| FD004 | 1.6% | 5.6% | 76 | 4 / 248 |

FD003 coverage is 79% against an 80% target. FD004 sends 51 engines to the human queue. The late-shift calibration gives up a little RMSE to cut late predictions. The NASA score is the one to read when early and late errors should not count the same.

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
Layer 5: Flight Cockpit (FastAPI REST Service, Vercel Serverless Edge, Dark Avionics Cockpit)
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

### 2. Run the tests
```bash
pytest
```
78 tests cover the pipeline, the platform, and the rule that the published development key cannot dispatch.

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
| `/api/work-orders/dispatch` | `POST` | Status change. Needs a private `X-API-Key`. Closed if the key is missing or is the old published value. |
| `/api/exceptions` | `GET` | Human review queue for sensor spikes and model disagreement |
| `/api/audit-log` | `GET` | Cryptographic blockchain ledger entries |
| `/api/audit-verify` | `GET` | Verifies cryptographic hash chain integrity across all blocks |
| `/api/mlops` | `GET` | Champion vs. Challenger metrics, PSI drift, and gate status |
| `/api/retrain/trigger` | `POST` | Retrain demo. Same private key as dispatch. |




---

## Limits

1. FD003 conformal coverage is 79% on an 80% target. Two fault modes under one regime leave a heavier tail than the calibrator covers.
2. FD004's out-of-fold anomaly rate is 5.6%, and the test rate is 1.6%. Fifty-one test engines go to the human queue. Six regimes plus two fault modes make early degradation hard to separate from a regime change.
3. The late-shift knob trades a bit of RMSE for fewer late RUL predictions. Late means the model says the engine has more life than it does.
4. Dispatch and retrain operations stay closed until `AEROSHIELD_API_KEY` is a private value. `aeroshield-dev-key` is rejected in development and in production. The public dashboard does not embed a key.
5. `outputs/*/work_orders.db` verifies with the published demo HMAC key. Production refuses to sign new rows with that key. A private key will not verify those sample files. Copy `.env.example` before expecting the write buttons to work.

---

## License

This project is licensed under the [MIT License](LICENSE).
