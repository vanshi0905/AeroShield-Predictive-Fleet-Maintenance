"""Tests for SOTA components:
1. ContinuousRegimeNormalizer (shield/src/regime_continuous.py)
2. AsymmetricLossGBM, StackingRULEnsemble, MultiScaleFeatureAugmentor (shield/src/sota_models.py)
3. TournamentGate, CandidateEvaluator, SelfImprovementEngine (shield/src/self_improver.py)
"""

import numpy as np
import pandas as pd
import pytest

from shield.src.regime_continuous import ContinuousRegimeNormalizer
from shield.src.sota_models import (
    AsymmetricLossGBM,
    StackingRULEnsemble,
    MultiScaleFeatureAugmentor,
)
from shield.src.self_improver import (
    TournamentGate,
    CandidateEvaluator,
    SelfImprovementEngine,
)
from shield.src.data import make_synthetic, OPS, SENS
from shield.src.features import Preprocessor


# ═══════════════════════════════════════════════════════════════════════════
# 1. ContinuousRegimeNormalizer Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_continuous_regime_normalizer_fit_transform():
    """Verify fit and transform_deviations output shapes and properties."""
    rng = np.random.default_rng(42)
    n = 200
    ops = rng.uniform(0, 100, size=(n, 3))
    # Sensors that are non-linear function of ops + noise
    sensors = 2.0 * ops[:, [0]] + 0.05 * (ops[:, [1]] ** 2) + rng.normal(0, 1, size=(n, 4))
    
    norm = ContinuousRegimeNormalizer(degree=2, alpha=1.0)
    devs = norm.fit_transform(ops, sensors)
    
    assert devs.shape == sensors.shape
    # Residuals/deviations must have significantly lower variance than raw sensors
    assert np.var(devs) < np.var(sensors)
    # Mean deviation should be close to 0
    assert np.allclose(np.mean(devs, axis=0), 0.0, atol=1e-2)


def test_continuous_regime_normalizer_removes_regime_effect():
    """Verify that regime variation is captured and subtracted."""
    n_per_regime = 100
    regimes = [
        [0.0, 0.0, 100.0],
        [10.0, 0.2, 80.0],
        [25.0, 0.6, 60.0],
        [40.0, 0.84, 40.0],
    ]
    ops_list, sens_list = [], []
    rng = np.random.default_rng(42)
    for r in regimes:
        o = np.tile(r, (n_per_regime, 1)) + rng.normal(0, 0.1, (n_per_regime, 3))
        # Sensor heavily dependent on altitude (op[0])
        s = 500.0 - 5.0 * o[:, [0]] + rng.normal(0, 0.5, (n_per_regime, 2))
        ops_list.append(o)
        sens_list.append(s)
    
    ops = np.vstack(ops_list)
    sensors = np.vstack(sens_list)
    
    raw_var = np.var(sensors, axis=0)
    norm = ContinuousRegimeNormalizer(degree=2, alpha=0.1)
    devs = norm.fit_transform(ops, sensors)
    dev_var = np.var(devs, axis=0)
    
    # Cross-regime variance should drop by > 90%
    assert (dev_var / raw_var < 0.10).all()


# ═══════════════════════════════════════════════════════════════════════════
# 2. AsymmetricLossGBM Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_asymmetric_loss_gbm_predictions_bounded():
    """Verify that predictions are strictly bounded within [0, cap]."""
    rng = np.random.default_rng(42)
    X = rng.normal(0, 1, size=(100, 10))
    y = rng.uniform(0, 150, size=100)
    
    model = AsymmetricLossGBM(cap=125.0, beta=2.5, n_estimators=50, random_state=42)
    model.fit(X, y)
    p10, p50, p90 = model.predict_raw(X)
    
    for p in (p10, p50, p90):
        assert (p >= 0.0).all()
        assert (p <= 125.0).all()
        assert np.isfinite(p).all()


def test_asymmetric_loss_gbm_penalizes_late():
    """Verify that higher beta pushes predictions downward (reducing late share)."""
    rng = np.random.default_rng(42)
    X = np.linspace(0, 10, 150).reshape(-1, 1)
    y = np.clip(120 - 8.0 * X[:, 0] + rng.normal(0, 5, 150), 0, 125)
    
    # Model with symmetric penalty (beta = 1.0)
    m_sym = AsymmetricLossGBM(cap=125.0, beta=1.0, n_estimators=60, random_state=42)
    m_sym.fit(X, y)
    _, p50_sym, _ = m_sym.predict_raw(X)
    
    # Model with heavy late penalty (beta = 3.5)
    m_asym = AsymmetricLossGBM(cap=125.0, beta=3.5, n_estimators=60, random_state=42)
    m_asym.fit(X, y)
    _, p50_asym, _ = m_asym.predict_raw(X)
    
    # Asymmetric model should have lower or equal mean prediction than symmetric model
    assert np.mean(p50_asym) <= np.mean(p50_sym) + 1e-4


# ═══════════════════════════════════════════════════════════════════════════
# 3. StackingRULEnsemble Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_stacking_ensemble_weights_sum_to_one():
    """Verify that blending weights are non-negative and sum to 1."""
    rng = np.random.default_rng(42)
    y_true = rng.uniform(10, 120, size=100)
    
    pred1 = y_true + rng.normal(0, 8, size=100)
    pred2 = y_true + rng.normal(0, 12, size=100)
    pred3 = y_true + rng.normal(0, 15, size=100)
    
    ensemble = StackingRULEnsemble(cap=125.0, alpha=1.0)
    ensemble.fit([pred1, pred2, pred3], y_true)
    
    assert ensemble.weights_ is not None
    assert (ensemble.weights_ >= 0.0).all()
    assert np.isclose(np.sum(ensemble.weights_), 1.0)
    
    blended = ensemble.predict([pred1, pred2, pred3])
    assert (blended >= 0.0).all() and (blended <= 125.0).all()


