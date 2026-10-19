"""SOTA model components: asymmetric-loss GBM, stacking ensemble, multi-scale feature augmentor.

These components are designed to push RUL prediction accuracy toward published SOTA on
NASA C-MAPSS, particularly on multi-regime subsets (FD002, FD004).
"""

import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

# ---------------------------------------------------------------------------
# LightGBM import with graceful fallback
# ---------------------------------------------------------------------------
try:
    import lightgbm as lgb
    _HAS_LGB = True
except ImportError:
    _HAS_LGB = False

if not _HAS_LGB:
    from sklearn.ensemble import HistGradientBoostingRegressor


# ═══════════════════════════════════════════════════════════════════════════
#  1.  Asymmetric Loss Gradient Boosted Machine
# ═══════════════════════════════════════════════════════════════════════════

def _asym_obj(beta):
    """Return (grad, hess) callable for LightGBM with asymmetric squared error.

    Late predictions (pred > truth) are penalised ``beta`` times more.
    """
    def _obj(y_pred, dataset):
        y_true = dataset.get_label()
        residual = y_pred - y_true
        # Late = positive residual → heavier penalty
        weight = np.where(residual > 0, beta, 1.0)
        grad = weight * residual
        hess = weight
        return grad, hess
    return _obj


class AsymmetricLossGBM:
    """Quantile RUL predictor with asymmetric squared-error median model.

    * P50 is trained with a custom objective that penalises late predictions
      (pred > truth) by a factor of ``beta``.
    * P10 / P90 use LightGBM's built-in quantile objective.
    * Falls back to ``HistGradientBoostingRegressor`` when LightGBM is absent.

    Parameters
    ----------
    cap : float
        Maximum RUL label (predictions are clipped to ``[0, cap]``).
    beta : float
        Asymmetric penalty multiplier for late predictions.
    n_estimators, learning_rate, num_leaves, min_child_samples : int / float
        LightGBM hyper-parameters.
    random_state : int
        Seed for reproducibility.
    """

    def __init__(self, cap=125.0, beta=2.5, n_estimators=300,
                 learning_rate=0.05, num_leaves=31, min_child_samples=30,
                 random_state=42):
        self.cap = cap
        self.beta = beta
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.random_state = random_state
        self._models = {}

    # ------------------------------------------------------------------ fit
    def fit(self, X, y, sample_weight=None):
        """Fit three internal models: P10, P50 (asymmetric), P90.

        Parameters
        ----------
        X : array-like, shape (n, d)
        y : array-like, shape (n,)
        sample_weight : array-like or None

        Returns
        -------
        self
        """
        y = np.clip(np.asarray(y, dtype=np.float64), 0, self.cap)
        X = np.asarray(X, dtype=np.float64)

        if _HAS_LGB:
            self._fit_lgb(X, y, sample_weight)
        else:
            self._fit_sklearn(X, y, sample_weight)
        return self

    # -- LightGBM path --
    def _fit_lgb(self, X, y, sw):
        common = dict(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            min_child_samples=self.min_child_samples,
            random_state=self.random_state,
            verbose=-1,
        )
        # P10 / P90 – built-in quantile objective
        for q in (0.1, 0.9):
            m = lgb.LGBMRegressor(objective="quantile", alpha=q, **common)
            m.fit(X, y, sample_weight=sw)
            self._models[q] = m

        # P50 – custom asymmetric squared error
        m50 = lgb.LGBMRegressor(objective=_asym_obj(self.beta), **common)
        # LightGBM needs a dummy metric when using a custom objective
        m50.fit(X, y, sample_weight=sw,
                eval_metric="rmse")
        self._models[0.5] = m50

    # -- sklearn fallback --
    def _fit_sklearn(self, X, y, sw):
        from sklearn.ensemble import HistGradientBoostingRegressor
        for q in (0.1, 0.5, 0.9):
            m = HistGradientBoostingRegressor(
                loss="quantile", quantile=q,
                max_iter=self.n_estimators,
                learning_rate=self.learning_rate,
                min_samples_leaf=self.min_child_samples,
                random_state=self.random_state,
            )
            m.fit(X, y, sample_weight=sw)
            self._models[q] = m

    # --------------------------------------------------------------- predict
    def predict_raw(self, X):
        """Return ``(p10, p50, p90)`` arrays, each clipped to ``[0, cap]``."""
        X = np.asarray(X, dtype=np.float64)
        return tuple(
            np.clip(self._models[q].predict(X), 0, self.cap)
            for q in (0.1, 0.5, 0.9)
        )


# ═══════════════════════════════════════════════════════════════════════════
#  2.  Stacking RUL Ensemble
# ═══════════════════════════════════════════════════════════════════════════

