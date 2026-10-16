# AeroShield: All-Layers Architectural Documentation Directory

This folder contains the complete, dedicated, layer-by-layer architectural documentation for the **AeroShield Autonomous Predictive Fleet Maintenance Platform** (built for **Tata Elxsi Case Study 1: Self-Healing Machines** on the **NASA C-MAPSS FD001–FD004** benchmark).

---

## Documentation Index

| Document | Layer & System Scope | Key Algorithms & Modules |
| :--- | :--- | :--- |
| **[`LAYER_1_DATA_ENGINEERING.md`](LAYER_1_DATA_ENGINEERING.md)** | **Layer 1: Deterministic Ingress & Feature Engineering** | Causal Running Median ($W=5$), 4 Gas-Path Ratios, K-Means 6-Regime Clustering, MAD Winsorizing |
| **[`LAYER_2_MODEL_AND_INFERENCE.md`](LAYER_2_MODEL_AND_INFERENCE.md)** | **Layer 2: Inference & Uncertainty Quantification** | Baseline Anomaly Detection ($d_{\text{base}}$), Quantile Pinball Loss ($P_{10}, P_{50}, P_{90}$), Non-Linear Consensus, Conformal Prediction, NASA Loss |
| **[`LAYER_3_AUTONOMOUS_TRIAGE.md`](LAYER_3_AUTONOMOUS_TRIAGE.md)** | **Layer 3: Autonomous Triage & Compliance Ledger** | Deterministic 4-Tier Severity Matrix, Human Exception Review Queue, SQLite State Machine, FAA Part 145 / EASA M.A.306 SHA-256 Ledger |
| **[`LAYER_4_MLOPS_AND_GOVERNANCE.md`](LAYER_4_MLOPS_AND_GOVERNANCE.md)** | **Layer 4: Continuous MLOps & Retraining Gate** | Age-Matched PSI Drift Profiler ($0-40, 40-80, 80-140, 140+$), 4-Condition Champion/Challenger Promotion Gate, Preprocessor Adaptation |
| **[`LAYER_5_COCKPIT_AND_VOICE_AGENT.md`](LAYER_5_COCKPIT_AND_VOICE_AGENT.md)** | **Layer 5: Flight Cockpit, Voice Agent & Cloud Edge** | Sarvam AI Copilot (`sarvam-105b-conversations`), Bulbul v3 Neural TTS, 60fps Flight Cycle Replay, Vercel Serverless Edge Deployment |
| **[`FULL_SYSTEM_AND_MODEL_ARCHITECTURE.md`](FULL_SYSTEM_AND_MODEL_ARCHITECTURE.md)** | **Master Architectural Reference** | Consolidated technical reference covering all benchmarks, formulations, and repository file maps |

---

## Benchmark Performance Highlights across NASA C-MAPSS

* **FD001 (Sea Level, HPC Wear)**: Capped RMSE **11.30 cyc** | NASA Loss **2,779** | 80% Conformal Coverage **84.0%** | Anomaly Detection **100.0%**
* **FD002 (6 Regimes, HPC Wear)**: Capped RMSE **13.97 cyc** | NASA Loss **14,520** | 80% Conformal Coverage **88.4%** | Anomaly Detection **100.0%**
* **FD003 (Sea Level, HPC + Fan Wear)**: Capped RMSE **11.23 cyc** | NASA Loss **2,680** | 80% Conformal Coverage **86.0%** | Anomaly Detection **100.0%**
* **FD004 (6 Regimes, HPC + Fan Wear)**: Capped RMSE **14.85 cyc** | NASA Loss **16,840** | 80% Conformal Coverage **87.5%** | Anomaly Detection **100.0%**
