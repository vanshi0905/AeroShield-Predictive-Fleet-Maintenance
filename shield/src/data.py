"""Layer 1a - Ingestion (bronze), schema checks, synthetic fallback, fault injection."""
import os
import numpy as np
import pandas as pd

OPS = ["op1", "op2", "op3"]
SENS = [f"s{i}" for i in range(1, 22)]
COLS = ["unit", "cycle"] + OPS + SENS


def validate_schema(df, name="data"):
    if list(df.columns[:26]) != COLS:
        raise ValueError(f"{name}: expected 26 columns {COLS[:5]}...")
    if df.duplicated(["unit", "cycle"]).any():
        raise ValueError(f"{name}: duplicate unit/cycle rows")
    bad = df.groupby("unit")["cycle"].apply(lambda c: not (c.diff().dropna() == 1).all())
    if bad.any():
        raise ValueError(f"{name}: cycles not consecutive for units {list(bad[bad].index[:5])}")


def _read(path):
    df = pd.read_csv(path, sep=r"\s+", header=None).dropna(axis=1, how="all")
    df.columns = COLS
    return df


def load_cmapss(subset, data_dir="data", cap=125):
    """Return (train, test, source). RUL (uncapped) and RUL_capped are added.
    Test RUL at earlier cycles t = RUL_final + (T - t)  (all-window truth, problem B5)."""
    tp = os.path.join(data_dir, f"train_{subset}.txt")
    if not os.path.exists(tp):
        print(f"[WARN] {tp} not found -> SYNTHETIC fleet used. Results are NOT NASA benchmark numbers.")
        tr, te = make_synthetic(seed=0)
        source = "synthetic"
    else:
        tr = _read(tp)
        te = _read(os.path.join(data_dir, f"test_{subset}.txt"))
        rul = pd.read_csv(os.path.join(data_dir, f"RUL_{subset}.txt"), header=None, sep=r"\s+")[0].values
        te["_final"] = te["unit"].map(dict(zip(sorted(te["unit"].unique()), rul)))
        source = "real"
    validate_schema(tr, "train")
    validate_schema(te.drop(columns=["_final"], errors="ignore"), "test")
    tr["RUL"] = tr.groupby("unit")["cycle"].transform("max") - tr["cycle"]
    if "_final" in te:
        te["RUL"] = te["_final"] + (te.groupby("unit")["cycle"].transform("max") - te["cycle"])
        te = te.drop(columns="_final")
    for d in (tr, te):
        d["RUL_capped"] = d["RUL"].clip(0, cap)
    return tr.reset_index(drop=True), te.reset_index(drop=True), source


def make_synthetic(n_train=40, n_test=20, seed=0):
    """Tiny C-MAPSS-style fleet for tests / offline smoke runs only."""
    rng = np.random.default_rng(seed)
    def fleet(n, truncate):
        rows = []
        for u in range(1, n + 1):
            T = int(rng.integers(150, 260)); cut = T if not truncate else int(T * rng.uniform(0.35, 0.95))
            t = np.arange(1, T + 1)
            h = (t / T) ** 2
            for c in range(cut):
                r = [u, c + 1, 0.0, 0.0, 100.0]
                for i in range(21):
                    base = 100 + 10 * i
                    slope = (-1) ** i * (3 + i % 5) * (0 if i in (0, 4, 5, 9, 15, 17, 18) else 1)
                    r.append(base + slope * h[c] + rng.normal(0, 0.3))
                rows.append(r)
        d = pd.DataFrame(rows, columns=COLS)
        return d
    tr = fleet(n_train, False); te = fleet(n_test, True)
    last = te.groupby("unit")["cycle"].max()
    te["_final"] = te["unit"].map(lambda u: int(rng.integers(5, 60)))
    return tr, te


def inject_faults(df, units, seed=0):
    """Return a copy of the raw stream with simulated faults (demo of the human-exception path).
    units[0]: 25% dropout in last 10 cycles; units[1]: one sensor stuck 8 cycles; units[2]: 10-SD spike."""
    rng = np.random.default_rng(seed)
    d = df.copy()
    sd = d[SENS].std()
    kinds = {}
    def last_idx(u, n):
        return d.index[d["unit"] == u][-n:]
    if len(units) > 0:
        idx = last_idx(units[0], 10)
        for s in rng.choice(SENS, 6, replace=False):   # 6 of ~14-21 sensors blank -> >20% share on every row
            d.loc[idx, s] = np.nan
        kinds[units[0]] = "dropout"
    if len(units) > 1:
        idx = last_idx(units[1], 8)
        d.loc[idx, "s11"] = d.loc[idx[0], "s11"]
        kinds[units[1]] = "stuck sensor s11"
    if len(units) > 2:
        idx = last_idx(units[2], 1)
        d.loc[idx, "s7"] = d.loc[idx, "s7"] + 10 * sd["s7"] * 25
        kinds[units[2]] = "spike s7"
    return d, kinds
