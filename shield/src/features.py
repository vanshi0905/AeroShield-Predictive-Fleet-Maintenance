"""Layer 1b - Cleaning (silver), regimes, computed sensor selection, causal features (gold)."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from .data import OPS, SENS

WIN_S, WIN_M, WIN_STD, WIN_SLOPE, EWMA_A, BASE_N = 5, 15, 10, 10, 0.2, 20


def _roll_sum(c, w):
    out = c.copy()
    out[w:] = c[w:] - c[:-w]
    return out


def engine_features(z, cycle_idx=None):
    """z: (T,S) regime-normalised sensors of ONE engine, time-ordered. Trailing windows only.
    Returns dict name -> (T,S). Pure function of rows <= t, so batch == stream (parity test)."""
    T, S = z.shape
    t = np.arange(T, dtype=float)
    n = lambda w: np.minimum(t + 1, w)[:, None]
    c1 = np.cumsum(z, 0); c2 = np.cumsum(z ** 2, 0)
    def rmean(w): return _roll_sum(c1, w) / n(w)
    m5, m15 = rmean(WIN_S), rmean(WIN_M)
    nw = n(WIN_STD); mean10 = rmean(WIN_STD)
    var = (_roll_sum(c2, WIN_STD) - nw * mean10 ** 2) / np.maximum(nw - 1, 1)
    std10 = np.sqrt(np.clip(var, 0, None)); std10[t < 1] = 0
    # slope over WIN_SLOPE cycles by rolling least squares on position index
    w = WIN_SLOPE; nn = np.minimum(t + 1, w)
    cu = np.cumsum(t); cuu = np.cumsum(t ** 2); cux = np.cumsum(t[:, None] * z, 0)
    Su, Suu, Sx, Sux = _roll_sum(cu, w), _roll_sum(cuu, w), _roll_sum(c1, w), _roll_sum(cux, w)
    den = Suu - Su ** 2 / nn
    num = Sux - (Su / nn)[:, None] * Sx
    slope = np.where((nn >= 3)[:, None], num / np.where(den > 0, den, 1)[:, None], 0.0)
    ewma = pd.DataFrame(z).ewm(alpha=EWMA_A, adjust=False).mean().values
    return {"m5": m5, "m15": m15, "std10": std10, "slope10": slope, "ewma": ewma}


class Preprocessor:
    """Fit on TRAIN engines only; apply identically to train/test/stream (no train/serve skew)."""

    def __init__(self, cfg, subset_cfg, seed=42):
        self.cfg, self.sc, self.seed = cfg, subset_cfg, seed
        self.km = None; self.k = 1
        self.sensors = None; self.sel_report = {}

    # ---------------- cleaning (silver) ----------------
    def clean(self, df):
        d = df.sort_values(["unit", "cycle"]).copy()
        d["missing_share"] = d[SENS].isna().mean(axis=1)           # recorded BEFORE filling
        d[SENS] = d.groupby("unit")[SENS].ffill()                  # causal gap fill (no back-fill/interp: non-causal)
        d[SENS] = d[SENS].fillna(self.med)                         # leading gaps -> training median
        if not (self.sc or {}).get("clustering", False):
            spk = d.groupby("unit")[SENS].transform(lambda s: s.rolling(3, min_periods=1).median())
            d[SENS] = spk                                          # trailing 3-pt median spike filter (single regime)
        d[SENS] = d[SENS].clip(self.lo, self.hi, axis=1)           # winsorise (never delete rows)
        return d

    def _regime(self, d):
        if self.km is None:
            return np.zeros(len(d), int)
        return self.km.predict(self.ops_scaler(d[OPS].values))

    def ops_scaler(self, x):
        return (x - self.ops_mu) / self.ops_sd

    def fit(self, train):
        d = train
        self.med = d[SENS].median()
        mad = (d[SENS] - self.med).abs().median() * 1.4826
        madf = mad.where(mad > 0, d[SENS].std())
        self.lo, self.hi = self.med - 4 * madf, self.med + 4 * madf
        # winsorise limits wide enough for rare real excursions: use max(4 robust SD, 99.99 pct)
        q = d[SENS].quantile([0.0001, 0.9999]); self.lo = np.minimum(self.lo, q.loc[0.0001]); self.hi = np.maximum(self.hi, q.loc[0.9999])
        self.ops_mu, self.ops_sd = d[OPS].mean().values, d[OPS].std().replace(0, 1).values
        if self.sc.get("clustering", False):
            Xo = self.ops_scaler(d[OPS].values)
            sub = Xo[np.random.default_rng(self.seed).choice(len(Xo), min(4000, len(Xo)), replace=False)]
            sil = {}
            for k in range(4, 9):
                lab = KMeans(k, n_init=3, random_state=self.seed).fit_predict(sub)
                sil[k] = float(silhouette_score(sub, lab))
            self.sel_report["silhouette"] = sil
            self.k = max(sil, key=sil.get) if self.sc.get("auto_k", True) else self.sc["n_regimes"]
            self.sel_report["k_chosen"] = self.k
            self.km = KMeans(self.k, n_init=10, random_state=self.seed).fit(Xo)
        reg = self._regime(d)
        # per-regime stats on raw training sensors (before sensor selection)
        self.stats = {}
        for r in np.unique(reg):
            g = d.loc[reg == r, SENS]
            self.stats[r] = (g.mean(), g.std().replace(0, np.nan))
        # computed sensor selection (problem A9)
        z = self._norm_all(d, reg)
        rel = {s: np.nanmin([self.stats[r][1][s] / (abs(self.stats[r][0][s]) + 1e-9) for r in self.stats]) for s in SENS}
        rho = {}
        for s in SENS:
            vals = []
            for u, g in d.groupby("unit"):
                x = z.loc[g.index, s].values
                if np.isfinite(x).all() and x.std() > 0:
                    vals.append(abs(spearmanr(g["cycle"].values, x)[0]))
            rho[s] = float(np.nanmedian(vals)) if vals else 0.0
        keep = [s for s in SENS if np.isfinite(rel[s]) and rel[s] > self.cfg["SENSOR_REL_STD_MIN"]
                and rho[s] > self.cfg["SENSOR_SPEARMAN_MIN"]]
        self.sensors = keep
        self.sel_report.update({"selected": keep, "median_abs_spearman": rho, "rel_std": {k: float(v) for k, v in rel.items()}})
        # sensor degradation direction, healthy-state baseline and robust SD (for agreement gate / drivers)
        zt = z[keep]
        sgn = {s: float(np.sign(np.corrcoef(zt[s], d["RUL"])[0, 1])) * -1 for s in keep} if "RUL" in d else {s: 1.0 for s in keep}
        self.dir = sgn
        early = d["cycle"] <= BASE_N
        self.fleet_base = zt[early].mean()
        ew = zt.groupby(d["unit"]).transform(lambda x: x.ewm(alpha=EWMA_A, adjust=False).mean())
        own = zt.groupby(d["unit"]).transform(lambda x: x.iloc[:BASE_N].mean())          # each engine's own early baseline
        hl = (d["cycle"] > BASE_N) & (d["cycle"] <= 2 * BASE_N + 5)
        r = (ew - own)[hl]
        self.fleet_sd = ((r - r.median()).abs().median() * 1.4826).clip(lower=1e-3)       # within-engine noise of the smoothed level
        eb = zt[early].groupby(d.loc[early, "unit"]).mean()
        self.eng_base_mu, self.eng_base_sd = eb.mean(), eb.std().clip(lower=1e-6)
        return self

    def normalize_raw(self, df):
        """Regime-normalised RAW sensors (no cleaning, NaNs kept) - used by the jump check so that legitimate
        operating-condition changes are not mistaken for sensor faults."""
        d = df.sort_values(["unit", "cycle"]); z = self._norm_all(d, self._regime(d))[self.sensors]
        return z.reindex(df.index)

    def _norm_all(self, d, reg):
        z = pd.DataFrame(index=d.index, columns=SENS, dtype=float)
        for r in np.unique(reg):
            m = reg == r
            mu, sd = self.stats.get(r, self.stats[min(self.stats)])
            z.loc[m, SENS] = (d.loc[m, SENS].values - mu.values) / sd.values
        return z

    # ---------------- gold features ----------------
    def transform(self, df, already_clean=False):
        """Returns gold DataFrame: meta cols + features. One row per input row."""
        d = df if already_clean else self.clean(df)
        reg = self._regime(d)
        z = self._norm_all(d, reg)[self.sensors]
        S = len(self.sensors)
        names = ["norm", "m5", "m15", "std10", "slope10", "ewma", "dbase"]
        feats = {k: [] for k in names}; cyc = []; fb = []
        fbm, fbs = self.eng_base_mu.values, self.eng_base_sd.values
        for u, idx in d.groupby("unit").indices.items():
            zz = np.nan_to_num(z.values[idx]); T = len(idx)
            f = engine_features(zz)
            cs = np.cumsum(zz, 0); n = np.minimum(np.arange(T) + 1, BASE_N)[:, None]
            cs = np.where(np.arange(T)[:, None] >= BASE_N, cs[BASE_N - 1] if T >= BASE_N else cs, cs)
            base = cs / n
            zb = np.abs((base - fbm) / fbs).max(axis=1)
            fallback = (zb > 4.0) | (np.arange(T) < 4)
            base = np.where(fallback[:, None], self.fleet_base.values[None, :], base)
            f["norm"] = zz; f["dbase"] = zz - base
            for k in names:
                feats[k].append(f[k])
            fb.append(fallback)
        order = np.concatenate([idx for _, idx in d.groupby("unit").indices.items()])
        meta = d.iloc[order][["unit", "cycle"] + [c for c in ("RUL", "RUL_capped") if c in d]].copy()
        blocks = {}
        for k in names:
            M = np.vstack(feats[k])
            for j, s in enumerate(self.sensors):
                blocks[f"{s}_{k}"] = M[:, j]
        blocks["baseline_fallback"] = np.concatenate(fb)
        blocks["missing_share"] = d.iloc[order]["missing_share"].values
        blocks["regime"] = reg[order]
        # Aerodynamic interaction ratios: fan/core speed (s8/s9), corrected speed (s13/s14),
        # pressure drop (s11/s7), and temperature ratio (s4/s3)
        eps = 1e-6
        for num_c, den_c, col_name in [
            ("s8", "s9", "ratio_s8_s9"),
            ("s13", "s14", "ratio_s13_s14"),
            ("s11", "s7", "ratio_s11_s7"),
            ("s4", "s3", "ratio_s4_s3"),
        ]:
            if num_c in d.columns and den_c in d.columns:
                num = d.iloc[order][num_c].values
                den = d.iloc[order][den_c].values
                blocks[col_name] = np.where(np.abs(den) > eps, num / den, 1.0)
            else:
                blocks[col_name] = np.ones(len(order), dtype=float)
        out = pd.concat([meta, pd.DataFrame(blocks, index=meta.index)], axis=1)
        out["short_history"] = out["cycle"] < self.cfg["SHORT_HISTORY_CYCLES"]
        return out.sort_index()

    @property
    def feature_cols(self):
        ratios = ["ratio_s8_s9", "ratio_s13_s14", "ratio_s11_s7", "ratio_s4_s3"]
        return [f"{s}_{k}" for k in ("norm", "m5", "m15", "std10", "slope10", "ewma", "dbase") for s in self.sensors] + ratios + ["cycle"]

    def anomaly_cols(self):
        return [f"{s}_dbase" for s in self.sensors]

    def deviation(self, gold):
        """Deviation (in robust SD) of the EWMA level from the engine's OWN early-life baseline, in the degradation direction."""
        e = gold[[f"{s}_ewma" for s in self.sensors]].values
        own_base = gold[[f"{s}_norm" for s in self.sensors]].values - gold[[f"{s}_dbase" for s in self.sensors]].values
        dev = (e - own_base) / self.fleet_sd.values
        return dev * np.array([self.dir[s] for s in self.sensors])
