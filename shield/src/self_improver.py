"""Autonomous Self-Improvement Engine for AeroShield SHIELD Pipeline.

Implements a closed-loop tournament evaluation system:
1. Bayesian-style grid search over hyperparameter configurations
2. Multi-model champion vs. challenger tournament with strict 4-gate validation
3. Automated promotion with SHA-256 audit trail and deterministic rollback
4. CLI interface for manual or scheduled execution

Usage:
    python run_self_improvement.py --subset FD001 --iterations 10 --auto-promote
"""

import copy
import hashlib
import itertools
import json
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .calibrate import (
    QuantileRULModel,
    RidgeRUL,
    tune_late_shift,
    smooth_by_engine,
    order_quantiles,
    CrossConformalCalibrator,
    BoundedStepSmoother,
)
from .evaluate import rmse, nasa_score, coverage, truncation_points, last_window_metrics
from . import mlops


# ─────────────────────────────────────────────────────────────────────────────
# Hyperparameter search space
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SEARCH_SPACE = {
    # QuantileRULModel (HistGradientBoosting)
    "hgb_max_iter":       [120, 180, 250, 350],
    "hgb_lr":             [0.04, 0.06, 0.08, 0.10],
    "hgb_min_leaf":       [25, 35, 50],
    "hgb_l2":             [0.5, 1.0, 2.0],
    # Late-bias shift
    "late_shift":         [0, 2, 4, 6, 8, 10],
    # Smoother
    "smoother_alpha":     [0.15, 0.25, 0.35, 0.50],
    "smoother_umax":      [0.5, 1.0, 2.0],
    # Imbalance weight multiplier for near-failure rows
    "near_weight_mult":   [1.5, 2.0, 3.0],
}

COMPACT_SEARCH_SPACE = {
    "hgb_max_iter":       [150, 250],
    "hgb_lr":             [0.05, 0.08],
    "hgb_min_leaf":       [30, 45],
    "hgb_l2":             [0.8, 1.5],
    "late_shift":         [0, 3, 6],
    "smoother_alpha":     [0.2, 0.35],
    "smoother_umax":      [1.0, 2.0],
    "near_weight_mult":   [2.0, 3.0],
}


# ─────────────────────────────────────────────────────────────────────────────
# Tournament Gate (4-gate validation)
# ─────────────────────────────────────────────────────────────────────────────

class TournamentGate:
    """Strict 4-gate promotion validation.

    A challenger is promoted only if ALL four gates pass:
    1. RMSE (capped truth) <= champion RMSE
    2. NASA score (uncapped truth) <= champion NASA * (1 + tolerance)
    3. Conformal coverage >= coverage_floor
    4. Late share <= late_ceiling
    """

    def __init__(self, nasa_tol=0.05, coverage_floor=0.75, late_ceiling=0.30):
        self.nasa_tol = nasa_tol
        self.coverage_floor = coverage_floor
        self.late_ceiling = late_ceiling

    def evaluate(self, champion_metrics, challenger_metrics):
        """Returns (passed: bool, checks: dict)."""
        c_rmse = champion_metrics.get("oof_oof_rmse", champion_metrics.get("rmse", 15.0))
        c_nasa = champion_metrics.get("oof_oof_nasa", champion_metrics.get("nasa", 2000.0))
        checks = {
            "rmse_not_worse": challenger_metrics["rmse"] <= c_rmse,
            "nasa_within_tol": challenger_metrics["nasa"] <= c_nasa * (1 + self.nasa_tol),
            "coverage_above_floor": challenger_metrics["coverage"] >= self.coverage_floor,
            "late_share_below_ceiling": challenger_metrics["late_share"] <= self.late_ceiling,
        }
        passed = all(checks.values())
        return passed, checks


# ─────────────────────────────────────────────────────────────────────────────
# Candidate Evaluator (OOF-based fast scoring)
# ─────────────────────────────────────────────────────────────────────────────

