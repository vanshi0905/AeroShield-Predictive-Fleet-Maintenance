# Layer 1: Deterministic Ingress & Aerodynamic Feature Engineering

**Primary Code Files**:
* [`shield/src/smoother.py`](../shield/src/smoother.py) — Causal running median noise filter
* [`shield/src/data.py`](../shield/src/data.py) — C-MAPSS data ingestion, schema validation, and regime clustering
* [`shield/src/features.py`](../shield/src/features.py) — Gas-path interaction ratios, EWMA smoothing, and robust winsorizing

---

## 1. System Role & Architecture

Layer 1 is the deterministic ingress gateway for the AeroShield predictive maintenance pipeline. It processes streaming telemetry from 21 continuous turbofan sensors and 3 operational flight settings, attenuates sensor instrumentation noise, computes gas-path thermodynamics, and clusters multi-regime operating envelopes.

```
Incoming C-MAPSS Telemetry Stream (21 Sensors, 3 Settings)
   │
   ▼
1. Ingress Schema Validation & Null Rejection (shield/src/data.py)
   │
   ▼
2. Causal Running Median Smoothing (Window W=5, zero lookahead) (shield/src/smoother.py)
   │
   ▼
3. Gas-Path Interaction Ratio Synthesis (s8/s9, s13/s14, s11/s7, s4/s3) (shield/src/features.py)
   │
   ▼
4. K-Means Operational Regime Clustering (K=6 flight conditions) (shield/src/data.py)
   │
   ▼
5. Exponentially Weighted Moving Average (alpha=0.10) & Robust MAD Winsorizing
   │
   ▼
Normalized Feature Vector to Layer 2
```

---

## 2. Algorithmic Formulations

### A. Causal Running Median Noise Attenuation
Sensor telemetry in industrial turbofans suffers from aerothermal noise, flow turbulence, and structural vibrations. Conventional symmetric smoothing filters (e.g. 2-sided Savitzky-Golay or centered rolling means) incorporate future sensor readings, introducing severe lookahead bias into historical model training.

AeroShield enforces a strictly causal running median over a rolling backward window $W=5$:

$$\tilde{x}_t = \text{Median}(x_{t-W+1}, x_{t-W+2}, \dots, x_t)$$

* For the first $t < W$ cycles, the median evaluates over all available causal points $\{x_1, \dots, x_t\}$.
* Guarantees zero data leakage and preserves sharp degradation trend inflections while rejecting single-point sensor dropouts and spikes.

### B. Gas-Path Thermodynamic Interaction Ratios
Raw sensor values change dynamically when pilots alter throttle resolver angles or when altitude changes. To capture component degradation independent of flight condition, AeroShield computes four thermodynamic gas-path interaction ratios derived from turbofan propulsion physics:

1. **Fan-to-Core Physical Rotor Speed Ratio**:
   $$\text{Ratio}_{s_8/s_9} = \frac{s_8 \text{ (Physical Fan Speed } N_f \text{, rpm)}}{s_9 \text{ (Physical Core Speed } N_c \text{, rpm)}}$$
   *Identifies core mechanical binding, shaft friction, and compressor fouling.*

2. **Corrected Rotor Speed Ratio**:
   $$\text{Ratio}_{s_{13}/s_{14}} = \frac{s_{13} \text{ (Corrected Fan Speed)}}{s_{14} \text{ (Corrected Core Speed)}}$$
   *Normalizes rotational dynamics against ambient temperature and pressure at the engine intake.*

3. **High-Pressure Compressor Pressure Drop Ratio**:
   $$\text{Ratio}_{s_{11}/s_7} = \frac{s_{11} \text{ (HPC Outlet Static Pressure } P_{s30} \text{, psia)}}{s_7 \text{ (HPC Outlet Total Pressure } P_{30} \text{, psia)}}$$
   *Directly reflects compressor blade tip clearance wear and aerodynamic stalling margins.*

4. **Turbine Temperature Expansion Ratio**:
   $$\text{Ratio}_{s_4/s_3} = \frac{s_4 \text{ (Low-Pressure Turbine Outlet Temp } T_{50} \text{, }^\circ\text{R)}}{s_3 \text{ (High-Pressure Compressor Outlet Temp } T_{30} \text{, }^\circ\text{R)}}$$
   *Monitors thermal expansion efficiency and turbine blade thermal barrier coating (TBC) degradation.*

### C. K-Means Operational Regime Clustering
In complex subsets FD002 and FD004, turbofans traverse 6 distinct operational flight regimes combining altitude ($0–40,000$ ft), Mach number ($0.0–0.84$), and throttle resolver angle ($20–100^\circ$).

A K-Means clustering model ($K=6$) is fitted on the normalized 3-dimensional operational setting space:
$$\mathbf{s}_t = [\text{setting}_1, \text{setting}_2, \text{setting}_3]^\top$$
Each cycle is mapped to a discrete regime cluster $c_t \in \{0, 1, 2, 3, 4, 5\}$, allowing baseline normalization parameters to be calculated regime-by-regime.

### D. Robust Winsorizing & EWMA
To protect against erratic sensor spikes without distorting natural degradation curves:
* **MAD Winsorizing**: Outliers beyond $\pm 4.5 \times \text{MAD}$ (Median Absolute Deviation) are capped at the robust boundary:
  $$\text{MAD}_j = \text{Median}(|s_{j,t} - \text{Median}(s_j)|)$$
* **EWMA Filtering**: Computes exponential trend features ($\alpha = 0.10$):
  $$y_t = \alpha \tilde{x}_t + (1 - \alpha) y_{t-1}$$

---

## 3. Unit Verification & Test Proofs

Covered in automated test suites:
* [`shield/tests/test_smoother.py`](../shield/tests/test_smoother.py): Validates single-pass causal running median, zero lookahead bias, and boundary behavior.
* [`shield/tests/test_features_parity.py`](../shield/tests/test_features_parity.py): Validates computation and numerical stability of all 4 gas-path interaction ratios.
* [`shield/tests/test_schema.py`](../shield/tests/test_schema.py): Validates rejection of incomplete or malformed C-MAPSS ingress records.
