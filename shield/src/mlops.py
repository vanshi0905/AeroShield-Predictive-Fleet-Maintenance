"""Layer 3 - MLOps: hashes, MLflow tracking, registry (champion/challenger), age-matched drift, residual monitor, gate."""
import hashlib, json, os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


def now(): return datetime.now(timezone.utc).isoformat()
def hash_obj(o): return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()[:12]
def hash_df(df): return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:12]


def log_mlflow(subset, params, metrics, tags, db="outputs/mlflow.db", experiment="SHIELD", jsonl_path="outputs/runs.jsonl"):
    """MLflow tracking with SQLite store and newline-delimited JSON run log (outputs/runs.jsonl). Never fails the pipeline."""
    try:
        os.makedirs(os.path.dirname(jsonl_path) or ".", exist_ok=True)
        run_record = {
            "timestamp": now(),
            "subset": subset,
            "experiment": experiment,
            "stage": tags.get("stage", "train"),
            "params": {k: str(v)[:250] for k, v in params.items()},
            "metrics": {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float, np.floating)) and np.isfinite(v)},
            "tags": {k: str(v) for k, v in tags.items()}
        }
        with open(jsonl_path, "a", encoding="utf-8") as jf:
            jf.write(json.dumps(run_record) + "\n")
    except Exception:
        pass

    try:
        import mlflow
        os.makedirs(os.path.dirname(db) or ".", exist_ok=True)
        mlflow.set_tracking_uri(f"sqlite:///{os.path.abspath(db)}")
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name=f"{subset}-{tags.get('stage', 'train')}") as r:
            mlflow.log_params({k: str(v)[:250] for k, v in params.items()})
            mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float, np.floating)) and np.isfinite(v)})
            mlflow.set_tags({k: str(v) for k, v in tags.items()})
            return r.info.run_id
    except Exception as e:                           # pragma: no cover
        print(f"[mlflow] logging skipped: {e}"); return None


# ------------------------------------------------------------------ drift
def psi(ref, new, bins=10):
    ref, new = np.asarray(ref, float), np.asarray(new, float)
    if len(ref) < 20 or len(new) < 20: return 0.0
    e = np.unique(np.percentile(ref, np.linspace(0, 100, bins + 1)))
    if len(e) < 3: return 0.0
    e[0] -= 1e-9; e[-1] += 1e-9
    r = np.histogram(np.clip(ref, e[0], e[-1]), e)[0] / len(ref) + 1e-4
    n = np.histogram(np.clip(new, e[0], e[-1]), e)[0] / len(new) + 1e-4
    return float(np.sum((n - r) * np.log(n / r)))


