# Google Stitch Master Prompt: AeroShield Avionics Fleet Command Cockpit

Copy and paste the entire prompt below directly into **Google Stitch** (`stitch.withgoogle.com`) to generate the complete high-fidelity UI design, component layout, and frontend code.

---

```text
Design a world-class, production-grade Web Dashboard for "AeroShield" — an Autonomous Predictive Fleet Maintenance and Digital Twin Cockpit for Connected Industrial Turbofans and Aeroderivative Engines (based on NASA C-MAPSS benchmarks FD001–FD004).

## Aesthetic & Design Identity:
- Theme: "Tactical Avionics Glass Cockpit" meets "Mission Control Center".
- Palette: Deep Obsidian Canvas (#080B0F, #0E1319, #131922) with sharp Electric Cyan (#00F5D4) primary accents, Avionics Sky Blue (#38BDF8) secondary telemetry, Signal Amber (#F59E0B) caution warnings, and Radar Crimson (#EF4444) critical alerts.
- Material Language: Tactical Glassmorphism (semi-transparent dark panels at 65% opacity, 20px backdrop blur, 0.5px subtle white/cyan micro-borders at 15% opacity, and subtle CRT telemetry scanline textures).
- Typography: Dual-font system — "Inter" for headers, navigation, and human-readable text; "JetBrains Mono" for all numerical telemetry, flight cycles, RUL bounds, timestamps, and SHA-256 cryptographic digests.

## Global Header & Status Bar:
- Top bar with:
  1. AeroShield Logo: High-tech aerospace turbine insignia with glowing status pill "SYSTEM NOMINAL - ALL SENSORS STREAMING".
  2. Fleet Partition Switcher: Segmented buttons for [FD001 (100 Engines - Sea Level)], [FD002 (260 Engines - 6 Flight Regimes)], [FD003 (100 Engines - Dual Fault)], [FD004 (248 Engines - Multi-Regime & Complex Faults)].
  3. Telemetry status pill and fleet readiness metrics.
  4. Global Clock: UTC mission elapsed clock with live flight cycle refresh ticker.

## 4 Main Navigation Tabs:

### TAB 1: FLEET HEALTH COMMAND OVERVIEW
1. Top KPI Summary Grid (5 floating glass cards):
   - "ACTIVE FLEET ENGINES": Value "100 Units" | Sub: "100% telemetry online"
   - "CONFORMAL COVERAGE (80% SLA)": Value "84.0%" | Sub: "+4.0% above contract target"
   - "ANOMALY DETECTION RATE": Value "100.0%" | Sub: "False Alarm Rate: 2.0% (<=5% SLA)"
   - "EARLY WARNING LEAD TIME": Value "38-46 Cycles" | Sub: "Median pre-failure alert window"
   - "UNSCHEDULED GROUNDINGS (AOG)": Value "not a promise" | Sub: "student demo, not a Part 145 approval"
2. Subsystem Health Matrix: 4 circular progress gauges for High Pressure Compressor (HPC), Low Pressure Turbine (LPT), Fan & Shaft Dynamics, and Combustor Gas-Path.
3. Fleet Telemetry & Risk Table:
   - High-density tabular layout with search bar, status filter (ALL, CRITICAL, MEDIUM, WATCH, NORMAL), and sorting.
   - Columns: Unit ID, Flight Regime, Cycle, Conformal RUL [P10 - P50 - P90], Anomaly Deviation (z-dbase), Risk Status Badge, Action Button.
   - Status Badges:
     * CRITICAL: Solid Red badge with pulsing alert beacon
     * MEDIUM: Amber badge
     * WATCH: Sky blue outline badge
     * NORMAL: Muted teal badge
   - Clicking an engine row seamlessly opens Tab 2 for deep drill-down.

### TAB 2: TURBOFAN TELEMETRY DRILL-DOWN & TIME-TRAVEL REPLAY
1. Engine Selector & Replay Scrub Bar:
   - Unit ID dropdown (Engine #1 to #100) + Current Flight Cycle indicator.
   - Interactive Avionics Time-Travel Scrub Bar spanning cycle 1 to failure (e.g. Cycle 192).
   - Scrub bar milestone ticks: "Nominal Baseline", "Early Anomaly Onset (Cycle 148)", "Degradation Knee (Cycle 170)", "Critical Grounding Limit (Cycle 185)".
   - Media controls: Step Back (-1 cycle), Play/Pause (1x, 2x, 5x speed), Step Forward (+1 cycle), Reset to Origin.
2. Conformal Prediction & RUL Uncertainty Chart:
   - Dynamic Chart.js canvas showing the full operational life.
   - Ground truth remaining useful life (dashed white line).
   - Point prediction / Median P50 (solid glowing cyan line #00F5D4).
   - 80% Conformal Prediction Bounds (P10 lower safety cutoff in dashed red/cyan, P90 upper bound in sky blue, with a translucent glowing gradient fill between P10 and P90).
   - Tooltip displaying: Cycle, P10 RUL, P50 RUL, P90 RUL, True RUL, Interval Width, and Anomaly z-score.
3. Telemetry Gas-Path Gauge Grid (6 live dials / bar meters):
   - Total Temp at HPC Outlet (T30 / s3): 1580.4 °R
   - Total Temp at LPT Outlet (T50 / s4): 1402.1 °R
   - Static Pressure at HPC Outlet (Ps30 / s11): 47.2 psia
   - Corrected Core Rotor Speed (Nc / s9): 9054.2 RPM
   - Fan Speed Ratio (s8/s9): 0.284
   - Compressor Pressure Ratio (s11/s7): 1.84

### TAB 3: AUTONOMOUS TRIAGE AGENT & WORK ORDERS
1. Autonomous Decision Engine Banner:
   - Displays current deterministic triage state (Deterministic Rule Engine isolated from LLMs to prevent hallucinated dispatch).
2. Work Order Dispatch Deck:
   - Industrial work order cards with chamfered corners, priority status glow, technician assignment, priority halos, and action buttons.
   - Card details: Order ID (e.g. WO-FD001-U042), Turbofan Unit, Cycle Detected, Severity Tier (CRITICAL / MEDIUM), Assigned Depot, Recommended Maintenance Procedure (e.g., "Boresscope Inspection - HPC Stage 2-4 Blade Tip Erosion").
   - Action controls: "Acknowledge Order", "Complete Maintenance", "Escalate to Human Supervisor".
3. Human-in-the-Loop Exception Queue:
   - Dedicated panel highlighting unconfirmed sensor spikes, frozen telemetry readings, or sensor dropouts that require manual engineer sign-off.
4. Tamper-Evident Cryptographic Audit Ledger (SHA-256):
   - Visual blockchain / block hash chain table with verified chain status badge ("100% INTACT - 0 TAMPERING DETECTED").
   - Columns: Block #, Timestamp, Order ID, Event Type, Action, Previous Hash, Block SHA-256 Digest.
   - "Verify Chain Integrity" interactive button with sub-second recalculation animation.

### TAB 4: MLOPS MODEL RETRAINING & DRIFT MONITOR
1. Champion vs Challenger Tournament Comparison:
   - Side-by-side metric comparison cards with visual diff indicators:
     * Test RMSE: Champion 11.30 vs Challenger 9.82 (-13.1% improvement)
     * NASA Asymmetric Loss: Champion 213 vs Challenger 184 (-13.6% improvement)
     * Conformal Coverage: Champion 84.0% vs Challenger 85.2% (+1.2%)
     * Late Prediction Share: Champion 29.0% vs Challenger 14.8% (-14.2% safer)
   - 4-Gate Automated Promotion Checklist (All green checkmarks):
     [x] RMSE Improvement >= 1.5%
     [x] Conformal Coverage >= 80.0%
     [x] Late Prediction Share <= 15.0%
     [x] Non-increasing Monotonicity Validated
2. Population Stability Index (PSI) Drift Histogram:
   - Visualizing distribution drift across operating regimes and sensor channels with drift alert thresholds (PSI < 0.10 Stable, 0.10-0.20 Moderate, > 0.20 Severe Drift).
3. Streaming Retraining Terminal Console:
   - Monospaced dark console window showing real-time stdout logs of the `ShieldPipeline` and `SelfImprovementEngine` tournament optimization rounds.

Ensure the final design feels authoritative, mathematically rigorous, ultra-modern, and completely free of generic AI template cliches.
```
