# Mathematical Formulation: AeroShield Predictive Maintenance

This document specifies the exact mathematical models, loss functions, and statistical evaluation metrics implemented in AeroShield.

---

## 1. NASA Asymmetric Scoring Function

In turbofan fleet operations, **late predictions** ($\hat{y} > y$, predicting the engine has more life than it actually does) are far more hazardous than **early predictions** ($\hat{y} < y$, scheduling maintenance earlier than necessary).

NASA formalizes this operational penalty via the asymmetric exponential scoring function:

$$S = \sum_{i=1}^{N} s_i$$

where for error $d_i = \hat{y}_i - y_i$:

$$s_i = \begin{cases} 
\exp\left(-\frac{d_i}{13}\right) - 1 & \text{for } d_i < 0 \quad (\text{Early prediction}) \\[8pt]
\exp\left(\frac{d_i}{10}\right) - 1 & \text{for } d_i \ge 0 \quad (\text{Late prediction})
\end{cases}$$

Notice that late over-predictions ($d_i > 0$) grow exponentially with base $1/10$, heavily penalizing delayed dispatches that could cause in-flight engine shutdowns (IFSD).

---

## 2. Conformal Quantile Calibration & Empirical Coverage

To provide rigorous safety bounds without assuming a Gaussian error distribution, AeroShield employs non-parametric conformal calibration.

For a target coverage rate of $1 - \alpha = 0.80$ (80% coverage envelope):
1. On a held-out calibration partition, compute non-conformity scores:
   $$E_i = \max(q_{0.1}(x_i) - y_i, \, y_i - q_{0.9}(x_i))$$
2. Determine the calibrated quantile offset $\hat{q}$:
   $$\hat{q} = \text{Quantile}_{1-\alpha}\left(\{E_i\}_{i=1}^n, \, \frac{\lceil (n+1)(1-\alpha) \rceil}{n}\right)$$
3. Calibrated prediction band for test instance $x_{\text{test}}$:
   $$C(x_{\text{test}}) = [q_{0.1}(x_{\text{test}}) - \hat{q}, \;\; q_{0.9}(x_{\text{test}}) + \hat{q}]$$

Empirical coverage is verified via:
$$\text{Coverage} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(y_i \in C(x_i)\right) \ge 0.75 \quad (75.0\% \text{ lower gate bound})$$

---

## 3. Age-Matched Population Stability Index (PSI)

To detect operational covariate shift without confounding sensor degradation with engine wear, sensor streams are partitioned into four operational age bins:
* **Bin 1**: $t \in [0, 40]$ cycles (Break-in baseline)
* **Bin 2**: $t \in [40, 80]$ cycles (Nominal cruise)
* **Bin 3**: $t \in [80, 140]$ cycles (Accelerated wear)
* **Bin 4**: $t \ge 140$ cycles (Depot boundary)

For each bin and sensor $j$, the continuous value range is divided into $K=10$ quantile bins based on the reference baseline distribution $P$. For a monitored batch distribution $Q$:

$$\text{PSI}_j = \sum_{k=1}^K \left( q_k - p_k \right) \times \ln\left(\frac{q_k + \epsilon}{p_k + \epsilon}\right)$$

where:
* $p_k$: Percentage of baseline instances in quantile bin $k$
* $q_k$: Percentage of production instances in quantile bin $k$
* $\epsilon = 10^{-4}$: Smoothing constant preventing division by zero

### Operational Thresholds
* **$\text{PSI} < 0.10$**: Stable (No statistically significant drift)
* **$0.10 \le \text{PSI} \le 0.20$**: Moderate Drift (Telemetry review flagged)
* **$\text{PSI} > 0.20$**: Significant Drift (Trigger automated preprocessor re-normalization and model retraining)
