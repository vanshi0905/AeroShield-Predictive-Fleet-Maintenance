"""Layer 2 - early-warning anomaly detector (Isolation Forest) with OUT-OF-FOLD threshold and lead-time metrics."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import GroupKFold


class AnomalyDetector:
    def __init__(self, cols=None, seed=42, ewma=0.3):
        self.cols, self.seed, self.alpha = cols, seed, ewma
        self.model = None; self.threshold = None

    def _fit(self, X):
        return IsolationForest(n_estimators=200, random_state=self.seed, n_jobs=-1).fit(X)

    @staticmethod
    def raw_score(model, X):
        return -model.decision_function(X)           # higher = more abnormal

    def smooth(self, units, s):
        out = np.empty_like(s)
        for u in np.unique(units):
            idx = np.where(units == u)[0]
            out[idx] = pd.Series(s[idx]).ewm(alpha=self.alpha, adjust=False).mean().values
        return out

    @staticmethod
    def confirmed(units, above, persist):
        """True when `above` held for `persist` consecutive cycles within an engine."""
        out = np.zeros(len(above), bool)
        for u in np.unique(units):
            idx = np.where(units == u)[0]
            run = 0
            for k in idx:
                run = run + 1 if above[k] else 0
                out[k] = run >= persist
        return out

    @staticmethod
    def engine_metrics(units, rul, conf, healthy_rul):
        """Engine-level false-alarm rate (alert while true RUL >= healthy_rul) and warning lead time (cycles of RUL at 1st alert)."""
        fa, lead, n = 0, [], 0
        for u in np.unique(units):
            idx = np.where(units == u)[0]
            c = conf[idx]; r = rul[idx]; n += 1
            if (c & (r >= healthy_rul)).any():
                fa += 1
            det = np.where(c & (r < healthy_rul))[0]           # first alert inside the degradation window
            if len(det):
                lead.append(float(r[det[0]]))
        healthy_rows = rul >= healthy_rul
        return {"engine_false_alarm_rate": fa / max(n, 1),
                "median_lead_time": float(np.median(lead)) if lead else 0.0,
                "alerted_engines": len(lead), "engines": n, "detection_rate": len(lead) / max(n, 1),
                "false_alerts_per_100_healthy_cycles": float(100 * (conf & healthy_rows).sum() / max(healthy_rows.sum(), 1))}

    def fit_with_oof(self, gold, rul, percentiles, persist, max_fa, healthy_rul, folds=5):
        if self.cols is None:
            self.cols = [c for c in gold.columns if c.endswith("_dbase")]
        X = gold[self.cols].values; units = gold["unit"].values
        healthy = rul >= healthy_rul
        oof = np.zeros(len(X))
        for tr, va in GroupKFold(folds).split(X, groups=units):
            m = self._fit(X[tr][healthy[tr]])
            oof[va] = self.raw_score(m, X[va])
        sm = self.smooth(units, oof)
        table = []
        for p in percentiles:
            thr = float(np.percentile(sm[healthy], p))
            conf = self.confirmed(units, sm > thr, persist)
            met = self.engine_metrics(units, rul, conf, healthy_rul)
            table.append({"percentile": p, "threshold": thr, **met})
        ok = [t for t in table if t["engine_false_alarm_rate"] <= max_fa]
        best = max(ok, key=lambda t: t["detection_rate"] * t["median_lead_time"]) if ok else min(table, key=lambda t: t["engine_false_alarm_rate"])
        self.threshold = best["threshold"]
        self.model = self._fit(X[healthy])
        return best, table

    def score_smoothed(self, gold):
        cols = self.cols if self.cols is not None else [c for c in gold.columns if c.endswith("_dbase")]
        return self.smooth(gold["unit"].values, self.raw_score(self.model, gold[cols].values))
