"""Layer 4 - deterministic rule-based triage agent (NO LLM). Every decision traces to a rule + a number."""
from collections import deque

RANK = {"NORMAL": 0, "WATCH": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
INV = {v: k for k, v in RANK.items()}
ACTIONS = {
    "CRITICAL": ("Ground engine; immediate inspection and component swap.", 0),
    "HIGH": ("Schedule maintenance in next available window.", 10),
    "MEDIUM": ("Plan inspection at next planned stop.", 30),
    "WATCH": ("Keep monitoring; no order.", None),
    "NORMAL": ("Routine operation.", None),
}


class TriageAgent:
    def __init__(self, config=None):
        c = config or {}
        g = c.get
        self.crit_p10, self.crit_p50 = g("CRIT_P10", 15), g("CRIT_P50", 25)
        self.high_p50, self.med_p50 = g("HIGH_P50", 50), g("MED_P50", 80)
        self.anom_med_p50, self.conflict_p50 = g("ANOM_MED_P50", 100), g("CONFLICT_P50", 110)
        self.max_width, self.persist = g("MAX_WIDTH", 60), g("PERSIST", 3)
        self.down_persist, self.disagree = g("DOWNGRADE_PERSIST", 5), g("DISAGREE_CYCLES", 25)
        self.hist, self.confirmed = {}, {}

    def reset(self, unit):
        self.hist.pop(unit, None); self.confirmed.pop(unit, None)

    def _exc(self, unit, cycle, p10, p50, p90, raw_sev, reason, action):
        return {"unit": unit, "cycle": cycle, "severity": "NORMAL", "unconfirmed_severity": raw_sev,
                "status": "NEEDS_HUMAN", "exception_reason": reason, "p10": float(p10), "p50": float(p50),
                "p90": float(p90), "due_in_cycles": None, "action": action}

    def raw_severity(self, p10, p50, anomaly):
        if p10 <= self.crit_p10 or p50 <= self.crit_p50: return "CRITICAL"
        if p50 <= self.high_p50: return "HIGH"
        if p50 <= self.med_p50 or (anomaly and p50 <= self.anom_med_p50): return "MEDIUM"
        return "WATCH" if anomaly else "NORMAL"

    def evaluate(self, unit, cycle, p10, p50, p90, anomaly_alert=False, dq=None, agree=None, second_model_p50=None):
        """dq=(ok, reason) from the data-quality gate; agree=(passed, count); returns decision dict."""
        # 1 data-quality gate
        if dq is not None and not dq[0]:
            return self._exc(unit, cycle, p10, p50, p90, "NORMAL", f"Data-quality: {dq[1]}",
                             "Sensor/transmission fault suspected - model not trusted; route to technician.")
        raw = self.raw_severity(p10, p50, anomaly_alert)
        # 2 conflicting signals
        if anomaly_alert and p50 > self.conflict_p50:
            return self._exc(unit, cycle, p10, p50, p90, raw, f"Conflicting signals: anomaly alert while P50={p50:.0f} > {self.conflict_p50}",
                             "Engineering review of anomaly vs RUL disagreement.")
        # 3 model disagreement
        if second_model_p50 is not None and abs(p50 - second_model_p50) > self.disagree:
            return self._exc(unit, cycle, p10, p50, p90, raw, f"Model disagreement: {p50:.0f} vs {second_model_p50:.0f} (> {self.disagree})",
                             "Models diverge - specialist triage.")
        # 4/5 gates for HIGH/CRITICAL
        if raw in ("HIGH", "CRITICAL"):
            if agree is not None and not agree[0]:
                return self._exc(unit, cycle, p10, p50, p90, raw, f"Deviation on too few sensors ({agree[1]} agree)",
                                 "Isolated sensor deviation - inspect sensor line before acting.")
            if p90 - p10 > self.max_width:
                return self._exc(unit, cycle, p10, p50, p90, raw, f"Interval {p90 - p10:.0f} cycles > {self.max_width}",
                                 "Uncertain trajectory - manual review.")
        # 6 confirmation / anti-flapping: upgrade = least severe of last PERSIST; downgrade needs DOWNGRADE_PERSIST
        h = self.hist.setdefault(unit, deque(maxlen=max(self.persist, self.down_persist)))
        cur = self.confirmed.get(unit, "NORMAL")
        h.append(RANK[raw]); r = list(h); new = RANK[cur]
        if len(r) >= self.persist and min(r[-self.persist:]) > RANK[cur]:
            new = min(r[-self.persist:])
        elif len(r) >= self.down_persist and max(r[-self.down_persist:]) < RANK[cur]:
            new = max(r[-self.down_persist:])
        sev = INV[new]; self.confirmed[unit] = sev
        action, due = ACTIONS[sev]
        status = {"CRITICAL": "AUTO_CREATED", "HIGH": "AUTO_CREATED", "MEDIUM": "AUTO_CREATED", "WATCH": "WATCH"}.get(sev, "NORMAL")
        return {"unit": unit, "cycle": cycle, "severity": sev, "unconfirmed_severity": raw, "status": status,
                "exception_reason": None, "p10": float(p10), "p50": float(p50), "p90": float(p90),
                "due_in_cycles": due, "action": action}
