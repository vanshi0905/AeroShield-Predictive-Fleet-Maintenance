---
name: AeroShield Tactical Avionics Fleet Command
colors:
  surface: '#0B0F14'
  surface-dim: '#080B0F'
  surface-bright: '#1E2630'
  surface-container-lowest: '#05070A'
  surface-container-low: '#0E1319'
  surface-container: '#131922'
  surface-container-high: '#1A222E'
  surface-container-highest: '#222C3B'
  on-surface: '#E2E8F0'
  on-surface-variant: '#94A3B8'
  inverse-surface: '#E2E8F0'
  inverse-on-surface: '#1A222E'
  outline: '#334155'
  outline-variant: '#1E293B'
  surface-tint: '#00F5D4'
  primary: '#00F5D4'
  on-primary: '#00382E'
  primary-container: '#004D3F'
  on-primary-container: '#5FFAE1'
  inverse-primary: '#007A65'
  secondary: '#38BDF8'
  on-secondary: '#003554'
  secondary-container: '#0369A1'
  on-secondary-container: '#BAE6FD'
  tertiary: '#F59E0B'
  on-tertiary: '#451A03'
  tertiary-container: '#78350F'
  on-tertiary-container: '#FDE68A'
  error: '#EF4444'
  on-error: '#450A0A'
  error-container: '#7F1D1D'
  on-error-container: '#FECACA'
  success: '#10B981'
  on-success: '#022C22'
  success-container: '#064E3B'
  on-success-container: '#A7F3D0'
  primary-fixed: '#5FFAE1'
  primary-fixed-dim: '#00F5D4'
  on-primary-fixed: '#00201A'
  on-primary-fixed-variant: '#004D3F'
  background: '#080B0F'
  on-background: '#E2E8F0'
  surface-variant: '#1E2630'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
  data-primary:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.02em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.1em
  telemetry-xs:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.05em
rounded:
  sm: 2px
  DEFAULT: 4px
  md: 6px
  lg: 8px
  xl: 12px
  full: 9999px
spacing:
  unit: 4px
  gutter: 12px
  margin: 16px
  panel-padding: 20px
---

## Brand & Aesthetic Vision

The **AeroShield Tactical Avionics Fleet Command** design system is engineered for aerospace test benches, fleet operations control rooms, and flight-depot engineering workstations. It merges **Tactile Glassmorphism** with **Avionics Flight-Deck Precision** (inspired by modern glass cockpits, Airbus ECAM / Boeing EICAS systems, and NASA mission telemetry).

The interface is built on a deep, hierarchical **Obsidian Flight Canvas** (`#080B0F` to `#131922`), engineered to eliminate optical fatigue across 24/7 mission shifts. Micro-borders (`0.5px` white/teal at 12–18% opacity), subtle radar scanlines, and glowing conformal uncertainty envelopes deliver immediate situational awareness without visual clutter.

---

## Color System & Functional Roles

Every color in AeroShield maps directly to critical operational and flight-safety states:

- **Electric Cyan (`#00F5D4`):** Primary system pulse. Signifies calibrated states, active telemetry streams, conformal median predictions ($P_{50}$), and nominal machine health.
- **Avionics Sky (`#38BDF8`):** Secondary data stream. Used for baseline aerodynamic indicators, historical trends, and uncalibrated point estimates.
- **Signal Amber (`#F59E0B`):** Degradation warning. Flags early anomalies, `WATCH` tier engines, and moderate drift (PSI $\ge 0.15$).
- **Radar Crimson (`#EF4444`):** Flight safety alert. Strictly reserved for `CRITICAL` risk tiers ($P_{10} \le 15$ cycles), sensor dropouts, emergency dispatch triggers, and ledger integrity breaks.
- **Emerald Green (`#10B981`):** Operational readiness. Confirms 100% verified cryptographic blocks, passing MLOps promotion gates, and normal fleet status.
- **Obsidian Glass (`#131922` at 65% opacity + 20px blur):** Floating card surface elevation.

---

## Typography Hierarchy

AeroShield establishes a disciplined division between **Human Interface** (`Inter`) and **Operational Avionics Telemetry** (`JetBrains Mono`):

1. **Navigation, Headers & Triage Rules:** Handled by `Inter` for instantaneous human reading under operational pressure.
2. **Cycle Counts, RUL Bounds, Sensor Telemetry & SHA-256 Digests:** Rendered strictly in tabular `JetBrains Mono` to prevent column jitter during live telemetry updates.
3. **Data Field Headers:** Formatted with `label-caps` (all uppercase, 0.1em tracking) to create a crisp, military aerospace instrument panel aesthetic.

