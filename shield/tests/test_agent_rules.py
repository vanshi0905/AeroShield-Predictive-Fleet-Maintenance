from shield.src.agent import TriageAgent

def run(agent, unit, seq):
    return [agent.evaluate(unit, i, *x) for i, x in enumerate(seq)]

def test_upgrade_needs_three_cycles():
    a = TriageAgent({"PERSIST": 3})
    d = run(a, 1, [(12, 22, 30)] * 3)
    assert d[0]["unconfirmed_severity"] == "CRITICAL" and d[0]["severity"] == "NORMAL"
    assert d[1]["severity"] == "NORMAL"
    assert d[2]["severity"] == "CRITICAL" and d[2]["status"] == "AUTO_CREATED" and d[2]["due_in_cycles"] == 0

def test_one_noisy_cycle_cannot_raise_alarm():
    a = TriageAgent(); d = run(a, 2, [(90, 100, 110), (10, 20, 30), (90, 100, 110), (90, 100, 110)])
    assert all(x["severity"] == "NORMAL" for x in d)

def test_confirmed_is_least_severe_of_last_three():
    a = TriageAgent(); d = run(a, 3, [(40, 70, 100), (12, 22, 30), (12, 22, 30)])   # MEDIUM, CRIT, CRIT -> MEDIUM
    assert d[2]["severity"] == "MEDIUM"

def test_downgrade_needs_five_cycles():
    a = TriageAgent(); run(a, 4, [(12, 22, 30)] * 3)
    d = run(a, 4, [(100, 120, 130)] * 5)
    assert d[3]["severity"] == "CRITICAL" and d[4]["severity"] == "NORMAL"

def test_watch_and_medium_rules():
    a = TriageAgent()
    assert a.raw_severity(80, 100, True) == "MEDIUM" and a.raw_severity(80, 105, True) == "WATCH"
    assert a.raw_severity(60, 75, False) == "MEDIUM" and a.raw_severity(60, 45, False) == "HIGH"
    assert a.raw_severity(14, 90, False) == "CRITICAL"          # P10 rule (conservative bound)

def test_watch_status_and_no_order():
    a = TriageAgent(); d = run(a, 5, [(100, 108, 120, True)] * 3)
    assert d[2]["status"] in ("WATCH", "NORMAL") and d[2]["status"] != "AUTO_CREATED"
