import pytest
from shield.src.data import make_synthetic, validate_schema

def test_valid_ok():
    tr, _ = make_synthetic(5, 2); validate_schema(tr)

def test_duplicate_rows_rejected():
    tr, _ = make_synthetic(5, 2); import pandas as pd; bad = pd.concat([tr, tr.iloc[[3]]])
    with pytest.raises(ValueError): validate_schema(bad.reset_index(drop=True))

def test_gap_in_cycles_rejected():
    tr, _ = make_synthetic(5, 2); bad = tr.drop(tr.index[10]).reset_index(drop=True)
    with pytest.raises(ValueError): validate_schema(bad)

def test_wrong_columns_rejected():
    tr, _ = make_synthetic(5, 2)
    with pytest.raises(ValueError): validate_schema(tr.rename(columns={"s3": "x"}))