class DriftMonitor:
    """Age-matched input drift (problem D2): compare new vs reference WITHIN the same engine-age bin
    so an older fleet is not mistaken for drifted machines. PSI>limit on >= k features in a bin, or KS p<ks_p."""

    def __init__(self, age_bins, psi_limit=0.2, min_features=3, ks_p=0.01):
        self.bins, self.limit, self.k, self.ks_p = list(age_bins), psi_limit, min_features, ks_p

    def check(self, ref, new, features, age_col="cycle"):
        rep, drifted_bins, per_feature = {}, [], {}
        for lo, hi in zip(self.bins[:-1], self.bins[1:]):
            r = ref[(ref[age_col] > lo) & (ref[age_col] <= hi)]; n = new[(new[age_col] > lo) & (new[age_col] <= hi)]
            name = f"{lo}-{hi}"
            if len(r) < 50 or len(n) < 50:
                rep[name] = {"skipped": "too few rows", "n_ref": len(r), "n_new": len(n)}; continue
            ps = {f: psi(r[f], n[f]) for f in features}
            ksp = {f: float(ks_2samp(r[f], n[f]).pvalue) for f in features}
            hot = [f for f in features if ps[f] > self.limit]
            ks_hot = [f for f in features if ksp[f] < self.ks_p]
            rep[name] = {"n_ref": len(r), "n_new": len(n), "psi": ps, "ks_p": ksp, "psi_drifted": hot, "ks_drifted": ks_hot}
            for f in features: per_feature[f] = max(per_feature.get(f, 0.0), ps[f])
            if len(hot) >= self.k or len(ks_hot) >= max(self.k, len(features) // 2): drifted_bins.append(name)
        return {"drift": bool(drifted_bins), "drifted_age_bins": drifted_bins, "max_psi_per_feature": per_feature, "bins": rep}


class ResidualMonitor:
    """Rolling error on matured engines vs validation error. Trigger if RMSE >10% worse (most direct staleness signal)."""

    def __init__(self, val_rmse, rise=0.10): self.val, self.rise = val_rmse, rise

    def check(self, pred, true):
        cur = float(np.sqrt(np.mean((np.asarray(pred) - np.asarray(true)) ** 2)))
        return {"live_rmse": cur, "validation_rmse": self.val, "relative_change": cur / self.val - 1, "trigger": cur > self.val * (1 + self.rise)}


def data_quality_drift(flags):
    return {"dropout_rate": float(flags["dropout"].mean()), "stuck_rate": float(flags["stuck"].mean()),
            "range_rate": float(flags["range"].mean()), "jump_rate": float(flags["jump"].mean())}


# ------------------------------------------------------------------ registry + gate
class ModelRegistry:
    """JSON registry with champion/challenger per subset (MLflow Model Registry aliases are the planned upgrade).
    Starts EMPTY - the first real training run registers v1 with its measured metrics."""

    def __init__(self, path="outputs/registry.json"):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.data = json.load(open(path)) if os.path.exists(path) else {}

    def save(self): json.dump(self.data, open(self.path, "w"), indent=2, default=str)

    def champion(self, subset): return self.data.get(subset, {}).get("champion")

    def register_champion(self, subset, version, metrics, path="", note="initial training"):
        s = self.data.setdefault(subset, {"champion": None, "history": []})
        if s["champion"]: s["champion"]["status"] = "archived"; s["history"].append(s["champion"])
        s["champion"] = {"version": version, "status": "champion", "metrics": metrics, "path": path, "promoted_at": now(), "note": note}
        self.save()

    @staticmethod
    def gate(champ, chall, target=0.80):
        """RMSE <= champion AND NASA <= +5% AND coverage >= target - 5 points AND late share <= +5 points."""
        checks = {
            "rmse_not_worse": chall["rmse"] <= champ["rmse"],
            "nasa_within_5pct": chall["nasa"] <= champ["nasa"] * 1.05,
            "coverage_within_5pts": chall["coverage"] >= target - 0.05,
            "late_share_within_5pts": chall["late_share"] <= champ["late_share"] + 0.05,
        }
        return all(checks.values()), checks

    def decide(self, subset, version, chall_metrics, champ_metrics, target=0.80, path="", trigger="", extra_checks=None):
        ok, checks = self.gate(champ_metrics, chall_metrics, target)
        if extra_checks:
            checks = {**checks, **extra_checks}; ok = all(checks.values())
        s = self.data.setdefault(subset, {"champion": None, "history": []})
        entry = {"version": version, "evaluated_at": now(), "trigger": trigger, "challenger": chall_metrics,
                 "champion_version": (s["champion"] or {}).get("version"), "champion": champ_metrics,
                 "checks": checks, "promoted": ok,
                 "reason": "Passed all gate checks" if ok else "Rejected: " + ", ".join(k for k, v in checks.items() if not v)}
        s["history"].append(entry)
        if ok:
            if s["champion"]: s["champion"]["status"] = "archived"
            s["champion"] = {"version": version, "status": "champion", "metrics": chall_metrics, "path": path, "promoted_at": now(), "note": trigger}
        self.save()
        return ok, entry
