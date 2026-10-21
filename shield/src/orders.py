"""Layer 5 - work orders: lifecycle, budget, de-duplication, keyed HMAC-SHA256 audit, provenance."""
import json, sqlite3, hashlib, hmac, os
from datetime import datetime, timezone

GENESIS = "GENESIS_" + "0" * 32
SEV = ["NORMAL", "WATCH", "MEDIUM", "HIGH", "CRITICAL"]
OPEN = ("AUTO_CREATED", "ACKNOWLEDGED", "QUEUED", "REOPENED")


def now(): return datetime.now(timezone.utc).isoformat()


class OrderManager:
    def __init__(self, db_path="outputs/work_orders.db", subsystem_map=None, medium_budget=10, window_cycles=20,
                 model_version="v1", rule_version="rules-2.1", config_hash="", stale_factor=2.0, reopen_window=20, reopen_limit=3,
                 hmac_key=None):
        self.db_path, self.sub = db_path, subsystem_map or {}
        self.budget, self.win = medium_budget, window_cycles
        self.mv, self.rv, self.ch = model_version, rule_version, config_hash
        self.stale_factor, self.reopen_window, self.reopen_limit = stale_factor, reopen_window, reopen_limit
        # This string is published. It only matches the sample ledgers already
        # committed under outputs/. It is not a private seal.
        published_demo_key = "aeroshield-v3-secret-key"
        key_str = hmac_key or os.environ.get("AEROSHIELD_HMAC_KEY") or published_demo_key
        env_mode = os.environ.get("AEROSHIELD_ENV", "development").lower()
        if env_mode in ("production", "prod") and key_str == published_demo_key:
            raise RuntimeError(
                "AEROSHIELD_HMAC_KEY must be a private value in production. "
                "The published demo key only matches the checked-in sample ledgers, "
                "and those ledgers are not a regulatory record."
            )
        self.hmac_key = key_str.encode() if isinstance(key_str, str) else key_str
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS work_orders(order_id TEXT PRIMARY KEY, engine_unit INTEGER, severity TEXT,
            cycle INTEGER, p10 REAL, p50 REAL, p90 REAL, top_sensors TEXT, suspect_subsystem TEXT, recommended_action TEXT,
            due_cycle INTEGER, status TEXT, exception_text TEXT, model_version TEXT, rule_version TEXT, config_hash TEXT,
            window_id INTEGER, reopen_count INTEGER DEFAULT 0, completed_cycle INTEGER, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_log(entry_id INTEGER PRIMARY KEY AUTOINCREMENT, prev_hash TEXT,
            current_hash TEXT, timestamp TEXT, order_id TEXT, event_type TEXT, details TEXT)""")
        self.conn.commit()

    def close(self): self.conn.commit(); self.conn.close()

    # ---------- audit ----------
    def _compute_hmac(self, prev, ts, order_id, event, details_str):
        payload = f"{prev}|{ts}|{order_id}|{event}|{details_str}".encode()
        return hmac.new(self.hmac_key, payload, hashlib.sha256).hexdigest()

    def _last_hash(self):
        r = self.conn.execute("SELECT current_hash FROM audit_log ORDER BY entry_id DESC LIMIT 1").fetchone()
        return r[0] if r else GENESIS

    def _audit(self, order_id, event, details):
        prev, ts = self._last_hash(), now()
        d = json.dumps({**details, "model_version": self.mv, "rule_version": self.rv, "config_hash": self.ch}, sort_keys=True)
        h = self._compute_hmac(prev, ts, order_id, event, d)
        self.conn.execute("INSERT INTO audit_log(prev_hash,current_hash,timestamp,order_id,event_type,details) VALUES(?,?,?,?,?,?)",
                          (prev, h, ts, order_id, event, d))

    def verify_audit_chain(self):
        rows = self.conn.execute("SELECT entry_id,prev_hash,current_hash,timestamp,order_id,event_type,details FROM audit_log ORDER BY entry_id").fetchall()
        exp = GENESIS
        for eid, prev, cur, ts, oid, ev, det in rows:
            if prev != exp: return False, f"Broken chain at entry {eid}"
            if self._compute_hmac(prev, ts, oid, ev, det) != cur:
                return False, f"Tampered entry {eid}: recomputed hash mismatch"
            exp = cur
        return True, f"Verified {len(rows)} audit entries. Integrity 100% intact."

    # ---------- orders ----------
    def _open_order(self, unit):
        return self.conn.execute(f"SELECT order_id,severity,status FROM work_orders WHERE engine_unit=? AND status IN {OPEN} AND order_id NOT LIKE 'EX-%'", (unit,)).fetchone()

    def _open_exception(self, unit):
        return self.conn.execute("SELECT order_id,exception_text FROM work_orders WHERE engine_unit=? AND status='NEEDS_HUMAN'", (unit,)).fetchone()

    def process_agent_decision(self, d, drivers=None, subsystem=None):
        """drivers: list of top-3 sensor names. Returns order_id or None."""
        unit, cyc, st = d["unit"], d["cycle"], d["status"]
        if st in ("NORMAL", "WATCH"): return None
        drivers = drivers or []
        subsystem = subsystem or (self.sub.get(drivers[0], "General turbofan wear") if drivers else "General turbofan wear")
        c = self.conn.cursor(); t = now()
        if st == "NEEDS_HUMAN":
            ex = self._open_exception(unit)
            if ex:
                if ex[1] != d["exception_reason"]:
                    c.execute("UPDATE work_orders SET exception_text=?,cycle=?,updated_at=? WHERE order_id=?", (d["exception_reason"], cyc, t, ex[0]))
                    self._audit(ex[0], "EXCEPTION_UPDATED", {"reason": d["exception_reason"], "cycle": cyc})
                return ex[0]
            oid = f"EX-{unit:04d}-{cyc:03d}"
            c.execute("INSERT OR REPLACE INTO work_orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (oid, unit, d.get("unconfirmed_severity", "NORMAL"), cyc, d["p10"], d["p50"], d["p90"], ", ".join(drivers), subsystem,
                       d["action"], None, "NEEDS_HUMAN", d["exception_reason"], self.mv, self.rv, self.ch, cyc // self.win, 0, None, t, t))
            self._audit(oid, "EXCEPTION_RAISED", {"reason": d["exception_reason"], "cycle": cyc})
            return oid
        sev = d["severity"]; win = cyc // self.win
        ex = self.conn.execute("SELECT order_id FROM work_orders WHERE engine_unit=? AND status='COMPLETED' ORDER BY completed_cycle DESC LIMIT 1", (unit,)).fetchone()
        o = self._open_order(unit)
        if o:
            oid, old, ost = o
            if SEV.index(sev) > SEV.index(old):
                status = "AUTO_CREATED" if ost != "ACKNOWLEDGED" else "ACKNOWLEDGED"
                c.execute("UPDATE work_orders SET severity=?,cycle=?,p10=?,p50=?,p90=?,top_sensors=?,suspect_subsystem=?,recommended_action=?,due_cycle=?,status=?,updated_at=? WHERE order_id=?",
                          (sev, cyc, d["p10"], d["p50"], d["p90"], ", ".join(drivers), subsystem, d["action"], cyc + (d["due_in_cycles"] or 0), status, t, oid))
                self._audit(oid, "ORDER_ESCALATED", {"from": old, "to": sev, "cycle": cyc})
            return oid
        status = "AUTO_CREATED"
        if sev == "MEDIUM":
            n = self.conn.execute("SELECT COUNT(*) FROM work_orders WHERE severity='MEDIUM' AND window_id=? AND status IN ('AUTO_CREATED','ACKNOWLEDGED')", (win,)).fetchone()[0]
            if n >= self.budget: status = "QUEUED"
        oid = f"WO-{unit:04d}-{cyc:03d}"
        # reopened shortly after completion?
        reopen = 0
        r = self.conn.execute("SELECT completed_cycle,reopen_count FROM work_orders WHERE engine_unit=? AND status='COMPLETED' ORDER BY completed_cycle DESC LIMIT 1", (unit,)).fetchone()
        if r and r[0] is not None and cyc - r[0] <= self.reopen_window:
            reopen = r[1] + 1; status = "REOPENED" if status == "AUTO_CREATED" else status
        c.execute("INSERT OR REPLACE INTO work_orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (oid, unit, sev, cyc, d["p10"], d["p50"], d["p90"], ", ".join(drivers), subsystem, d["action"],
                   cyc + (d["due_in_cycles"] or 0), status, None, self.mv, self.rv, self.ch, win, reopen, None, t, t))
        self._audit(oid, "ORDER_REOPENED" if reopen else ("ORDER_QUEUED" if status == "QUEUED" else "ORDER_CREATED"),
                    {"severity": sev, "cycle": cyc, "status": status})
        if reopen >= self.reopen_limit:
            return self.process_agent_decision({**d, "status": "NEEDS_HUMAN", "exception_reason": f"Order reopened {reopen} times", "action": "Repeated failures - root-cause review."}, drivers)
        return oid

    def release_queued(self, window):
        """New window opens: QUEUED MEDIUM orders (lowest P10 first) become AUTO_CREATED within budget. Nothing is dropped."""
        n = self.conn.execute("SELECT COUNT(*) FROM work_orders WHERE severity='MEDIUM' AND window_id=? AND status IN ('AUTO_CREATED','ACKNOWLEDGED')", (window,)).fetchone()[0]
        rows = self.conn.execute("SELECT order_id FROM work_orders WHERE status='QUEUED' ORDER BY p10").fetchall()
        for (oid,) in rows[:max(self.budget - n, 0)]:
            self.conn.execute("UPDATE work_orders SET status='AUTO_CREATED',window_id=?,updated_at=? WHERE order_id=?", (window, now(), oid))
            self._audit(oid, "ORDER_RELEASED", {"window": window})

    def acknowledge(self, order_id, who="operator"):
        self.conn.execute("UPDATE work_orders SET status='ACKNOWLEDGED',updated_at=? WHERE order_id=? AND status IN ('AUTO_CREATED','REOPENED','QUEUED','NEEDS_HUMAN')", (now(), order_id))
        self._audit(order_id, "ACKNOWLEDGED", {"by": who}); self.conn.commit()

    def complete(self, order_id, cycle, who="operator", outcome="serviced_before_failure"):
        """Only a completion event closes an order. Engine becomes a (censored) labelled engine for retraining."""
        self.conn.execute("UPDATE work_orders SET status='COMPLETED',completed_cycle=?,updated_at=? WHERE order_id=?", (cycle, now(), order_id))
        self._audit(order_id, "COMPLETED", {"by": who, "cycle": cycle, "outcome": outcome}); self.conn.commit()

    def flag_stale(self, current_cycle):
        """Open, unacknowledged > STALE_FACTOR x due window -> human queue. Returns ids flagged."""
        rows = self.conn.execute("SELECT order_id,cycle,due_cycle FROM work_orders WHERE status IN ('AUTO_CREATED','REOPENED')").fetchall()
        out = []
        for oid, cyc, due in rows:
            window = max((due or cyc) - cyc, 10)
            if current_cycle - cyc > self.stale_factor * window:
                self.conn.execute("UPDATE work_orders SET status='NEEDS_HUMAN',exception_text='STALE: unacknowledged beyond %sx due window',updated_at=? WHERE order_id=?" % self.stale_factor, (now(), oid))
                self._audit(oid, "STALE_ESCALATED", {"cycle": current_cycle}); out.append(oid)
        self.conn.commit(); return out
