# System Architecture: AeroShield Autonomous Predictive Maintenance Platform

AeroShield is a closed-loop autonomous predictive maintenance and digital twin platform engineered for connected industrial turbofans, high-pressure compressors, and aeroderivative engines based on NASA C-MAPSS FD001–FD004 benchmarks.

---

## 1. High-Level Architecture Topology

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
│  - Gas-Path Interaction Ratios: s8/s9 (Fan/Core Speed), s13/s14 (Corrected Speed),     │
│    s11/s7 (Pressure Ratio), s4/s3 (Temperature Ratio)                                  │
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
│  - Tamper-Evident SHA-256 cryptographic hash chain Audit Chain (Immutable Event Provenance)          │
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

## 2. Component Design Details

### Data Engineering Pipeline
* **Raw Stream Cleaning**: Telemetry rows with missing sensor readings are rejected at ingress. Sensor noise is cleaned using a single-pass causal running median filter ($W=5$), avoiding lookahead bias.
* **Aerodynamic Ratio Injection**: Four thermodynamic ratios are computed directly from the gas path:
  1. $\text{Fan/Core Speed Ratio} = s_8 / s_9$
  2. $\text{Corrected Speed Ratio} = s_{13} / s_{14}$
  3. $\text{Compressor Pressure Ratio} = s_{11} / s_7$
  4. $\text{Turbine Temperature Ratio} = s_4 / s_3$

### Anomaly Detection & Conformal Calibration
* Anomaly scores use baseline-subtracted sensor deviations against the early cycles of each engine. Out-of-fold detection is 100% on FD001 and FD002, 69% on FD003, and 5.6% on FD004. Test-set detection is 29%, 38%, 19%, and 1.6%. FD004 is not a 100% detection result.
* RUL uncertainty is quantified via non-parametric conformal prediction, yielding statistically validated P10, P50, and P90 quantile intervals.

### Tamper-Evident Audit Chain
Each work-order event is appended to an HMAC-SHA256 chain. The sample databases use a published demo key, so this is not an FAA Part 145 or EASA M.A.306 record. The link is:
$$\text{Hash}_i = \text{SHA256}(\text{EntryID} \parallel \text{Timestamp} \parallel \text{OrderID} \parallel \text{Action} \parallel \text{Hash}_{i-1})$$
The integrity of the entire historical maintenance log can be verified in millisecond latency via the dashboard or API endpoint `/api/audit-verify`.