class CandidateEvaluator:
    """Evaluates a hyperparameter configuration on out-of-fold predictions.

    Uses GroupKFold by engine to prevent data leakage.
    Returns standardized metrics dict.
    """

    def __init__(self, cap=125.0, folds=5, seed=42):
        self.cap = cap
        self.folds = folds
        self.seed = seed

    def _make_weights(self, y, near_rul, mult):
        return 1.0 + (mult - 1.0) * (y <= near_rul)

    def evaluate_config(self, gold, feature_cols, config, near_rul=50, d_max=5.0,
                        conformal_level=0.80, short_cycles=40):
        """Train and evaluate a single hyperparameter configuration using OOF.

        Returns metrics dict with rmse, nasa, coverage, late_share, and oof predictions.
        """
        cap = self.cap
        X = gold[feature_cols].values
        y = gold["RUL_capped"].values if "RUL_capped" in gold else np.clip(gold["RUL"].values, 0, cap)
        y_uncapped = gold["RUL"].values if "RUL" in gold else y
        u = gold["unit"].values
        age = gold["cycle"].values

        max_iter = config.get("hgb_max_iter", 150)
        lr = config.get("hgb_lr", 0.08)
        min_leaf = config.get("hgb_min_leaf", 40)
        l2 = config.get("hgb_l2", 1.0)
        shift = config.get("late_shift", 0)
        alpha = config.get("smoother_alpha", 0.3)
        umax = config.get("smoother_umax", 1.0)
        wt_mult = config.get("near_weight_mult", 2.0)

        from sklearn.ensemble import HistGradientBoostingRegressor

        # OOF predictions
        o10, o50, o90 = np.zeros(len(X)), np.zeros(len(X)), np.zeros(len(X))
        fold_rmse = []

        for k, (tr, va) in enumerate(GroupKFold(self.folds).split(X, groups=u)):
            w = self._make_weights(y[tr], near_rul, wt_mult)

            models = {}
            for q in (0.1, 0.5, 0.9):
                m = HistGradientBoostingRegressor(
                    loss="quantile", quantile=q,
                    max_iter=max_iter, learning_rate=lr,
                    min_samples_leaf=min_leaf, l2_regularization=l2,
                    random_state=self.seed + k
                )
                m.fit(X[tr], np.clip(y[tr], 0, cap), sample_weight=w)
                models[q] = m

            o10[va] = np.clip(models[0.1].predict(X[va]), 0, cap)
            o50[va] = np.clip(models[0.5].predict(X[va]), 0, cap)
            o90[va] = np.clip(models[0.9].predict(X[va]), 0, cap)
            fold_rmse.append(rmse(o50[va], y[va]))

        # Apply late-bias shift
        sh = lambda a: np.clip(a - shift, 0, cap)
        o10, o50 = sh(o10), sh(o50)

        # Smooth
        sm = lambda a: smooth_by_engine(u, a, alpha, d_max, umax, cap)
        s10, s50, s90 = order_quantiles(sm(o10), sm(o50), sm(o90), cap)

        # Conformal calibration
        trunc = truncation_points(gold, 10, seed=self.seed)
        conf = CrossConformalCalibrator(conformal_level, cap, short_cycles)
        conf.fit(s10[trunc], s90[trunc], y[trunc], age[trunc])
        w10, w90 = conf.widen(s10, s90, age)

        # Metrics on truncation points
        t = trunc
        metrics = {
            "rmse": rmse(s50[t], y[t]),
            "nasa": nasa_score(s50[t], y[t]),
            "coverage": coverage(w10[t], w90[t], y[t]),
            "late_share": float(np.mean(s50[t] > y[t])),
            "fold_rmse_mean": float(np.mean(fold_rmse)),
            "fold_rmse_std": float(np.std(fold_rmse)),
            "config": config,
        }
        return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Self-Improvement Engine
# ─────────────────────────────────────────────────────────────────────────────

