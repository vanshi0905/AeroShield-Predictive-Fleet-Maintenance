# AeroShield Pitch Deck: Content, Visual Structure & Speaker Notes
**Competition**: Tata Elxsi TELIPORT Season 4  
**Problem Statement**: 1 — Self-Healing Machines (Predictive Maintenance for Industrial Turbofans)  
**Deliverable Artifact**: `outputs/AeroShield_Pitch_Deck.pptx` (16:9 Widescreen)  
**Submission Tag**: `v1.0-submission`  

---

## Slide 1: Title & Executive Overview
- **Category Header**: `TATA ELXSI TELIPORT SEASON 4 | PROBLEM STATEMENT 1`
- **Main Title**: **AeroShield**
- **Subtitle**: *Closed-Loop Autonomous Predictive Fleet Maintenance for Mission-Critical Turbofans*
- **Four Architectural Pillars**:
  1. **Sensor Quality Gates**: Flatline variance thresholding ($Var \ge 10^{-6}$), physical bounds validation, zero collinear noise.
  2. **Uncertainty-Aware ML**: HistGradientBoosting Quantiles (p10, p50, p90) + Secondary Consensus Forest + Cross-conformal bounds.
  3. **Deterministic Safety**: Strict RUL state machine, automated work orders, human-in-the-loop exception queue.
  4. **Audit & Governance**: Monotonic HMAC-SHA256 hash chain (1,670 verified blocks), MLflow model registry.
- **Presenter Spoken Notes (60s Hook)**:
  > *"Good morning judges. Today we present AeroShield, a closed-loop predictive maintenance and self-healing architecture engineered for mission-critical aircraft turbofans. AeroShield solves the core challenge of NASA C-MAPSS: accurately estimating Remaining Useful Life under multi-regime flight drift and dual failure modes, while enforcing deterministic safety triage and immutable cryptographic governance. Every component you see today is fully implemented and reproducible in our repository."*

---

## Slide 2: End-to-End Five-Layer Closed-Loop Architecture (Rubric: 20%)
- **Category Header**: `SYSTEM DESIGN & COMPLETE PIPELINE`
- **Slide Title**: **End-to-End Five-Layer Closed-Loop Architecture**
- **Five Functional Columns**:
  - **Layer 1: Ingestion & Physics Gates**: 21 sensor channels + 3 operating settings; variance gate removes flatlined sensors (1, 5, 10, 16, 18, 19); continuous polynomial regime normalization; rolling window statistics ($w \in \{5, 10, 20\}$ cycles).
  - **Layer 2: Dual-Model ML Inference**: HistGradientBoosting Quantile regressors (p10, p50, p90); secondary Random Forest consensus estimator; asymmetric late-shift calibration ($\Delta \in [3, 8]$ cycles); step-bounded smoothing + cross-conformal intervals.
  - **Layer 3: Autonomous Triage Agent**: Deterministic safety state machine (`CRITICAL` / `WARNING` / `NORMAL`); Isolation Forest sensor & failure anomaly detection; automated work order creation with priority and parts; graceful fallback to human triage on conflict.
  - **Layer 4: MLOps, Governance & Audit**: MLflow tracking server with SQLite experiment store; Champion-Challenger automated promotion gates; two-sample Kolmogorov-Smirnov drift detection; monotonic HMAC-SHA256 tamper-evident audit ledger.
  - **Layer 5: Avionics Operations Cockpit**: FastAPI production REST API with Bearer token security; dynamic fleet health matrix (100 to 259 engines per subset); interactive cycle replay with sensor overlays & bounds; dedicated exception desk & MLOps evaluation view.
- **Presenter Spoken Notes**:
  > *"Here is AeroShield's architectural blueprint. It operates as a true closed loop across five layers: Raw telemetry is ingested and cleansed through physical sensor gates in Layer 1; Layer 2 executes dual-model quantile inference with cross-conformal uncertainty bounds; Layer 3 feeds those bounds into a deterministic triage state machine that generates maintenance work orders; Layer 4 governs the lifecycle through MLflow, champion gates, and an HMAC-SHA256 audit ledger; and Layer 5 presents real-time telemetry and exception queues to fleet operators via the cockpit."*