class StackingRULEnsemble:
    """Blend multiple base-model predictions with a constrained Ridge meta-learner.

    Parameters
    ----------
    cap : float
        Predictions are clipped to ``[0, cap]``.
    alpha : float
        Ridge regularisation strength.
    """

    def __init__(self, cap=125.0, alpha=1.0):
        self.cap = cap
        self.alpha = alpha
        self._meta = None
        self.weights_ = None

    # ------------------------------------------------------------------ fit
    def fit(self, base_preds_list, y):
        """Fit meta-learner on base predictions.

        Parameters
        ----------
        base_preds_list : list of array-like
            Each element is shape ``(n,)`` – one base model's predictions.
        y : array-like, shape ``(n,)``
            True labels.

        Returns
        -------
        self
        """
        Z = np.column_stack([np.asarray(p) for p in base_preds_list])
        y = np.asarray(y, dtype=np.float64)

        # Use non-negative Ridge if sklearn supports ``positive=True`` (>=1.0)
        try:
            self._meta = Ridge(alpha=self.alpha, fit_intercept=False, positive=True)
            self._meta.fit(Z, y)
        except TypeError:
            # Older sklearn – fall back to unconstrained Ridge then clip weights
            self._meta = Ridge(alpha=self.alpha, fit_intercept=False)
            self._meta.fit(Z, y)
            self._meta.coef_ = np.clip(self._meta.coef_, 0, None)

        # Normalise weights so they sum to 1
        w = self._meta.coef_.copy()
        w_sum = w.sum()
        if w_sum > 0:
            w = w / w_sum
        else:
            w = np.ones(len(w)) / len(w)
        self._meta.coef_ = w
        self.weights_ = w.copy()
        return self

    # --------------------------------------------------------------- predict
    def predict(self, base_preds_list):
        """Return blended prediction clipped to ``[0, cap]``."""
        Z = np.column_stack([np.asarray(p) for p in base_preds_list])
        return np.clip(self._meta.predict(Z), 0, self.cap)


# ═══════════════════════════════════════════════════════════════════════════
#  3.  Multi-Scale Feature Augmentor
# ═══════════════════════════════════════════════════════════════════════════

class MultiScaleFeatureAugmentor:
    """Add cumulative stress features and multi-scale rolling statistics.

    All computed features are *strictly causal* – they depend only on the
    current and past cycles for each engine (no future leakage).

    Parameters
    ----------
    thermal_sensor : str
        Sensor column used for cumulative thermal stress (default ``'s3'``).
        If deviations are available, use ``'s3_deviation'``.
    pressure_sensor : str
        Sensor column used for cumulative pressure stress (default ``'s7'``).
    corr_window : int
        Rolling window size for inter-sensor correlation features.
    """

    def __init__(self, thermal_sensor="s3", pressure_sensor="s7",
                 corr_window=20):
        self.thermal_sensor = thermal_sensor
        self.pressure_sensor = pressure_sensor
        self.corr_window = corr_window

    def augment(self, gold_df, sensors, ops_cols=None):
        """Return *gold_df* with additional columns appended.

        Parameters
        ----------
        gold_df : pd.DataFrame
            Must contain ``'unit'``, ``'cycle'``, and the sensor columns.
        sensors : list[str]
            Sensor column names present in ``gold_df`` (e.g. deviation columns).
        ops_cols : list[str] or None
            Operating-condition columns (unused internally but accepted for
            interface consistency).

        Returns
        -------
        pd.DataFrame
            Copy of ``gold_df`` with new feature columns.
        """
        if ops_cols is None:
            ops_cols = ["op1", "op2", "op3"]

        df = gold_df.copy()
        df = df.sort_values(["unit", "cycle"]).reset_index(drop=True)

        # --- Determine actual column names for thermal / pressure ----
        th_col = self._resolve_col(df, self.thermal_sensor, sensors)
        pr_col = self._resolve_col(df, self.pressure_sensor, sensors)

        # ---- Cumulative thermal stress per engine -------------------
        if th_col is not None:
            df["thermal_stress_cum"] = df.groupby("unit")[th_col].transform(
                lambda s: np.cumsum(np.maximum(s.values, 0.0) ** 2)
            )

        # ---- Cumulative pressure stress per engine ------------------
        if pr_col is not None:
            df["pressure_stress_cum"] = df.groupby("unit")[pr_col].transform(
                lambda s: np.cumsum(np.maximum(s.values, 0.0) ** 2)
            )

        # ---- Rolling correlation interaction features ---------------
        corr_pairs = self._pick_corr_pairs(df, sensors)
        for col_a, col_b, name in corr_pairs:
            corrs = []
            for _, g in df.groupby("unit"):
                c = g[col_a].rolling(self.corr_window, min_periods=2).corr(g[col_b]).fillna(0.0)
                corrs.append(c)
            df[name] = pd.concat(corrs).sort_index().values if corrs else 0.0

        return df

    # -------------------------------------------------------- helpers
    @staticmethod
    def _resolve_col(df, base_name, sensors):
        """Try ``<base>_deviation``, ``<base>_norm``, then ``<base>``."""
        for suffix in ("_deviation", "_norm", ""):
            cand = base_name + suffix
            if cand in df.columns:
                return cand
        # Check if any sensor column starts with the base name
        for s in sensors:
            if s.startswith(base_name):
                return s
        return None

    def _pick_corr_pairs(self, df, sensors):
        """Select correlation sensor pairs that exist in the DataFrame."""
        candidates = [
            ("s3", "s7", "corr_s3_s7"),
            ("s8", "s9", "corr_s8_s9"),
        ]
        out = []
        for a, b, name in candidates:
            ca = self._resolve_col(df, a, sensors)
            cb = self._resolve_col(df, b, sensors)
            if ca is not None and cb is not None:
                out.append((ca, cb, name))
        return out
