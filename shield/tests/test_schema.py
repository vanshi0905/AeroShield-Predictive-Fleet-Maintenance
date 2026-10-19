import numpy as np
import pandas as pd
import pytest
from shield.src.data import make_synthetic, validate_schema, SENS
from shield.src.features import Preprocessor


def test_valid_ok():
    tr, _ = make_synthetic(5, 2)
    validate_schema(tr)


def test_duplicate_rows_rejected():
    tr, _ = make_synthetic(5, 2)
    bad = pd.concat([tr, tr.iloc[[3]]])
    with pytest.raises(ValueError, match="duplicate"):
        validate_schema(bad.reset_index(drop=True))


def test_gap_in_cycles_rejected():
    tr, _ = make_synthetic(5, 2)
    bad = tr.drop(tr.index[10]).reset_index(drop=True)
    with pytest.raises(ValueError, match="cycles not consecutive"):
        validate_schema(bad)


def test_wrong_columns_rejected():
    tr, _ = make_synthetic(5, 2)
    with pytest.raises(ValueError, match="expected 26 columns"):
        validate_schema(tr.rename(columns={"s3": "x"}))


def test_missing_values_accepted_and_causally_imputed(cfg):
    """Requirement R2 & Fault F4: Missing sensor values are NOT rejected at schema ingress.
    Instead, they are accepted, flagged via missing_share, and causally filled.
    """
    tr, _ = make_synthetic(5, 2)
    
    # Inject missing values (NaNs) across random sensor fields
    tr_missing = tr.copy()
    tr_missing.loc[5:15, ["s2", "s7", "s11"]] = np.nan
    tr_missing.loc[20, SENS[:5]] = np.nan

    # 1. Ingress schema validation must PASS (not reject data for missing values)
    validate_schema(tr_missing)

    # 2. Preprocessor must clean, record missing_share, and causally impute without NaNs
    prep = Preprocessor(cfg, {"clustering": False}).fit(tr)
    cleaned = prep.clean(tr_missing)

    assert "missing_share" in cleaned.columns
    assert (cleaned["missing_share"] > 0).any()
    assert not cleaned[SENS].isna().any().any(), "Cleaned sensors still contain unhandled NaNs!"