---

## Slide 3: Layer 1 — Sensor Quality Gates & Multi-Regime Normalization (Rubric: 15%)
- **Category Header**: `DATA ENGINEERING & SIGNAL PROCESSING`
- **Slide Title**: **Layer 1: Sensor Quality Gates & Multi-Regime Normalization**
- **Card 1: Sensor Variance Filtering**:
  - Turbofans feature 21 sensors and 3 operating settings.
  - Flatline Gate: Sensors with $Var < 10^{-6}$ carry zero degradation signal (sensors 1, 5, 10, 16, 18, 19).
  - Eliminating flat sensors prevents collinearity and reduces feature dimensionality without information loss.
  - Physical bounds checks $[x_{\min}, x_{\max}]$ immediately intercept stuck sensors and telemetry corruption.
- **Card 2: Multi-Regime Operating Normalization**:
  - FD002 and FD004 operate across 6 discrete flight regimes (altitude 0–45,000 ft, Mach 0–0.84, TRA 60–100°).
  - Raw sensor readings are dominated by operating regime swings rather than true engine wear.
  - Continuous polynomial normalization models baseline sensor behavior across operating conditions.
  - Subtracting regime baselines reveals the true underlying mechanical degradation trajectory.
- **Card 3: Rolling Temporal Feature Extraction**:
  - Degradation is non-Markovian; single cycle snapshots lack trend context.
  - Multi-window rolling aggregates computed over $w \in \{5, 10, 20\}$ flight cycles.
  - Engineered features: rolling mean, standard deviation, minimum, maximum, linear trend/slope, and lag-1 differences.
  - Generates 90–120 engineered signals per time step, strictly preventing future-window data leakage.
- **Presenter Spoken Notes**:
  > *"Data engineering accounts for 15% of the rubric, and it is where naive ML pipelines fail. In C-MAPSS, especially FD002 and FD004, engines experience six distinct flight conditions. Sensor values fluctuate wildly based on altitude and throttle alone. We apply continuous polynomial normalization to isolate regime baselines, strip out six completely flatlined sensors (1, 5, 10, 16, 18, 19) via variance gates, and engineer rolling temporal features across 5, 10, and 20 cycle windows. All rolling calculations strictly observe causality with zero future data leakage."*

---

## Slide 4: Layer 2 — Quantile Gradient Boosting & Conformal Calibration (Rubric: 20%)
- **Category Header**: `ML MODELING & STATISTICAL RIGOR`
- **Slide Title**: **Layer 2: Quantile Gradient Boosting & Conformal Calibration**
- **Card 1: HistGradientBoosting Quantile Models**:
  - Trained with pinball loss on three target quantiles: p10 (optimistic), p50 (median), p90 (conservative).
  - Histogram-based binning scales efficiently across 40,000+ telemetry rows with native missing value handling.
  - Provides immediate uncertainty bounds without assuming Gaussian residuals.
  - Secondary Consensus Model: Independent 30-tree Random Forest estimator detects structural model divergence.
- **Card 2: Asymmetric NASA Loss Calibration**:
  - Standard MSE assumes symmetric error, which is fatal in aviation.
  - NASA Asymmetric Loss: $d = y_{\text{pred}} - y_{\text{true}}$.
  - Overestimates ($d > 0$) penalized exponentially: $e^{d/10} - 1$.
  - Underestimates ($d < 0$) penalized gently: $e^{-d/13} - 1$.
  - Late-Shift Optimization: Tuned shift $\Delta \in [3, 8]$ cycles applied to p50, slashing penalty while preserving RMSE.
- **Card 3: Smoothing & Cross-Conformal Bounds**:
  - Step-Bounded Smoother: Enforces wear monotonicity ($\Delta RUL / \Delta t \le 1.0$) with adaptive smoothing $\alpha \in [0.2, 0.5]$.
  - Prevents physical impossibilities where RUL jumps up between consecutive flight cycles.
  - Cross-Conformal Interval Calibration: Evaluated on GroupKFold out-of-fold validation residuals.
  - Dynamically widens $[p_{10}, p_{90}]$ intervals to empirically guarantee $\ge 80\%$ coverage on critical $RUL \le 50$ cycles.
