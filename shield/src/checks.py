"""Sensor-fault checks (data-quality gate, design 4.6) - per row, causal, vectorised + single-row API."""
import numpy as np
import pandas as pd
from .data import SENS


class SensorQualityGate:
    def __init__(self, sensors, max_nan=0.20, stuck_window=5, range_margin=0.30, jump_k=10.0):
        self.sensors = list(sensors); self.max_nan, self.stuck_window = max_nan, stuck_window
        self.range_margin, self.jump_k = range_margin, jump_k

    def fit(self, train, z=None):
        v = train[self.sensors]
        self.lo, self.hi = v.min(), v.max()
        self.span = (self.hi - self.lo).replace(0, 1e-6)
        d = train.groupby("unit")[self.sensors].diff().abs()
        self.mad_step = d.median().clip(lower=1e-6)
        self.z_span = self.z_mad = None
        if z is not None:                         # jump check in regime-normalised units
            zt = z[self.sensors]; self.z_span = (zt.max() - zt.min()).replace(0, 1e-6)
            self.z_mad = zt.groupby(train["unit"]).diff().abs().median().clip(lower=1e-6)
        # stuck check only for sensors that are practically never constant over the window in healthy data
        # (quantised sensors such as integer bleed enthalpy are legitimately flat for several cycles)
        const = x_ = train.groupby("unit")[self.sensors].transform(lambda s: s.rolling(self.stuck_window).std()) < 1e-9
        self.stuck_rate = const.mean()
        self.noisy = (d.median() > 0) & (self.stuck_rate < 0.001)
        return self

    def flags(self, raw, z=None):
        """raw: RAW (uncleaned) frame sorted by unit,cycle. Returns frame of boolean flags + reason strings."""
        x = raw[self.sensors]
        f = pd.DataFrame(index=raw.index)
        f["dropout"] = x.isna().mean(axis=1) > self.max_nan
        g = x.groupby(raw["unit"])
        sd = g.transform(lambda s: s.rolling(self.stuck_window, min_periods=self.stuck_window).std())
        stuck_mask = (sd < 1e-9) & self.noisy
        f["stuck"] = stuck_mask.any(axis=1)
        m = self.range_margin * self.span
        rng_bad = (x < self.lo - m) | (x > self.hi + m)
        f["range"] = rng_bad.any(axis=1)
        if z is not None and self.z_mad is not None:
            step = z[self.sensors].groupby(raw["unit"]).diff().abs()
            jump_bad = step > np.maximum(self.jump_k * self.z_mad, 0.25 * self.z_span)
        else:
            step = g.diff().abs()
            jump_bad = step > np.maximum(self.jump_k * self.mad_step, 0.25 * self.span)
        f["jump"] = jump_bad.any(axis=1)
        reasons = [""] * len(raw)
        bad = np.where(f[["dropout", "stuck", "range", "jump"]].any(axis=1).values)[0]
        for i in bad:
            r = []
            if f["dropout"].iat[i]: r.append(f"Sensor dropout {x.iloc[i].isna().mean()*100:.0f}% > {self.max_nan*100:.0f}%")
            if f["stuck"].iat[i]: r.append("stuck sensor(s) " + ",".join(stuck_mask.columns[stuck_mask.iloc[i].values][:3]))
            if f["range"].iat[i]: r.append("out-of-range " + ",".join(rng_bad.columns[rng_bad.iloc[i].values][:3]))
            if f["jump"].iat[i]: r.append("jump " + ",".join(jump_bad.columns[jump_bad.iloc[i].values][:3]))
            reasons[i] = "; ".join(r)
        f["reason"] = reasons
        f["ok"] = ~(f["dropout"] | f["stuck"] | f["range"] | f["jump"])
        return f


def sensor_agreement(dev_row, k=3, sd=3.0):
    """dev_row: robust-SD deviations in the degradation direction. Returns (passed, count)."""
    c = int(np.sum(dev_row > sd))
    return c >= k, c