def test_stacking_ensemble_improves_over_worst():
    """Verify that ensemble error is strictly lower than the worst model."""
    rng = np.random.default_rng(42)
    y_true = np.linspace(10, 100, 200)
    p_good = y_true + rng.normal(0, 3, size=200)
    p_bad = y_true + rng.normal(0, 20, size=200)
    
    ens = StackingRULEnsemble(cap=125.0)
    ens.fit([p_good, p_bad], y_true)
    blended = ens.predict([p_good, p_bad])
    
    rmse_ens = np.sqrt(np.mean((blended - y_true) ** 2))
    rmse_bad = np.sqrt(np.mean((p_bad - y_true) ** 2))
    assert rmse_ens < rmse_bad


# ═══════════════════════════════════════════════════════════════════════════
# 4. MultiScaleFeatureAugmentor Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_multi_scale_augmentor_causal(cfg, fleet):
    """Verify that MultiScaleFeatureAugmentor is strictly causal (no future lookahead)."""
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    gold = p.transform(fleet)
    
    aug = MultiScaleFeatureAugmentor(thermal_sensor="s3", pressure_sensor="s7")
    aug_full = aug.augment(gold, p.sensors)
    
    # Check for unit 1 at cycle 30
    unit1 = gold[gold.unit == 1].reset_index(drop=True)
    t = 30
    prefix = unit1.iloc[:t].copy()
    aug_prefix = aug.augment(prefix, p.sensors)
    
    # Features at cycle 30 in prefix should equal cycle 30 in full
    cols_to_check = [c for c in aug_full.columns if c in ("thermal_stress_cum", "pressure_stress_cum")]
    for col in cols_to_check:
        val_prefix = aug_prefix.iloc[-1][col]
        val_full = aug_full[(aug_full.unit == 1) & (aug_full.cycle == t)][col].values[0]
        assert np.isclose(val_prefix, val_full, atol=1e-6)


def test_multi_scale_augmentor_adds_thermal_stress(cfg, fleet):
    """Verify that thermal and pressure stress columns exist and are non-decreasing."""
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    gold = p.transform(fleet)
    
    aug = MultiScaleFeatureAugmentor(thermal_sensor="s3", pressure_sensor="s7")
    aug_df = aug.augment(gold, p.sensors)
    
    assert "thermal_stress_cum" in aug_df.columns
    assert "pressure_stress_cum" in aug_df.columns
    
    # Cumulative stress must be non-decreasing within each engine
    for u in (1, 2, 3):
        eng = aug_df[aug_df.unit == u]
        diffs = np.diff(eng["thermal_stress_cum"].values)
        assert (diffs >= -1e-9).all()


# ═══════════════════════════════════════════════════════════════════════════
# 5. TournamentGate & SelfImprovementEngine Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_tournament_gate_criteria():
    """Verify 4-gate validation pass/fail logic using unified registry gate rules."""
    gate = TournamentGate(nasa_tol=0.05, coverage_floor=0.75, late_margin=0.05)
    champ = {"rmse": 12.0, "nasa": 300.0, "coverage": 0.82, "late_share": 0.25}
    
    # Case 1: All better -> PASS
    chall_pass = {"rmse": 11.5, "nasa": 280.0, "coverage": 0.85, "late_share": 0.22}
    passed, checks = gate.evaluate(champ, chall_pass)
    assert passed is True
    assert all(checks.values())
    
    # Case 2: Worse RMSE -> FAIL
    chall_bad_rmse = {"rmse": 12.8, "nasa": 280.0, "coverage": 0.85, "late_share": 0.22}
    passed, checks = gate.evaluate(champ, chall_bad_rmse)
    assert passed is False
    assert checks["rmse_not_worse"] is False
    
    # Case 3: Coverage below floor -> FAIL
    chall_low_cov = {"rmse": 11.2, "nasa": 280.0, "coverage": 0.70, "late_share": 0.22}
    passed, checks = gate.evaluate(champ, chall_low_cov)
    assert passed is False
    assert checks["coverage_above_floor"] is False

    # Case 4: Late share delta > +5 pts -> FAIL
    chall_high_late = {"rmse": 11.2, "nasa": 280.0, "coverage": 0.82, "late_share": 0.35}
    passed, checks = gate.evaluate(champ, chall_high_late)
    assert passed is False
    assert checks["late_share_within_margin"] is False


def test_self_improvement_tournament_execution(cfg, fleet, tmp_path):
    """Verify SelfImprovementEngine runs a mini-tournament cleanly."""
    fleet_slice = fleet[fleet.unit <= 4].copy().reset_index(drop=True)
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet_slice)
    gold = p.transform(fleet_slice)
    feature_cols = p.feature_cols[:4]  # test with 4 features for fast unit testing
    
    # Fast micro search space for rapid unit testing
    mini_space = {
        "hgb_max_iter": [5],
        "hgb_lr": [0.08],
        "hgb_min_leaf": [5],
        "hgb_l2": [1.0],
        "late_shift": [2],
        "smoother_alpha": [0.3],
        "smoother_umax": [1.0],
        "near_weight_mult": [2.0],
    }
    
    engine = SelfImprovementEngine(
        subset="FD001",
        gold=gold,
        feature_cols=feature_cols,
        cap=125.0,
        seed=42,
        out_dir=str(tmp_path),
        search_space=mini_space,
        folds=2,
    )
    
    summary = engine.run_tournament(n_iterations=2, strategy="random", verbose=False, auto_promote=True)
    assert "total_candidates" in summary
    assert summary["total_candidates"] == 2
    assert "champion_before" in summary
    assert "elapsed_seconds" in summary