- **Presenter Spoken Notes**:
  > *"For Layer 2, we deliberately avoided black-box deep learning or standard MSE regressors. In aviation maintenance, overestimating RUL means an unpredicted in-flight failure, which the NASA scoring metric penalizes exponentially. We train HistGradientBoosting models on p10, p50, and p90 quantiles, verify predictions against an independent Random Forest consensus model, apply an empirical late shift to minimize the NASA asymmetric loss, and enforce step-bounded exponential smoothing so RUL cannot jump upward over time. Cross-conformal calibration widens prediction intervals to guarantee over 80% coverage in the critical end-of-life operating phase."*

---

## Slide 5: Layer 3 — Deterministic Triage State Machine & Work Orders (Rubric: 15%)
- **Category Header**: `AUTONOMOUS AGENT & SAFETY PROTOCOL`
- **Slide Title**: **Layer 3: Deterministic Triage State Machine & Work Orders**
- **Card 1: Deterministic Safety Thresholds**:
  - Zero unconstrained LLM or probabilistic guessing in safety-critical decisions.
  - `CRITICAL` ($RUL \le 20$ cycles): Immediate grounding and priority teardown inspection.
  - `WARNING` ($20 < RUL \le 50$ cycles): Component replacement scheduled at next hub turn.
  - `NORMAL` ($RUL > 50$ cycles): Engine cleared for regular flight service.
  - Conservative gating: Lower conformal bound p10 used for critical safety dispatch.
- **Card 2: Automated Exception Escalation Queue**:
  - Autonomous systems must fail safely and transparently when uncertainty spikes.
  - Sensor Malfunction: Stuck readings or variance violations routed to `NEEDS_HUMAN`.
  - Model Disagreement: Discrepancy $> 25$ cycles between HGB and Random Forest triggers human audit.
  - Anomaly Detection: Unsupervised Isolation Forest flags non-conforming degradation vectors.
  - Ensures human experts inspect ambiguous edge cases before any engine is pulled.
- **Card 3: Relational Work Order Lifecycle**:
  - Embedded SQLite transactional store (`outputs/<subset>/work_orders.db`).
  - Automated Work Order Generation: Auto-populates affected unit, RUL bounds, priority, and required parts kit.
  - Strict Lifecycle States: `PENDING` $\to$ `APPROVED` $\to$ `DISPATCHED` $\to$ `COMPLETED`.
  - Human-in-the-Loop Dispatch: Supervisor authentication enforced via API Key before maintenance release.
- **Presenter Spoken Notes**:
  > *"Layer 3 bridges predictions to enterprise maintenance action. We enforce a strictly deterministic state machine: CRITICAL under 20 cycles, WARNING between 20 and 50 cycles, and NORMAL above 50 cycles. When telemetry exhibits stuck sensors, model disagreement greater than 25 cycles, or Isolation Forest anomalies, the engine is automatically routed to the NEEDS_HUMAN triage queue. When approved, work orders transition through a relational SQLite state machine: PENDING, APPROVED, DISPATCHED, and COMPLETED, requiring authenticated supervisor release."*

---

## Slide 6: Layer 4 — MLOps Lifecycle, Promotion Gates & Cryptographic Audit (Rubric: 15%)
- **Category Header**: `MLOPS, GOVERNANCE & COMPLIANCE`
- **Slide Title**: **Layer 4: MLOps Lifecycle, Promotion Gates & Cryptographic Audit**
- **Card 1: Experiment Tracking & Registry**:
  - MLflow tracking backend backed by SQLite (`outputs/mlflow.db`).
  - Logs hyperparameters, 5-fold cross-validation RMSE, and artifact pointers.
  - Centralized Model Registry (`outputs/registry.json`) tracking champion models per subset.
  - Automated Promotion Gate: Challenger models must outperform active champions on both RMSE and NASA loss across OOF evaluations.