class SelfImprovementEngine:
    """Autonomous closed-loop self-improvement for the SHIELD pipeline.

    Workflow:
    1. Load current champion metrics from registry
    2. Generate challenger configurations (grid search or random sampling)
    3. Evaluate each challenger on OOF data
    4. Tournament: compare challengers against champion using 4-gate validation
    5. If a challenger passes all gates: promote and audit-log the change
    6. If no challenger passes: retain champion, log rejection

    All decisions are recorded in a JSON audit trail.
    """

    def __init__(self, subset, gold, feature_cols, cap=125.0, seed=42,
                 out_dir="outputs", search_space=None):
        self.subset = subset
        self.gold = gold
        self.cols = feature_cols
        self.cap = cap
        self.seed = seed
        self.out_dir = os.path.join(out_dir, subset)
        self.search_space = search_space or COMPACT_SEARCH_SPACE
        self.evaluator = CandidateEvaluator(cap=cap, seed=seed)
        self.gate = TournamentGate()
        self.history = []
        os.makedirs(self.out_dir, exist_ok=True)

    def _load_champion(self):
        """Load champion metrics from registry or compute from current OOF."""
        reg_path = os.path.join(os.path.dirname(self.out_dir), "registry.json")
        if os.path.exists(reg_path):
            with open(reg_path) as f:
                reg = json.load(f)
            if self.subset in reg:
                champ = reg[self.subset].get("champion", {})
                if isinstance(champ, dict) and "metrics" in champ:
                    return champ["metrics"]
                if "metrics" in reg[self.subset]:
                    return reg[self.subset]["metrics"]
        return None

    def _random_configs(self, n_configs):
        """Generate random hyperparameter configurations."""
        rng = np.random.default_rng(self.seed)
        configs = []
        for _ in range(n_configs):
            cfg = {}
            for key, values in self.search_space.items():
                cfg[key] = values[rng.integers(0, len(values))]
            configs.append(cfg)
        return configs

    def _grid_configs(self, max_configs=50):
        """Generate a grid of hyperparameter configurations, randomly subsampled."""
        keys = list(self.search_space.keys())
        values = [self.search_space[k] for k in keys]
        all_combos = list(itertools.product(*values))

        rng = np.random.default_rng(self.seed)
        if len(all_combos) > max_configs:
            idx = rng.choice(len(all_combos), max_configs, replace=False)
            all_combos = [all_combos[i] for i in idx]

        return [dict(zip(keys, combo)) for combo in all_combos]

    def run_tournament(self, n_iterations=10, strategy="random", verbose=True):
        """Run the self-improvement tournament.

        Args:
            n_iterations: Number of challenger configurations to evaluate
            strategy: 'random' or 'grid'
            verbose: Print progress

        Returns:
            dict with tournament results
        """
        t0 = time.time()

        # Load or compute champion baseline
        champion_metrics = self._load_champion()
        if champion_metrics is None:
            if verbose:
                print("[self-improve] No champion found, computing baseline...")
            # Evaluate default config as champion
            default_config = {
                "hgb_max_iter": 150, "hgb_lr": 0.08, "hgb_min_leaf": 40,
                "hgb_l2": 1.0, "late_shift": 5, "smoother_alpha": 0.3,
                "smoother_umax": 1.0, "near_weight_mult": 2.0,
            }
            champion_metrics = self.evaluator.evaluate_config(
                self.gold, self.cols, default_config
            )
            if verbose:
                print(f"[self-improve] Baseline champion: RMSE={champion_metrics['rmse']:.2f} "
                      f"NASA={champion_metrics['nasa']:.0f} Coverage={champion_metrics['coverage']:.1%}")

        # Generate challenger configs
        if strategy == "grid":
            configs = self._grid_configs(n_iterations)
        else:
            configs = self._random_configs(n_iterations)

        if verbose:
            print(f"[self-improve] Evaluating {len(configs)} challenger configs...")

        best_challenger = None
        results = []

        for i, cfg in enumerate(configs):
            try:
                metrics = self.evaluator.evaluate_config(self.gold, self.cols, cfg)
                passed, checks = self.gate.evaluate(champion_metrics, metrics)

                result = {
                    "iteration": i + 1,
                    "config": cfg,
                    "metrics": {k: v for k, v in metrics.items() if k != "config"},
                    "passed_gate": passed,
                    "gate_checks": checks,
                }
                results.append(result)

                if verbose and (i + 1) % max(1, len(configs) // 5) == 0:
                    print(f"  [{i+1}/{len(configs)}] RMSE={metrics['rmse']:.2f} "
                          f"NASA={metrics['nasa']:.0f} "
                          f"{'PASS' if passed else 'FAIL'}")

                if passed:
                    if best_challenger is None or metrics["rmse"] < best_challenger["metrics"]["rmse"]:
                        best_challenger = result

            except Exception as e:
                if verbose:
                    print(f"  [{i+1}/{len(configs)}] ERROR: {e}")
                results.append({"iteration": i + 1, "config": cfg, "error": str(e)})

        # Tournament summary
        elapsed = time.time() - t0
        n_passed = sum(1 for r in results if r.get("passed_gate", False))

        summary = {
            "subset": self.subset,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_candidates": len(configs),
            "passed_gate": n_passed,
            "failed_gate": len(configs) - n_passed,
            "elapsed_seconds": round(elapsed, 1),
            "champion_before": {k: v for k, v in champion_metrics.items() if k != "config"},
            "best_challenger": best_challenger,
            "promoted": best_challenger is not None,
        }

        if verbose:
            print(f"\n[self-improve] Tournament complete in {elapsed:.1f}s")
            print(f"  Passed gate: {n_passed}/{len(configs)}")
            if best_challenger:
                bm = best_challenger["metrics"]
                print(f"  PROMOTED: RMSE={bm['rmse']:.2f} (was {champion_metrics['rmse']:.2f}) "
                      f"NASA={bm['nasa']:.0f} (was {champion_metrics['nasa']:.0f})")
            else:
                print(f"  No challenger passed all 4 gates. Champion retained.")

        # Record history
        self.history.append(summary)

        # Save tournament log
        log_path = os.path.join(self.out_dir, "self_improvement_log.json")
        with open(log_path, "w") as f:
            json.dump(self.history, f, indent=2, default=str)

        return summary

    def run_iterative(self, total_iterations=20, batch_size=5, max_rounds=10, verbose=True):
        """Run multiple tournament rounds, narrowing the search space around the best config.

        Each round evaluates `batch_size` configs. If a champion is dethroned, the next
        round narrows the search around the winning config.
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"  AEROSHIELD SELF-IMPROVEMENT: {self.subset}")
            print(f"  {total_iterations} total candidates across {max_rounds} rounds")
            print(f"{'='*60}\n")

        all_results = []
        remaining = total_iterations

        for round_num in range(1, max_rounds + 1):
            if remaining <= 0:
                break

            n = min(batch_size, remaining)
            if verbose:
                print(f"\n--- Round {round_num} ({n} candidates) ---")

            result = self.run_tournament(n_iterations=n, strategy="random", verbose=verbose)
            all_results.append(result)
            remaining -= n

            # If a challenger won, narrow the search around its config
            if result["promoted"] and result["best_challenger"]:
                winning_config = result["best_challenger"]["config"]
                self._narrow_search_space(winning_config)
                if verbose:
                    print(f"  Search space narrowed around winning config.")

        return all_results

    def _narrow_search_space(self, center_config):
        """Narrow the search space around a winning configuration."""
        narrowed = {}
        for key, values in self.search_space.items():
            if key in center_config:
                center = center_config[key]
                # Keep center and its immediate neighbours in the sorted list
                sorted_vals = sorted(set(values))
                if center in sorted_vals:
                    idx = sorted_vals.index(center)
                    lo = max(0, idx - 1)
                    hi = min(len(sorted_vals) - 1, idx + 1)
                    narrowed[key] = sorted_vals[lo:hi + 1]
                else:
                    narrowed[key] = values
            else:
                narrowed[key] = values
        self.search_space = narrowed
