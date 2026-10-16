import numpy as np, pytest
from shield.src.calibrate import BoundedStepSmoother

def test_recovers_from_single_low_outlier():
    """A4: one noisy low prediction must NOT lock RUL low (the running-minimum ratchet)."""
    s = BoundedStepSmoother(0.3, 5.0, 1.0, 125.0)
    s.smooth_step(1, 80.0)
    g = s.smooth_step(1, 10.0)
    assert g >= 74.0                         # drop bounded by d_max
    out = [s.smooth_step(1, 80.0) for _ in range(10)]
    assert out[-1] > g and out[-1] >= 80 - 1e-6 or out[-1] > 78   # climbs back (u_max per cycle)

def test_running_minimum_would_lock_but_smoother_does_not():
    raw = np.r_[np.full(20, 80.0), 10.0, np.full(30, 80.0)]
    runmin = np.minimum.accumulate(raw)
    sm = BoundedStepSmoother(0.3, 5.0, 1.0, 125.0).smooth_series(raw)
    assert runmin[-1] == 10.0 and sm[-1] > 60

def test_u_max_zero_recovers_old_behaviour_ratchet():
    raw = np.r_[np.full(10, 80.0), 10.0, np.full(30, 80.0)]
    sm = BoundedStepSmoother(1.0, 100.0, 0.0, 125.0).smooth_series(raw)
    assert sm[-1] == 10.0

def test_reset_on_maintenance():
    s = BoundedStepSmoother(); s.smooth_step(7, 20.0); s.reset_engine(7)
    assert s.smooth_step(7, 120.0) == 120.0
