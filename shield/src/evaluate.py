"""Metrics: RMSE/MAE, NASA score, coverage by band, near-failure PR, bootstrap CIs, truncation sampling."""
import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_fscore_support


def nasa_score(pred, true):
    d = np.asarray(pred, float) - np.asarray(true, float)
    return float(np.sum(np.where(d < 0, np.exp(-d / 13.0) - 1, np.exp(d / 10.0) - 1)))


def rmse(p, t): return float(np.sqrt(np.mean((np.asarray(p) - np.asarray(t)) ** 2)))
def mae(p, t): return float(np.mean(np.abs(np.asarray(p) - np.asarray(t))))


def coverage(lo, hi, y, mask=None):
    c = (lo <= y) & (y <= hi)
    if mask is not None:
        c = c[mask]
    return float(c.mean()) if len(c) else float("nan")


def bootstrap_ci(fn, n, reps=1000, seed=0):
    rng = np.random.default_rng(seed)
    vals = [fn(rng.integers(0, n, n)) for _ in range(reps)]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def truncation_points(gold, repeats, seed=0, min_cycle=20):
    """Row positions of random truncation points per engine (mimics how test engines are cut)."""
    rng = np.random.default_rng(seed)
    pos = []
    for u, idx in gold.groupby("unit").indices.items():
        T = len(idx)
        lo = min(min_cycle, T)
        for _ in range(repeats):
            pos.append(idx[rng.integers(lo - 1, T)])
    return np.array(pos)


def last_window_metrics(unit, cycle, p10, p50, p90, true_capped, true_uncapped, cap, near=30, ci=True):
    """Final-window metrics, one row per engine."""
    n = len(p50)
    m = {
        "rmse_capped_truth": rmse(p50, true_capped), "mae_capped_truth": mae(p50, true_capped),
        "rmse_uncapped_truth": rmse(p50, true_uncapped),
        "nasa_capped_truth": nasa_score(p50, true_capped), "nasa_uncapped_truth": nasa_score(p50, true_uncapped),
        "late_share": float(np.mean(p50 > true_capped)),
        "coverage": coverage(p10, p90, true_capped),
        "coverage_rul_le_50": coverage(p10, p90, true_capped, true_capped <= 50),
        "coverage_rul_gt_50": coverage(p10, p90, true_capped, true_capped > 50),
        "n_engines": int(n),
    }
    y = true_uncapped <= near; pred = p50 <= near
    if y.any():
        pr, rc, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
        m.update(near_precision=float(pr), near_recall=float(rc), near_f1=float(f1),
                 near_pr_auc=float(average_precision_score(y, -p50)))
    if ci:
        m["ci95"] = {
            "rmse_capped_truth": bootstrap_ci(lambda i: rmse(p50[i], true_capped[i]), n),
            "nasa_uncapped_truth": bootstrap_ci(lambda i: nasa_score(p50[i], true_uncapped[i]), n),
            "late_share": bootstrap_ci(lambda i: np.mean(p50[i] > true_capped[i]), n),
        }
    return m


def all_window_metrics(p50, true_capped, true_uncapped):
    return {"rmse": rmse(p50, true_capped), "mae": mae(p50, true_capped),
            "nasa_uncapped_truth": nasa_score(p50, true_uncapped), "late_share": float(np.mean(p50 > true_capped)),
            "n_windows": int(len(p50))}
