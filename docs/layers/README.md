# AeroShield: All-Layers Architectural Documentation Directory

This folder contains the complete, dedicated, layer-by-layer architectural documentation for the **AeroShield Autonomous Predictive Fleet Maintenance Platform** (built for **Tata Elxsi Case Study 1: Self-Healing Machines** on the **NASA C-MAPSS FD001–FD004** benchmark).

---

## Documentation Index

| Document | Layer & System Scope | Key Algorithms & Modules |
| :--- | :--- | :--- |
| **[`LAYER_1_DATA_ENGINEERING.md`](LAYER_1_DATA_ENGINEERING.md)** | **Layer 1: Deterministic Ingress & Feature Engineering** | Causal Running Median ($W=5$), 4 Gas-Path Ratios, K-Means 6-Regime Clustering, MAD Winsorizing |
| **[`LAYER_2_MODEL_AND_INFERENCE.md`](LAYER_2_MODEL_AND_INFERENCE.md)** | **Layer 2: Inference & Uncertainty Quantification** | Baseline Anomaly Detection ($d_{\text{base}}$), Quantile Pinball Loss ($P_{10}, P_{50}, P_{90}$), Non-Linear Consensus, Conformal Prediction, NASA Loss |
| **[`LAYER_3_AUTONOMOUS_TRIAGE.md`](LAYER_3_AUTONOMOUS_TRIAGE.md)** | **Layer 3: Rule triage and demo ledger** | 4-tier rule matrix, human queue, SQLite states, HMAC hash chain with a published demo key |
| **[`LAYER_4_MLOPS_AND_GOVERNANCE.md`](LAYER_4_MLOPS_AND_GOVERNANCE.md)** | **Layer 4: Continuous MLOps & Retraining Gate** | Age-Matched PSI Drift Profiler ($0-40, 40-80, 80-140, 140+$), 4-Condition Champion/Challenger Promotion Gate, Preprocessor Adaptation |
| **[`LAYER_5_COCKPIT_AVIONICS.md`](LAYER_5_COCKPIT_AVIONICS.md)** | **Layer 5: Cockpit** | Tactical flight dashboard and Vercel edge deployment |
| **[`FULL_SYSTEM_AND_MODEL_ARCHITECTURE.md`](FULL_SYSTEM_AND_MODEL_ARCHITECTURE.md)** | **Master Architectural Reference** | Consolidated technical reference covering all benchmarks, formulations, and repository file maps |

---

## Benchmark Performance Highlights across NASA C-MAPSS

For the single source of truth across all four C-MAPSS subsets (FD001–FD004), refer directly to the verified benchmark tables in the [Root README](../../README.md#benchmark-results-nasa-c-mapss) and [`outputs/benchmark_summary.csv`](../../outputs/benchmark_summary.csv), which are programmatically derived and verified straight from `outputs/*/metrics.json`.
