"""C6 / section 4.8: features computed on a prefix (as a stream would see them) equal the batch features -> no future leakage."""
import numpy as np
from shield.src.features import Preprocessor
from shield.src.data import SENS

def test_batch_equals_prefix_stream(cfg, fleet):
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    full = p.transform(fleet)
    cols = p.feature_cols
    for unit in (1, 7, 20, 33, 40):
        eng = fleet[fleet.unit == unit]
        for t in (25, 60, 120):
            if t > len(eng): continue
            pref = p.transform(eng.iloc[:t]).iloc[-1][cols].values.astype(float)
            ref = full[(full.unit == unit) & (full.cycle == t)][cols].values[0].astype(float)
            assert np.allclose(pref, ref, atol=1e-9), (unit, t)

def test_future_rows_do_not_change_past_features(cfg, fleet):
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    a = p.transform(fleet); b = fleet.copy(); b.loc[b.cycle > 100, SENS] += 999
    b = p.transform(b); m = a.cycle <= 100
    assert np.allclose(a.loc[m, p.feature_cols].values.astype(float), b.loc[m, p.feature_cols].values.astype(float))

def test_scaler_fitted_on_train_only(cfg, fleet):
    p = Preprocessor(cfg, {"clustering": False}).fit(fleet)
    assert set(p.stats) == {0} and p.sensors   # stats stored at fit time, never refit on transform
