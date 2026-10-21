# Layer 3: Autonomous Triage & Regulatory Compliance Ledger

**Primary Code Files**:
* [`shield/src/agent.py`](../shield/src/agent.py) — Deterministic 4-tier operational triage matrix
* [`shield/src/orders.py`](../shield/src/orders.py) — SQLite work order lifecycle state machine & tamper-evident SHA-256 cryptographic audit ledger
* [`shield/src/checks.py`](../shield/src/checks.py) — Sensor spike and model disagreement human exception queue

---

## 1. System Role & Architecture

Layer 3 serves as the autonomous operational controller of the AeroShield platform. In safety-critical aviation, ungrounded probabilistic language models must never be permitted to authorize physical maintenance dispatches or aircraft groundings. Layer 3 replaces LLM hallucination with a deterministic 4-tier rule matrix, routes telemetry edge cases to certified human specialists, manages an ACID-compliant SQLite state machine, and cryptographically signs every action to an immutable SHA-256 ledger.

```
Inference Output from Layer 2 (P10, P50, P90, Anomaly Score, Secondary Opinion)
   │
   ├───────────────────────────────────────────────────────┐
   ▼                                                       ▼
1. Exception Detection Gate                        2. Deterministic 4-Tier Severity Matrix
   • Sensor Spike Check (|z| > 4.5)                   • Tier 1 (Critical): P50 <= 25 cyc
   • Model Disagreement (|P50_1 - P50_2| > 25)        • Tier 2 (High):     P50 <= 50 cyc
   │                                                  • Tier 3 (Medium):   P50 <= 80 or Anom+P50<=100
   ▼ (If Triggered)                                   • Tier 4 (Normal):   P50 > 80 cyc
3. Human Exception Review Queue                       │
   • Work Order locked in NEEDS_HUMAN                 ▼
   • Requires certified specialist override       4. SQLite State Machine
   │                                                  • DRAFT -> DISPATCHED -> COMPLETED
   └───────────────────────────┬──────────────────────┘
                               │
                               ▼
5. Demo HMAC hash chain (not an FAA or EASA record)
   • Merkle block linkage: Hash_i = SHA256(Entry || PrevHash || TS || Order || Action || Signer)
   • 100% Tamper-Evident Historical Verification
```

---

## 2. Core Operational Modules

### A. Deterministic 4-Tier Severity Matrix
The autonomous triage engine processes conformal predictions and anomaly indicators to assign engines to four distinct operational tiers:

| Tier | Severity | Trigger Criteria | Action Protocol | Maintenance SLA |
| :--- | :---: | :--- | :--- | :---: |
| **Tier 1** | **CRITICAL** | $P_{50} \le 25$ flight cycles | Immediate Aircraft on Ground (AOG) grounding; emergency depot bay reservation; engine replacement dispatch. | Immediate (0 cycles) |
| **Tier 2** | **HIGH** | $P_{50} \le 50$ flight cycles | Priority overhaul slot allocation; provision replacement compressor blisk or turbine blades. | Within 5 cycles |
| **Tier 3** | **MEDIUM** | $P_{50} \le 80$ cycles **OR** ($A_t \ge 3.0$ and $P_{50} \le 100$) | Scheduled borescope inspection during next planned turnaround. Constrained by fleet budget guardrails (max 10 orders per window). | Within 20 cycles |
| **Tier 4** | **NORMAL** | $P_{50} > 80$ flight cycles | Engine cleared for full operational envelope; routine health monitoring. | Standard cycle |

### B. Human Specialist Review Queue
Automated physical actions are halted whenever telemetry exhibits anomalies that indicate instrument failure or model uncertainty:
1. **Sensor Spike Anomaly**: If any normalized sensor exceeds $|z_s| > 4.5\sigma$, the system assumes an instrumentation or wiring failure rather than physical engine wear.
2. **Model Consensus Disagreement**: If the primary quantile model and secondary non-linear estimator differ by $> 25$ cycles ($|\hat{q}_{0.50} - \hat{y}_{\text{sec}}| > 25$).

Such units are flagged with status `NEEDS_HUMAN` and added to the Human Exception Queue. The engine cannot be cleared until a certified reliability engineer reviews raw telemetry and logs an authorized override.

### C. SQLite Work Order Lifecycle State Machine
Work orders follow a strict, ACID-compliant SQLite state transition flow:
* `DRAFT`: Generated automatically by Tier 1–3 triage or exception triggers.
* `DISPATCHED`: Authorized either autonomously (for clear-cut Tier 1/2 criteria) or manually by a fleet maintenance controller.
* `COMPLETED`: Maintenance performed and signed off by depot technicians.
* `OVERRIDDEN`: Human review exception inspected and approved.

### D. Demo HMAC hash chain
Work-order events are appended as an HMAC-SHA256 chain so a reviewer can see that a sample row was not edited in place. The key that seals `outputs/*/work_orders.db` is published in this repository. That makes the chain a demo. It is not an FAA Part 145 or EASA M.A.306 maintenance record, and someone who has the key can recompute it.

AeroShield enforces this via a cryptographically linked SHA-256 blockchain ledger:
1. **Genesis Block**: Sealed with initial root nonce:
   $$\text{Hash}_0 = \text{SHA256}(\text{"GENESIS\_"} \parallel 0^{32})$$
2. **Successive Block Sealing**: For entry $i \ge 1$:
   $$\text{Hash}_i = \text{SHA256}\left(\text{EntryID}_i \parallel \text{Hash}_{i-1} \parallel \text{Timestamp}_i \parallel \text{OrderID}_i \parallel \text{Action}_i \parallel \text{Operator}_i \parallel \text{Details}_i\right)$$
3. **Live Verification**:
   The entire historical chain of custody is verified in sub-second $\mathcal{O}(N)$ time:
   * Every block recomputes its SHA-256 hash from its stored payload.
   * Every block validates that its `prev_hash` strictly matches $\text{Hash}_{i-1}$.
   * If any row in the SQLite database is manually tampered with, the parent hash linkage breaks instantly and triggers an integrity alert on `/api/audit-verify`.

---

## 3. Unit Verification & Test Proofs

Covered in automated test suites:
* [`shield/tests/test_agent_rules.py`](../shield/tests/test_agent_rules.py): Validates deterministic 4-tier assignment and turnaround window budget caps.
* [`shield/tests/test_exceptions.py`](../shield/tests/test_exceptions.py): Validates sensor spike isolation and model divergence exception queue routing.
* [`shield/tests/test_orders_lifecycle.py`](../shield/tests/test_orders_lifecycle.py): Validates SQLite state transitions and operator recording.
* [`shield/tests/test_audit_chain.py`](../shield/tests/test_audit_chain.py): Validates SHA-256 cryptographic parent linkage and simulates bit-level tampering detection.
