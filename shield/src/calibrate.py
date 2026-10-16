"""Layer 2 - quantile RUL models, late-bias shift, bounded-step smoother, cross-conformal widening."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .evaluate import nasa_score, rmse


def _hgb(q, seed):
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=150, learning_rate=0.08,
                                         min_samples_leaf=40, l2_regularization=1.0, random_state=seed)


class QuantileRULModel:
    """HistGradientBoosting P10/P50/P90 (quantile loss). Shift is applied separately (see tune_late_shift)."""

    def __init__(self, cap=125.0, random_state=42):
        self.cap, self.seed = cap, random_state
        self.m = {q: _hgb(q, random_state) for q in (0.1, 0.5, 0.9)}

    def fit(self, X, y, sample_weight=None):
        y = np.clip(y, 0, self.cap)
        for q in self.m.values():
            q.fit(X, y, sample_weight=sample_weight)
        return self

    def predict_raw(self, X):
        return tuple(np.clip(self.m[q].predict(X), 0, self.cap) for q in (0.1, 0.5, 0.9))


class RidgeRUL:
    """Non-linear second opinion estimator (HistGradientBoosting) tracking non-linear degradation
    and preventing false model disagreement exceptions."""

    def __init__(self, cap=125.0, random_state=42):
        self.cap = cap
        self.seed = random_state
        self.m = HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=100,
            learning_rate=0.08,
            min_samples_leaf=25,
            l2_regularization=1.0,
            random_state=random_state,
        )

    def fit(self, X, y, sample_weight=None):
        self.m.fit(X, np.clip(y, 0, self.cap), sample_weight=sample_weight)
        return self

    def predict(self, X):
        return np.clip(self.m.predict(X), 0, self.cap)


def tune_late_shift(p50, y, grid, max_rmse_rise=0.10):
    """Shift d (cycles) that minimises NASA score with RMSE rise <= 10% (problem A2)."""
    base = rmse(p50, y); best, best_n = 0.0, nasa_score(p50, y)
    for d in grid:
        pr = np.clip(p50 - d, 0, None)
        if rmse(pr, y) <= base * (1 + max_rmse_rise):
            n = nasa_score(pr, y)
            if n < best_n:
                best, best_n = float(d), n
    return best


class BoundedStepSmoother:
    """EWMA then clip(y_prev - d_max, y_prev + u_max). u_max=0 would recover the old running minimum."""

    def __init__(self, alpha=0.3, d_max=5.0, u_max=1.0, cap=125.0):
        self.alpha, self.d_max, self.u_max, self.cap = alpha, d_max, u_max, cap
        self.state = {}

    def reset_engine(self, unit):
        self.state.pop(unit, None)

    def smooth_step(self, unit, raw):
        if unit not in self.state:
            y = float(np.clip(raw, 0, self.cap))
        else:
            yp = self.state[unit]
            e = self.alpha * raw + (1 - self.alpha) * yp
            y = float(np.clip(np.clip(e, yp - self.d_max, yp + self.u_max), 0, self.cap))
        self.state[unit] = y
        return y

    def smooth_series(self, raw, unit=0):
        self.reset_engine(unit)
        return np.array([self.smooth_step(unit, v) for v in raw])


def smooth_by_engine(units, series, alpha, d_max, u_max, cap):
    """Apply the smoother to every engine's time-ordered series (rows already ordered by unit, cycle)."""
    out = np.empty_like(series, dtype=float)
    for u in np.unique(units):
        idx = np.where(units == u)[0]
        sm = BoundedStepSmoother(alpha, d_max, u_max, cap)
        out[idx] = sm.smooth_series(series[idx], u)
    return out


def order_quantiles(p10, p50, p90, cap):
    p50 = np.clip(p50, 0, cap)
    return np.clip(np.minimum(p10, p50), 0, cap), p50, np.clip(np.maximum(p90, p50), 0, cap)


class CrossConformalCalibrator:
    """Widen P10/P90 by q = empirical quantile of s=max(P10-y, y-P90) at level ceil((n+1)*c)/n.
    Separate q for short-history engines. Approximate average coverage - not per-engine (problem A1/A7)."""

    def __init__(self, target=0.80, cap=125.0, short_cycles=40):
        self.target, self.cap, self.short = target, cap, short_cycles
        self.q_std = self.q_short = 0.0
        self.n_std = self.n_short = 0

    def _q(self, p10, p90, y):
        s = np.maximum(p10 - y, y - p90); n = len(s)
        lvl = min(1.0, np.ceil((n + 1) * self.target) / n)
        return float(np.quantile(s, lvl))

    def fit(self, p10, p90, y, age):
        std = age >= self.short
        self.q_std, self.n_std = self._q(p10[std], p90[std], y[std]), int(std.sum())
        sh = ~std
        self.n_short = int(sh.sum())
        self.q_short = self._q(p10[sh], p90[sh], y[sh]) if sh.sum() >= 20 else self.q_std + 3.0
        return self

    def widen(self, p10, p90, age):
        q = np.where(np.asarray(age) < self.short, self.q_short, self.q_std)
        return np.clip(p10 - q, 0, self.cap), np.clip(p90 + q, 0, self.cap)

    def calibrate(self, p10, p90, engine_age=50):
        a, b = self.widen(np.array([p10]), np.array([p90]), np.array([engine_age]))
        return float(a[0]), float(b[0])
