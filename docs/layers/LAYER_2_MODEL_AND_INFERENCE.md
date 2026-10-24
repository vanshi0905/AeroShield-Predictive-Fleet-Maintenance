# Layer 2: Machine Learning Inference, Conformal Uncertainty & Anomaly Detection

**Primary Code Files**:
* [`shield/src/anomaly.py`](../shield/src/anomaly.py) — Baseline-subtracted sensor anomaly detector
* [`shield/src/calibrate.py`](../shield/src/calibrate.py) — Quantile HistGradientBoosting, Conformal Prediction, and Secondary Non-Linear Consensus

---

## 1. System Role & Architecture

Layer 2 executes real-time machine learning inference, statistical anomaly detection, and conformal uncertainty quantification. It ingests the normalized feature vector from Layer 1 and outputs calibrated remaining useful life (RUL) prediction intervals ($P_{10}, P_{50}, P_{90}$), anomaly deviation scores, and model consensus metrics.

```
Normalized Feature Vector from Layer 1
   │
   ├───────────────────────────────────────────────────────┐
   ▼                                                       ▼
1. Baseline-Subtracted Anomaly Detection           2. Piecewise Linear Capped Target
   • Healthy Baseline (t <= 20 cycles)                • RUL_cap = 125 cycles
   • Deviation d_base relative to baseline            • Eliminates flat initial wear
   • Threshold tau = 3.0                              
   • OOF rate is not the test rate              
   │                                                       │
   │                                                       ▼
   │                                               3. Quantile HistGradientBoosting
   │                                                  • Pinball Loss for P10, P50, P90
   │                                                  • Gradient-boosted decision trees
   │                                                       │
   │                                                       ▼
   │                                               4. Non-Linear Secondary Consensus
   │                                                  • Independent Second Opinion
   │                                                  • Divergence check (|P50_1 - P50_2| > 25)
   │                                                       │
   ▼                                                       ▼
5. Non-Parametric Conformal Prediction Calibration
   • Finite-sample non-conformity scores E_i on held-out calibration engines
   • Calibrated interval C(x) = [q_0.1 - q_hat, q_0.9 + q_hat]
   • Validated empirical coverage: 78.6% to 88.4% (>= 75.0% lower gate)
   │
   ▼
Inference Output Vector to Layer 3 Triage
```

---

## 2. Core Mathematical Formulations

### A. Baseline-Subtracted Sensor Anomaly Detection
* **The Classical Failure Mode**: Conventional anomaly detectors evaluate raw rolling averages or un-normalized $z$-scores. Under multi-regime environments (FD002/FD004), shifting flight conditions cause massive apparent swings in temperature and pressure that are completely unrelated to mechanical wear. Consequently, classical detection rates on FD002/FD004 dropped below $<6\%$.
* **The Baseline-Subtracted Formulation**: AeroShield computes the engine-specific baseline for each sensor $j$ during the initial healthy flight cycles ($t \le 20$):
  $$\mu_{j, \text{base}} = \frac{1}{20} \sum_{t=1}^{20} s_{j, t}, \qquad \sigma_{j, \text{base}} = \sqrt{\frac{1}{20} \sum_{t=1}^{20} (s_{j, t} - \mu_{j, \text{base}})^2}$$
  The baseline-subtracted sensor deviation $d_{\text{base}}$ at flight cycle $t$ is:
  $$d_{\text{base}}(s_{j, t}) = \frac{s_{j, t} - \mu_{j, \text{base}}}{\sigma_{j, \text{base}}}$$
  An `IsolationForest` ensemble ($N=200$ trees) is trained on the baseline-subtracted deviation vector $\mathbf{d}_{\text{base}}$. Anomaly scores $s_t = -\text{decision\_function}(\mathbf{d}_{\text{base}})$ are smoothed with an EWMA ($\alpha = 0.3$) and confirmed when the score exceeds an out-of-fold calibrated threshold for $\ge 2$ consecutive cycles.
* **Results**: Out-of-fold detection on training engines is 100% (FD001), 100% (FD002), 87.0% (FD003), and 83.5% (FD004) with median leads of 29–43 cycles. On held-out test engines, flag rates are 29.0%, 37.8%, 21.0%, and 19.4% (reflecting engines entering progressive degradation before observation cutoff). On terminal test cycles, only 3 FD004 engines require human escalation.

