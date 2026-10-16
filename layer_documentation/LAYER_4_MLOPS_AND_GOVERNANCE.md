# Layer 4: Continuous MLOps Governance & Drift Protection

**Primary Code Files**:
* [`shield/src/mlops.py`](../shield/src/mlops.py) — Age-matched PSI drift profiler and 4-gate champion/challenger policy
* [`shield/src/retrain_demo.py`](../shield/src/retrain_demo.py) — Closed-loop retraining pipeline with drift-adaptive preprocessor statistics

---

## 1. System Role & Architecture

Layer 4 acts as the statistical governance guardrail for all models deployed in the AeroShield platform. In production industrial fleets, operating conditions drift due to seasonal atmospheric changes, route altitude variations, and sensor recalibrations. Layer 4 continuously monitors incoming telemetry streams for covariate shift using age-matched statistical divergence, executes closed-loop retraining, and enforces a strict 4-condition promotion gate that guarantees candidate models never degrade serving performance.

```
Monitored Fleet Telemetry Stream
   │
   ▼
1. Age-Matched Population Stability Index (PSI) Scan
   • Bins: Stage 1 [0-40], Stage 2 [40-80], Stage 3 [80-140], Stage 4 [140+]
   • Prevents confounding component wear with operational drift
   • Evaluates 10 quantile bins per sensor feature
   │
   ├─► PSI < 0.10: Stable (Nominal Serving)
   ├─► 0.10 <= PSI <= 0.20: Moderate Drift (Telemetry Warning)
   └─► PSI > 0.20: Significant Drift (Trigger Closed-Loop Retraining)
                               │
                               ▼
2. Drift-Adaptive Preprocessor Retraining
   • Updates running medians, MAD winsor limits, and baseline norms
   • Incorporates right-censored fleet engines (serviced before failure)
   • Trains Challenger Candidate (Quantile HistGradientBoosting + Consensus)
                               │
                               ▼
3. Four-Condition Statistical Invariance Gate
   [Check 1] Test RMSE <= Champion (Zero Degradation)
   [Check 2] NASA Asymmetric Loss <= +5.0% Rise
   [Check 3] Conformal Coverage >= 75.0% Min (1-Sided Boundary)
   [Check 4] Late Over-Prediction Delta <= +5.0 pts Over Champion
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼ (All 4 Pass)                              ▼ (Any Fail)
   PROMOTED TO CHAMPION                        RETAINED IN STAGING
   • Active in production serving              • Gated flag set (gated=true)
   • Registry status updated                   • Champion v1 retained
```

---

## 2. Mathematical Formulations & Governance Protocols

### A. Age-Matched Population Stability Index (PSI)
* **The Confounding Dilemma**: Standard drift detection blindly scans all incoming sensor readings against a global baseline. Because turbofan sensors naturally shift as engines age (e.g. exhaust gas temperature increases as turbine clearances widen), standard drift monitors falsely flag natural component degradation as operational covariate shift.
* **The Age-Matched Solution**: AeroShield partitions flight cycles into four operational lifecycle stages:
  1. **Stage 1 (Break-in Baseline)**: $t \in [0, 40]$ cycles
  2. **Stage 2 (Steady Cruise)**: $t \in [40, 80]$ cycles
  3. **Stage 3 (Accelerated Degradation)**: $t \in [80, 140]$ cycles
  4. **Stage 4 (Depot Wear Boundary)**: $t \ge 140$ cycles

For each stage and sensor feature $j$, the reference distribution $P$ is divided into $K=10$ baseline quantile bins. For an incoming batch distribution $Q$:

$$\text{PSI}_j = \sum_{k=1}^{10} (q_k - p_k) \times \ln\left(\frac{q_k + \epsilon}{p_k + \epsilon}\right)$$

where:
* $p_k$: Percentage of baseline reference samples in quantile bin $k$.
* $q_k$: Percentage of production incoming samples in quantile bin $k$.
* $\epsilon = 10^{-4}$: Smoothing constant preventing division by zero.

### Operational Drift Thresholds:
* **$\text{PSI} < 0.10$**: **Stable**. Baseline invariant; production serving proceeds.
* **$0.10 \le \text{PSI} \le 0.20$**: **Moderate Drift**. Minor atmospheric or flight route variation; telemetry warning logged.
* **$\text{PSI} > 0.20$**: **Significant Drift**. Structural covariate shift detected; triggers automated preprocessor adaptation and retraining job.

---

### B. Four-Condition Champion/Challenger Promotion Gate
Before any newly trained challenger model can replace the active champion in production, it must be evaluated on an independent hold-out validation set and pass all four criteria:

#### Gate 1: Zero-Degradation RMSE Invariance
$$\text{RMSE}_{\text{challenger}} \le \text{RMSE}_{\text{champion}}$$
*Ensures candidate accuracy never regresses against active serving baseline.*

#### Gate 2: NASA Asymmetric Loss Bound
$$\text{Loss}_{\text{challenger}} \le 1.05 \times \text{Loss}_{\text{champion}}$$
*Limits risk growth to $\le +5.0\%$ under the exponential late-prediction penalty metric.*

#### Gate 3: One-Sided Conformal Coverage Safety Boundary
$$\text{Coverage}_{\text{challenger}} \ge 75.0\%$$
*Guarantees the $80\%$ conformal prediction interval maintains at least $75.0\%$ empirical coverage on the validation engines (preventing overconfident under-coverage).*

#### Gate 4: Late Over-Prediction Share Constraint
$$\text{LateShare}_{\text{challenger}} - \text{LateShare}_{\text{champion}} \le +5.0 \text{ percentage points}$$
*Restricts the proportion of late predictions ($d_i \ge 0$), directly protecting the fleet against dangerous in-flight engine shutdowns (IFSD).*

If **any single check fails**, the promotion is blocked immediately. The model is registered in the SQLite MLflow registry as `status=STAGING` with `gated=true`, and the active champion remains in production serving.

---

### C. Right-Censored Telemetry Adaptation
In operational fleets, many engines are pulled for scheduled maintenance or airframe overhauls before reaching functional run-to-failure failure. AeroShield's retraining pipeline handles right-censored units by evaluating a one-sided loss:
$$L_{\text{censored}}(y, \hat{y}) = \begin{cases} 
0 & \text{if } \hat{y} \ge y_{\text{observed}} \\[4pt]
(y_{\text{observed}} - \hat{y})^2 & \text{if } \hat{y} < y_{\text{observed}}
\end{cases}$$
This prevents the retraining pipeline from artificially assuming engines that were serviced early had failed.

---

## 3. Unit Verification & Test Proofs

Covered in automated test suites:
* [`shield/tests/test_improvements.py`](../shield/tests/test_improvements.py): Validates one-sided coverage gate check and drift-adaptive retraining.
* [`platform/test_platform.py`](../platform/test_platform.py): Validates `/api/mlops` metrics payload and `/api/retrain/trigger` automated evaluation.