---

## Key Screen Layouts & Structural Modules

### Screen 1: Global Fleet Health Command Overview
- **Fleet KPI Metric Tiles:** High-contrast floating glass cards with micro-sparklines:
  - *Active Turbofans in Service* (e.g. 100 FD001 / 248 FD004)
  - *Empirical Conformal Coverage Rate* (83.2% vs 80.0% SLA Target)
  - *Fleet Readiness Score* (94.2% Operational)
  - *False Alarm Rate* (< 5.0% Guaranteed)
  - *Target Unscheduled Groundings (AOG)*: `0.00`
- **Turbofan Health Matrix Table:** Real-time searchable, filterable fleet roster with sortable columns: `Unit ID`, `Operating Regime`, `Cycle`, `Conformal RUL Band [P10 - P50 - P90]`, `Anomaly Score (z-dbase)`, `Health Status Chip`, `Quick Dispatch Action`.
- **Subsystem Degradation Gauges:** Segmented circular health meters for High Pressure Compressor (HPC), Low Pressure Turbine (LPT), Fan & Core Shaft Dynamics ($N_f / N_c$).

### Screen 2: Turbofan Telemetry Drill-Down & Time-Travel Replay
- **Avionics Time-Travel Scrub Bar:** Horizontal flight-cycle scrubber spanning Cycle 1 to End-of-Life:
  - Milestone markers: *Nominal Cruise*, *Onset of Degradation*, *Knee-Point Acceleration*, *Critical Cutoff*.
  - Playback controls: Play/Pause (1x, 2x, 5x speed), Step Forward (+1 cycle), Reset to Origin.
- **Glowing Conformal RUL Prediction Chart:**
  - Interactive multi-layer canvas: $P_{10}$ lower safety bound (dashed cyan), $P_{50}$ median estimate (solid bright cyan with outer glow), $P_{90}$ upper bound (dotted sky blue), and ground truth RUL line.
  - Semi-transparent gradient fill representing the 80% conformal uncertainty envelope.
- **Live Gas-Path Sensor Telemetry Grid:**
  - High Pressure Compressor Outlet Temp ($T_{30}$, `s3`)
  - Low Pressure Turbine Outlet Temp ($T_{50}$, `s4`)
  - Compressor Discharge Pressure ($P_{30}$, `s7`)
  - Fan & Core Rotor Speeds ($N_f$, `s8`; $N_c$, `s9`)
  - Aerodynamic Ratios: Core Speed Ratio ($s_8/s_9$), Pressure Drop ($s_{11}/s_7$), Turbine Temp Ratio ($s_4/s_3$).

### Screen 3: Autonomous Triage Agent & Cryptographic Work Orders
- **Industrial Dispatch Tickets:** Tactical physical work order cards with chamfered corners, priority status glow, technician assignment, estimated time-to-grounding, and recommended maintenance action (e.g., *Inspect HPC Stage 3 Blades for Creep Wear*).
- **Human Exception Queue:** Segregated review deck for sensor dropout anomalies, spike jump exceptions, and multi-model disagreement alerts.
- **Tamper-Evident Cryptographic Ledger (SHA-256):**
  - Chained block visualization: `Entry #`, `Timestamp`, `Work Order ID`, `Action Executed`, `Previous Hash`, `Current Block Hash`.
  - Live "Verify Ledger Integrity" action button with real-time green cryptographic verification badge.

### Screen 4: MLOps Model Retraining & Continuous Adaptation Cockpit
- **Champion vs. Challenger Tournament Matrix:** Side-by-side metric diff bars evaluating RMSE, C-MAPSS Asymmetric Score, Conformal Coverage %, and Late Prediction Share %.
- **Population Stability Index (PSI) Drift Histogram:** Visualizing feature distribution drift between training reference and streaming test cycles.
- **Live Retraining Terminal:** Embedded avionics terminal displaying real-time retraining stdout stream, loss convergence, and automated promotion gate decisions.

---

## Tactile Audio & Micro-Interaction Guidelines

- **Synthetic Audio Clicks:** Web Audio API zero-latency acoustic ticks on tab switches (800Hz / 15ms), timeline scrubbing (1200Hz / 8ms), and metallic latch tone on work order dispatch.
- **Hover & Focus States:** 0.5px border glow intensifies to 40% cyan on interactive cards; subtle 1.01x scale transform on dispatch buttons.
- **Zero AI Slop:** No generic gradients, no cartoonish illustrations, no oversized empty cards. Every pixel serves flight safety, uncertainty communication, and tactical fleet decision-making.
