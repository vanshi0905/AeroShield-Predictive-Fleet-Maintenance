"""Problem C2: every exception rule of design section 7.6 gets a test with FORCED bad input."""
import numpy as np, pandas as pd, pytest
from shield.src.agent import TriageAgent
from shield.src.checks import SensorQualityGate, sensor_agreement
from shield.src.orders import OrderManager

SENSORS = ["s2", "s3", "s4", "s7", "s8", "s11", "s12", "s13"]

def mk_stream(n=30, seed=0):
    r = np.random.default_rng(seed)
    d = pd.DataFrame({"unit": 1, "cycle": np.arange(1, n + 1)})
    for s in SENSORS: d[s] = 100 + r.normal(0, 1, n)
    return d

def gate_for_train():
    tr = pd.concat([mk_stream(80, k).assign(unit=k + 1) for k in range(5)], ignore_index=True)
    return SensorQualityGate(SENSORS).fit(tr)

def test_dropout_over_20pct():
    g = gate_for_train(); d = mk_stream()
    d.loc[d.index[-1], SENSORS[:4]] = np.nan                    # 50% of sensors blank on last row
    f = g.flags(d)
    assert bool(f["dropout"].iat[-1]) and not f["ok"].iat[-1]
    dec = TriageAgent().evaluate(1, 30, 20, 35, 50, dq=(False, f["reason"].iat[-1]))
    assert dec["status"] == "NEEDS_HUMAN" and "Data-quality" in dec["exception_reason"]

def test_stuck_sensor():
    g = gate_for_train(); d = mk_stream(); d.loc[d.index[-8:], "s11"] = d["s11"].iat[-8]
    f = g.flags(d); assert bool(f["stuck"].iat[-1]) and not f["ok"].iat[-1]

def test_range_violation_and_jump_spike():
    g = gate_for_train(); d = mk_stream(); d.loc[d.index[-1], "s7"] += 10 * 25     # ~10 SD+ spike
    f = g.flags(d)
    assert bool(f["range"].iat[-1]) and bool(f["jump"].iat[-1]) and not f["ok"].iat[-1]

def test_clean_stream_not_flagged():
    g = gate_for_train(); assert g.flags(mk_stream())["ok"].all()

def test_too_few_sensors_agree_blocks_severe():
    dev = np.array([8.0, 0, 0, 0, 0, 0, 0, 0])                   # one sensor far away, others unchanged
    passed, n = sensor_agreement(dev, 3, 3.0); assert not passed and n == 1
    d = TriageAgent().evaluate(1, 50, 10, 20, 30, agree=(passed, n))
    assert d["status"] == "NEEDS_HUMAN" and d["severity"] != "CRITICAL" and "too few sensors" in d["exception_reason"]

def test_enough_sensors_agree_allows_severe():
    assert sensor_agreement(np.array([4, 5, 3.5, 0, 0]), 3, 3.0)[0]

def test_wide_interval_on_severe():
    d = TriageAgent({"MAX_WIDTH": 60}).evaluate(1, 50, 10, 20, 90)
    assert d["status"] == "NEEDS_HUMAN" and "Interval" in d["exception_reason"]

def test_anomaly_persistent_while_rul_high():
    d = TriageAgent().evaluate(1, 50, 100, 120, 135, anomaly_alert=True)
    assert d["status"] == "NEEDS_HUMAN" and "Conflicting" in d["exception_reason"]

def test_model_disagreement():
    d = TriageAgent({"DISAGREE_CYCLES": 25}).evaluate(1, 50, 20, 30, 40, second_model_p50=70)
    assert d["status"] == "NEEDS_HUMAN" and "disagreement" in d["exception_reason"].lower()

def test_repeated_reopen_goes_to_human(tmp_path):
    om = OrderManager(str(tmp_path / "o.db"), reopen_limit=3)
    dec = {"unit": 5, "severity": "HIGH", "status": "AUTO_CREATED", "exception_reason": None, "p10": 30, "p50": 40, "p90": 55, "due_in_cycles": 10, "action": "x"}
    c = 100
    for _ in range(4):
        om.process_agent_decision({**dec, "cycle": c}); oid = f"WO-0005-{c:03d}"; om.complete(oid, c + 1); c += 5
    rows = om.conn.execute("SELECT status FROM work_orders WHERE engine_unit=5").fetchall()
    assert ("NEEDS_HUMAN",) in rows