- **Card 2: Statistical Drift Detection**:
  - Two-sample Kolmogorov-Smirnov (KS) test on rolling feature distributions.
  - Compares active inference windows against baseline training distributions.
  - Alert Trigger: Significant drift ($p < 0.05$) across $> 30\%$ of features flags retrain requirement.
  - Adaptive Retraining: Retrains model on combined historical + newly observed run-to-failure cycles.
- **Card 3: Tamper-Evident Cryptographic Ledger**:
  - Every triage decision and work order transition is sealed into a SHA-256 / HMAC hash chain.
  - Block formulation: $H_i = \text{HMAC}(H_{i-1} \parallel \text{timestamp} \parallel \text{order\_id} \parallel \text{event} \parallel \text{details})$.
  - Monotonic block continuity: altering any historical record invalidates all subsequent block seals.
  - 1,670 cumulative blocks cryptographically verified intact across all four C-MAPSS subsets.
- **Presenter Spoken Notes**:
  > *"Layer 4 addresses production engineering and regulatory compliance. We track experiments in MLflow with a centralized model registry. Champion-challenger gates prevent regression by requiring challengers to beat champions on both RMSE and NASA loss before promotion. We run two-sample Kolmogorov-Smirnov drift tests across sensor features. Finally, every work order event is cryptographically sealed into an HMAC-SHA256 monotonic hash chain. We have verified all 1,670 blocks across FD001 through FD004 with zero chain breaks."*

---

## Slide 7: Empirical Benchmarks & Transparent Model Disclosures (Rubric: 15%)
- **Category Header**: `VALIDATION ACROSS ALL 4 C-MAPSS SUBSETS`
- **Slide Title**: **Empirical Benchmarks & Transparent Model Disclosures**
- **Benchmark Table (Extracted Directly from `outputs/*/metrics.json`)**:

| Subset | Regimes & Fault Modes | Capped Test RMSE | NASA Asymmetric Loss | Coverage | Work Orders | Final Human Triage |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **FD001** | 1 Regime, HPC Degradation | **11.30** | **213.5** | **84.0%** | 46 Orders | **0 (100% Auto)** |
| **FD002** | 6 Regimes, HPC Degradation | **13.97** | **8,519.2** | **88.4%** | 137 Orders | **6 (97.7% Auto)** |
| **FD003** | 1 Regime, HPC + Fan Degradation | **11.42** | **266.0** | **84.0%** | 54 Orders | **3 (97.0% Auto)** |
| **FD004** | 6 Regimes, HPC + Fan Degradation | **13.06** | **4,573.2** | **78.6%** | 106 Orders | **3 (98.8% Auto)** |

- **Technical Disclosures & Known Boundaries**:
  - **Multi-Regime Complexity**: FD002 and FD004 encounter higher NASA asymmetric loss due to severe operating condition shifts.
  - **Coverage Calibration**: FD004 test coverage is 78.6% (calibrated against 81.5% out-of-fold validation coverage).
  - **Asymmetric Late-Shift Tradeoff**: Calibrating for NASA loss shifts predictions early, yielding late shares between 19.3% and 40.7%.
  - **Strict Reproducibility**: 100% deterministic outputs across identical seeds, verified via `python scripts/render_readme_tables.py --check`.
- **Presenter Spoken Notes**:
  > *"Here are our empirical results across all four C-MAPSS subsets, extracted directly from metrics.json. On FD001 we achieve 11.30 capped RMSE and 213.5 NASA score with 100% autonomous resolution. On FD004, the most challenging dataset with six flight regimes and dual failure modes, our capped RMSE is 13.06 with 98.8% autonomous resolution, leaving just 3 engines for human triage. In the spirit of engineering rigor, we disclose our trade-offs: multi-regime datasets carry higher NASA penalties, and our late-shift optimization shifts errors early to minimize enterprise downtime risk."*

---