### B. Piecewise Linear Capped Target
In turbofan engines, physical wear is negligible during early flight cycles (crack propagation and material loss remain latent). Modeling RUL linearly from cycle 0 forces models to fit meaningless variations during healthy operation. AeroShield enforces a piecewise linear target capped at $RUL_{\text{cap}} = 125$ cycles:

$$y_t = \min(RUL_t, \, 125)$$

This stabilizes early-cycle gradient descent and concentrates model capacity on the accelerated degradation knee.

### C. Quantile HistGradientBoosting ($P_{10}, P_{50}, P_{90}$)
Instead of predicting a single point estimate, AeroShield fits three separate quantile regressors using histogram-based gradient-boosted decision trees (`HistGradientBoostingRegressor`). Each model minimizes the pinball loss at quantile $\alpha \in \{0.10, 0.50, 0.90\}$:

$$L_\alpha(y, \hat{y}) = \max(\alpha(y - \hat{y}), \, (1 - \alpha)(\hat{y} - y))$$

* $\hat{q}_{0.10}$: Conservative lower bound (90% probability actual RUL exceeds this value).
* $\hat{q}_{0.50}$: Median expected remaining lifetime.
* $\hat{q}_{0.90}$: Optimistic upper bound.

### D. Non-Linear Secondary Model Consensus
To safeguard against single-model bias, an independent non-linear ensemble (`RandomForestRegressor` / `GradientBoosting`) generates a secondary prediction $\hat{y}_{\text{sec}}$. 

If the primary median and secondary predictions diverge by more than 25 flight cycles:
$$|\hat{q}_{0.50} - \hat{y}_{\text{sec}}| > 25$$
the system flags a model disagreement exception and dispatches the unit to the Human Specialist Review Queue rather than taking automated physical action.

### E. Non-Parametric Conformal Prediction Calibration
To provide rigorous finite-sample coverage guarantees without assuming Gaussian normality, AeroShield applies non-parametric conformal calibration.

1. On a held-out calibration partition of $n$ run-to-failure engines, compute non-conformity errors:
   $$E_i = \max(q_{0.10}(x_i) - y_i, \;\; y_i - q_{0.90}(x_i))$$
2. Determine the calibrated empirical $(1 - \alpha)$-quantile offset $\hat{q}$ (for target coverage $1 - \alpha = 0.80$):
   $$\hat{q} = \text{Quantile}_{1-\alpha}\left(\{E_i\}_{i=1}^n, \;\; \frac{\lceil (n+1)(1-\alpha) \rceil}{n}\right)$$
3. Construct the calibrated prediction band for any incoming flight cycle $x_{\text{test}}$:
   $$C(x_{\text{test}}) = [q_{0.10}(x_{\text{test}}) - \hat{q}, \;\;\; q_{0.90}(x_{\text{test}}) + \hat{q}]$$

**Empirical Coverage Across NASA C-MAPSS (Held-out Test Engines)**:
* **FD001**: 84.0%
* **FD002**: 88.4%
* **FD003**: 84.0%
* **FD004**: 78.6% (81.5% out-of-fold calibration)
*(All safely surpass the 75.0% lower gate requirement).*

### F. NASA Asymmetric Loss Function
In aviation maintenance, late predictions ($\hat{y} > y$, predicting the engine has more life than it actually does) are far more hazardous than early predictions ($\hat{y} < y$, scheduling maintenance earlier than necessary).

NASA formalizes this operational asymmetry through an exponential penalty metric:

$$S = \sum_{i=1}^N s_i \qquad \text{where} \qquad s_i = \begin{cases} 
\exp\left(-\frac{d_i}{13}\right) - 1 & \text{for } d_i < 0 \quad (\text{Early Prediction}) \\[8pt]
\exp\left(\frac{d_i}{10}\right) - 1 & \text{for } d_i \ge 0 \quad (\text{Late Prediction})
\end{cases}$$

where error $d_i = \hat{y}_i - y_i$. Late over-predictions grow exponentially with base $1/10$, heavily penalizing delayed dispatches that could cause in-flight shutdowns (IFSD).

---

## 3. Unit Verification & Test Proofs

Covered in automated test suites:
* [`shield/tests/test_calibration.py`](../shield/tests/test_calibration.py): Validates conformal quantile bounds, non-conformity scores, and coverage validation.
* [`shield/tests/test_improvements.py`](../shield/tests/test_improvements.py): Validates baseline-subtracted anomaly detection rate ($>80\%$) and secondary model consensus.
