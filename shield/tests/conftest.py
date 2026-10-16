import os, sys, yaml, numpy as np, pandas as pd, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from shield.src.data import make_synthetic, COLS, SENS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

@pytest.fixture(scope="session")
def cfg():
    return yaml.safe_load(open(os.path.join(ROOT, "shield/config/thresholds.yaml")))

@pytest.fixture(scope="session")
def fleet():
    tr, te = make_synthetic(40, 10, seed=1)
    tr["RUL"] = tr.groupby("unit")["cycle"].transform("max") - tr["cycle"]
    return tr
