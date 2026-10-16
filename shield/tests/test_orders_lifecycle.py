from shield.src.orders import OrderManager

def dec(unit, cyc, sev="HIGH", p10=30):
    due = {"CRITICAL": 0, "HIGH": 10, "MEDIUM": 30}[sev]
    return {"unit": unit, "cycle": cyc, "severity": sev, "status": "AUTO_CREATED", "exception_reason": None, "p10": p10, "p50": 40, "p90": 60, "due_in_cycles": due, "action": "a"}

def test_single_open_order_and_escalation(tmp_path):
    om = OrderManager(str(tmp_path / "a.db"))
    a = om.process_agent_decision(dec(1, 100, "MEDIUM")); b = om.process_agent_decision(dec(1, 105, "CRITICAL")); c = om.process_agent_decision(dec(1, 106, "HIGH"))
    assert a == b == c
    n = om.conn.execute("SELECT COUNT(*) FROM work_orders WHERE engine_unit=1").fetchone()[0]; assert n == 1
    assert om.conn.execute("SELECT severity FROM work_orders").fetchone()[0] == "CRITICAL"     # never auto-downgraded
    assert om.conn.execute("SELECT COUNT(*) FROM audit_log WHERE event_type='ORDER_ESCALATED'").fetchone()[0] == 1

def test_acknowledge_complete_closes_only_on_event(tmp_path):
    om = OrderManager(str(tmp_path / "b.db")); oid = om.process_agent_decision(dec(2, 100))
    om.acknowledge(oid); assert om.conn.execute("SELECT status FROM work_orders").fetchone()[0] == "ACKNOWLEDGED"
    om.process_agent_decision({**dec(2, 110), "severity": "NORMAL", "status": "NORMAL"})
    assert om.conn.execute("SELECT status FROM work_orders").fetchone()[0] == "ACKNOWLEDGED"
    om.complete(oid, 120); assert om.conn.execute("SELECT status FROM work_orders").fetchone()[0] == "COMPLETED"

def test_medium_budget_queues_and_releases_without_dropping(tmp_path):
    om = OrderManager(str(tmp_path / "c.db"), medium_budget=2, window_cycles=20)
    for u in range(1, 6): om.process_agent_decision(dec(u, 100 + u, "MEDIUM", p10=50 - u))
    st = [r[0] for r in om.conn.execute("SELECT status FROM work_orders ORDER BY engine_unit")]
    assert st.count("QUEUED") == 3 and st.count("AUTO_CREATED") == 2
    om.process_agent_decision(dec(9, 101, "CRITICAL")); assert om.conn.execute("SELECT status FROM work_orders WHERE engine_unit=9").fetchone()[0] == "AUTO_CREATED"  # CRITICAL never capped
    om.release_queued(6)
    assert om.conn.execute("SELECT COUNT(*) FROM work_orders WHERE status='QUEUED'").fetchone()[0] == 1       # 2 released, 1 still held
    assert om.conn.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0] == 6                              # nothing dropped

def test_stale_escalation(tmp_path):
    om = OrderManager(str(tmp_path / "d.db")); om.process_agent_decision(dec(3, 100, "HIGH"))
    assert om.flag_stale(105) == [] and len(om.flag_stale(140)) == 1
    assert om.conn.execute("SELECT status FROM work_orders").fetchone()[0] == "NEEDS_HUMAN"

def test_exception_dedup(tmp_path):
    om = OrderManager(str(tmp_path / "e.db"))
    ex = {"unit": 4, "cycle": 50, "severity": "NORMAL", "status": "NEEDS_HUMAN", "exception_reason": "stuck", "p10": 1, "p50": 2, "p90": 3, "due_in_cycles": None, "action": "x"}
    om.process_agent_decision(ex); om.process_agent_decision({**ex, "cycle": 51})
    assert om.conn.execute("SELECT COUNT(*) FROM work_orders WHERE engine_unit=4").fetchone()[0] == 1