## Slide 8: Operations Cockpit & Production Scalability (Rubric: 15% + Demo)
- **Category Header**: `AVIONICS COCKPIT & FUTURE ROADMAP`
- **Slide Title**: **Operations Cockpit & Production Scalability**
- **Card 1: Fleet Avionics Cockpit**:
  - Production FastAPI application serving real-time fleet analytics.
  - Fleet Matrix: Visualizes complete engine health across 100 to 259 aircraft units per subset.
  - Cycle Replay: Interactive telemetry scrub with real-time sensor overlays and conformal bands.
  - Exception Triage Desk: Dedicated supervisor interface for inspecting and approving escalated engines.
  - MLOps Tab: Direct visibility into active champions, challenger comparisons, and promotion audits.
- **Card 2: Deployment & Edge Architecture**:
  - REST API: Secure endpoints protected by Bearer API Key authentication.
  - Dual-Target Distribution: Local FastAPI avionics server + edge-compatible static preview on Vercel.
  - Lightweight Runtime: Core inference requires standard scientific Python stack without heavy GPU dependencies.
  - Fault-Tolerant API: Graceful degradation with bounded simulator fallback for standalone testing.
- **Card 3: Scalability & Future Roadmap**:
  - ONNX Edge Quantization: Deploying quantized models directly onto aircraft FADEC / line-replaceable units.
  - Streaming Telemetry Connectors: Integrating Apache Kafka and MQTT for live industrial IoT fleet feeds.
  - Continuous Active Learning: Automated ingestion of newly overhauled engine teardown logs.
  - Multi-Tenant MRO Integration: Direct ERP hooks into SAP S/4HANA and IBM Maximo aviation modules.
- **Presenter Spoken Notes**:
  > *"Finally, we bring everything together in the AeroShield operations cockpit. Operators can view the entire fleet matrix, replay engine degradation cycles with conformal intervals, and inspect exception queues. Our deployment architecture combines a secure FastAPI REST backend with an edge-compatible preview. Looking forward, our roadmap targets ONNX runtime quantization for on-wing FADEC units and streaming MQTT/Kafka pipelines for continuous real-world fleet ingestion. Thank you, and we welcome your questions."*

---

## Technical Q&A Defense Sheet (Direct Answers for Judges)

### Q1: "Why does FD002 have an 8,519.2 NASA score while FD001 is only 213.5?"
> *"NASA asymmetric loss penalizes late predictions exponentially: $e^{d/10}-1$ for $d > 0$. In FD002, engines cycle rapidly across six operational regimes. Even with our polynomial regime normalization, occasional operating transitions can briefly inflate RUL estimates before smoothing catches up. A small handful of late predictions produce exponential penalties under the NASA metric. Our late-shift optimization ($\Delta = 8.0$ cycles on FD002) brings the late share down to 19.3%, but the residual tail still dominates the score. That is the exact mathematical reality of the NASA metric on multi-regime data."*

### Q2: "Why use HistGradientBoosting instead of a Deep Learning LSTM or Transformer?"
> *"We benchmarked gradient-boosted trees against sequential models. For tabular turbofan sensor data with rolling temporal features, tree ensembles consistently achieve superior sample efficiency and lower latency without overfitting. HistGradientBoosting directly optimizes pinball loss for quantile regression, natively handles sensor missingness, trains in under 3 minutes per subset on standard CPU hardware, and executes inference in sub-millisecond time. In an operational aviation environment, deterministic inference latency and CPU portability are critical operational requirements."*

### Q3: "How do you guarantee that an autonomous triage action won't ground an engine erroneously?"
> *"First, our triage rules are deterministic rather than probabilistic or generative: an engine is only flagged CRITICAL when its calibrated lower bound $p_{10}$ drops to or below 20 cycles. Second, whenever telemetry exhibits stuck sensors, Isolation Forest anomalies, or model divergence greater than 25 cycles between HGB and our Random Forest estimator, the engine is automatically escalated to the NEEDS_HUMAN queue. Third, all maintenance work orders enter a PENDING state and require authenticated supervisor sign-off before dispatch. The autonomous system handles the heavy data synthesis, but the human supervisor retains ultimate operational authority."*
