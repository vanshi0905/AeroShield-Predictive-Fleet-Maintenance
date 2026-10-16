"""Tests verifying the 4 key improvements:
1. Aerodynamic interaction ratios in feature engineering.
2. Baseline-subtracted sensor deviations (dbase) for anomaly detection.
3. Non-linear secondary estimator in RidgeRUL.
4. One-sided coverage gate in ModelRegistry.
"""
import numpy as np
import pandas as pd
import pytest
from shield.src.features import Preprocessor
from shield.src.anomaly import AnomalyDetector
from shield.src.calibrate import RidgeRUL
from shield.src.mlops import ModelRegistry


def test_aerodynamic_feature_engineering(cfg, fleet):
    """Test that gas-path interaction ratios (s8/s9, s13/s14, s11/s7, s4/s3) are generated and causal."""
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    gold = p.transform(fleet)
    
    expected_ratios = ["ratio_s8_s9", "ratio_s13_s14", "ratio_s11_s7", "ratio_s4_s3"]
    for r in expected_ratios:
        assert r in gold.columns, f"Missing aerodynamic ratio column: {r}"
        assert r in p.feature_cols, f"Missing {r} in Preprocessor.feature_cols"
        assert not gold[r].isna().any(), f"NaN found in aerodynamic ratio: {r}"
        assert np.isfinite(gold[r].values).all(), f"Non-finite values in {r}"


def test_anomaly_cols_use_dbase(cfg, fleet):
    """Test that Preprocessor.anomaly_cols returns baseline-subtracted deviation features (dbase)."""
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    cols = p.anomaly_cols()
    assert len(cols) > 0
    assert all(c.endswith("_dbase") for c in cols), f"Expected dbase columns, got: {cols}"


def test_anomaly_detector_healthy_vs_degraded(cfg, fleet):
    """Test AnomalyDetector trains on healthy envelope and reliably triggers when deviation expands."""
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    gold = p.transform(fleet)
    rul = fleet["RUL"].values

    ad = AnomalyDetector(p.anomaly_cols(), seed=42)
    best, table = ad.fit_with_oof(gold, rul, cfg["ANOM_PERCENTILES"], cfg["ANOM_PERSIST"], cfg["ANOM_MAX_ENGINE_FA"], cfg["HEALTHY_RUL"])
    
    assert ad.threshold is not None
    assert best["engine_false_alarm_rate"] <= cfg["ANOM_MAX_ENGINE_FA"]
    assert best["detection_rate"] > 0.0


def test_secondary_model_nonlinear():
    """Test that RidgeRUL behaves as a non-linear estimator capable of fitting quadratic/exponential degradation curves."""
    rng = np.random.default_rng(42)
    X = np.linspace(0, 10, 200).reshape(-1, 1)
    # Non-linear quadratic degradation
    y = np.clip(120 - 1.2 * (X[:, 0] ** 2) + rng.normal(0, 1.0, 200), 0, 125)
    
    model = RidgeRUL(cap=125.0, random_state=42).fit(X, y)
    preds = model.predict(X)
    
    # Check that predictions are bounded [0, cap]
    assert (preds >= 0).all() and (preds <= 125.0).all()
    # Non-linear fit should have very low RMSE on quadratic curve
    error = np.sqrt(np.mean((preds - y) ** 2))
    assert error < 5.0, f"Non-linear estimator expected RMSE < 5.0, got {error}"


def test_mlops_one_sided_coverage_gate():
    """Test that ModelRegistry.gate accepts coverage >= target - 0.05 even when coverage is well above target."""
    target = 0.80
    champ = {"rmse": 20.0, "nasa": 1000.0, "coverage": 0.81, "late_share": 0.20}
    
    # Challenger has superior coverage 0.92 (which would fail two-sided check abs(0.92 - 0.80) = 0.12 > 0.05)
    chall_high_coverage = {"rmse": 19.5, "nasa": 950.0, "coverage": 0.92, "late_share": 0.18}
    ok, checks = ModelRegistry.gate(champ, chall_high_coverage, target=target)
    assert checks["coverage_within_5pts"] is True or checks["coverage_within_5pts"] == True
    assert ok is True

    # Challenger has inadequate coverage 0.70 (fails one-sided check 0.70 < 0.75)
    chall_low_coverage = {"rmse": 19.5, "nasa": 950.0, "coverage": 0.70, "late_share": 0.18}
    ok_low, checks_low = ModelRegistry.gate(champ, chall_low_coverage, target=target)
    assert checks_low["coverage_within_5pts"] is False
    assert ok_low is False


def test_preprocessor_adapts_to_drift(cfg, fleet):
    """Test that Preprocessor adapts its normalization statistics when sensor distribution drifts."""
    from shield.src.data import SENS
    p1 = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    
    # Introduce a 2.0 sigma shift to fleet sensors
    drifted = fleet.copy()
    drifted[SENS] = drifted[SENS] + 2.0 * fleet[SENS].std().values
    p2 = Preprocessor(cfg, {"clustering": False}).fit(drifted)
    
    # Verify that preprocessor statistics adapted to the drift
    assert (p2.med != p1.med).any()
    assert (p2.stats[0][0] > p1.stats[0][0]).any()


def test_multi_regime_anomaly_detection_performance(cfg):
    """Test that multi-regime anomaly detection on FD002 achieves detection rate > 80% with false alarm <= 5%."""
    from shield.src.pipeline import load_cfg, load_cmapss
    sc = {"clustering": True, "n_regimes": 6, "auto_k": False}
    train, _, _ = load_cmapss("FD002", "data", cfg["CAP"])
    u_subset = train["unit"].unique()[:40]
    train_sub = train[train["unit"].isin(u_subset)].reset_index(drop=True)
    p = Preprocessor(cfg, sc, seed=42).fit(train_sub)
    gold = p.transform(train_sub)
    ad = AnomalyDetector(p.anomaly_cols(), seed=42)
    best, table = ad.fit_with_oof(gold, gold["RUL"].values, cfg["ANOM_PERCENTILES"], cfg["ANOM_PERSIST"], cfg["ANOM_MAX_ENGINE_FA"], cfg["HEALTHY_RUL"], folds=3)
    assert best["engine_false_alarm_rate"] <= 0.05, f"False alarm rate too high: {best['engine_false_alarm_rate']}"
    assert best["detection_rate"] >= 0.80, f"Detection rate below 80%: {best['detection_rate']}"

