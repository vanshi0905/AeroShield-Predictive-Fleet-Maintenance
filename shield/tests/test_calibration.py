import numpy as np
from shield.src.calibrate import CrossConformalCalibrator, tune_late_shift, order_quantiles
from shield.src.evaluate import nasa_score, coverage

def test_conformal_widens_narrow_bands_to_target():
    r = np.random.default_rng(0); n = 4000
    y = r.uniform(0, 125, n); p50 = y + r.normal(0, 12, n); p10, p90 = p50 - 5, p50 + 5     # far too narrow
    age = r.integers(40, 200, n)
    c = CrossConformalCalibrator(0.8, 125.0).fit(p10[:2000], p90[:2000], y[:2000], age[:2000])
    lo, hi = c.widen(p10[2000:], p90[2000:], age[2000:])
    assert coverage(p10[2000:], p90[2000:], y[2000:]) < 0.4 and 0.74 <= coverage(lo, hi, y[2000:]) <= 0.86 and c.q_std > 0

def test_short_history_bucket_is_wider():
    r = np.random.default_rng(1); n = 4000; y = r.uniform(0, 125, n); age = r.integers(5, 200, n)
    noise = np.where(age < 40, 25, 8); p50 = y + r.normal(0, 1, n) * noise
    c = CrossConformalCalibrator(0.8).fit(p50 - 5, p50 + 5, y, age)
    assert c.q_short > c.q_std

def test_late_shift_chosen_when_predictions_run_late():
    r = np.random.default_rng(2); y = r.uniform(5, 125, 3000); p = y + 6 + r.normal(0, 5, 3000)
    assert tune_late_shift(p, y, [0, 1, 2, 3, 4, 5, 6, 8]) >= 3

def test_quantile_order_enforced():
    a, b, c = order_quantiles(np.array([50.0]), np.array([40.0]), np.array([30.0]), 125.0)
    assert a[0] <= b[0] <= c[0]

def test_nasa_penalises_late_more():
    assert nasa_score([60], [50]) > nasa_score([40], [50])
