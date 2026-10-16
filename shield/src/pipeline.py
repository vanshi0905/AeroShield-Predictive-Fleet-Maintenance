"""SHIELD master pipeline: ingest -> clean -> features -> models -> calibrate -> anomaly -> agent replay -> work orders -> MLOps."""
import os, json, time, yaml
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
import joblib

from .data import load_cmapss, inject_faults, SENS
from .features import Preprocessor
from .checks import SensorQualityGate
from .calibrate import (QuantileRULModel, RidgeRUL, tune_late_shift, smooth_by_engine, order_quantiles, CrossConformalCalibrator)
from .anomaly import AnomalyDetector
from .agent import TriageAgent
from .orders import OrderManager
from .evaluate import (nasa_score, rmse, last_window_metrics, all_window_metrics, truncation_points, coverage)
from . import mlops

VERSION = "v1"


def load_cfg(subset, config_dir="shield/config"):
    cfg = yaml.safe_load(open(os.path.join(config_dir, "thresholds.yaml")))
    sc = yaml.safe_load(open(os.path.join(config_dir, f"{subset.lower()}.yaml")))
    return cfg, sc


# ======================================================================= RUL system (models + calibration)
class RULSystem:
    """Quantile GBM + Ridge second model; OOF (GroupKFold by engine) -> late shift -> bounded-step smoother -> conformal."""

    def __init__(self, cfg, feature_cols, cap=125.0, seed=42, folds=5):
        self.cfg, self.cols, self.cap, self.seed, self.folds = cfg, feature_cols, cap, seed, folds

    def _weights(self, y): return 1.0 + (y <= self.cfg["NEAR_WEIGHT_RUL"])

    def fit(self, gold, verbose=True):
        c = self.cfg; cap = self.cap
        X = gold[self.cols].values; y = gold["RUL_capped"].values; u = gold["unit"].values; age = gold["cycle"].values
        o10, o50, o90, orr = (np.zeros(len(X)) for _ in range(4))
        self.fold_rmse = []
        for k, (tr, va) in enumerate(GroupKFold(self.folds).split(X, groups=u)):
            m = QuantileRULModel(cap, self.seed + k).fit(X[tr], y[tr], self._weights(y[tr]))
            o10[va], o50[va], o90[va] = m.predict_raw(X[va])
            orr[va] = RidgeRUL(cap).fit(X[tr], y[tr]).predict(X[va])
            self.fold_rmse.append(rmse(o50[va], y[va]))
            if verbose: print(f"   fold {k+1}/{self.folds}: raw RMSE {self.fold_rmse[-1]:.2f}")
        trunc = truncation_points(gold, c["CALIB_REPEATS"], seed=self.seed)
        # A2: late-bias shift on OOF truncation points
        self.shift = tune_late_shift(o50[trunc], y[trunc], c["LATE_SHIFT_GRID"], c["LATE_SHIFT_MAX_RMSE_RISE"])
        sh = lambda a: np.clip(a - self.shift, 0, cap)
        # P90 (optimistic bound) is NOT shifted: truth is capped, so a shifted P90 sits below the cap and creates an atom of
        # identical miss-scores that distorts the conformal quantile. Its coverage is handled by conformal widening.
        o10, o50, orr = sh(o10), sh(o50), sh(orr)
        # A3/A4: tune smoother on OOF
        best = None
        for a in c["SMOOTHER_GRID_ALPHA"]:
            for um in c["SMOOTHER_GRID_UMAX"]:
                s = smooth_by_engine(u, o50, a, c["D_MAX"], um, cap)
                score = nasa_score(s[trunc], y[trunc]) + 0 * rmse(s[trunc], y[trunc])
                if best is None or score < best[0]: best = (score, a, um)
        self.alpha, self.umax = best[1], best[2]
        sm = lambda a: smooth_by_engine(u, a, self.alpha, c["D_MAX"], self.umax, cap)
        s10, s50, s90 = order_quantiles(sm(o10), sm(o50), sm(o90), cap)
        sr = sm(orr)
        # A1: conformal widening AFTER shift+smoothing
        self.conf = CrossConformalCalibrator(c["CONFORMAL_LEVEL"], cap, c["SHORT_HISTORY_CYCLES"]).fit(s10[trunc], s90[trunc], y[trunc], age[trunc])
        w10, w90 = self.conf.widen(s10, s90, age)
        self.oof = pd.DataFrame({"unit": u, "cycle": age, "RUL": gold["RUL"].values, "RUL_capped": y,
                                 "raw_p50": o50 + self.shift, "p10": w10, "p50": s50, "p90": w90, "ridge_p50": sr})
        self.trunc = trunc
        d = np.abs(s50[trunc] - sr[trunc])
        self.disagree = float(max(c["DISAGREE_CYCLES"], np.percentile(d, 95)))
        self.oof_metrics = {"late_shift": self.shift, "smoother_alpha": self.alpha, "smoother_u_max": self.umax,
                            "conformal_q_standard": self.conf.q_std, "conformal_q_short": self.conf.q_short,
                            "oof_rmse": rmse(s50[trunc], y[trunc]), "oof_nasa": nasa_score(s50[trunc], y[trunc]),
                            "oof_late_share": float(np.mean(s50[trunc] > y[trunc])),
                            "oof_coverage": coverage(w10[trunc], w90[trunc], y[trunc]),
                            "oof_coverage_rul_le_50": coverage(w10[trunc], w90[trunc], y[trunc], y[trunc] <= 50),
                            "oof_coverage_short_history": coverage(w10[trunc], w90[trunc], y[trunc], age[trunc] < c["SHORT_HISTORY_CYCLES"]),
                            "raw_oof_coverage_before_conformal": coverage(s10[trunc], s90[trunc], y[trunc]),
                            "oof_rmse_before_shift_smoothing": rmse(np.clip(o50[trunc] + self.shift, 0, cap), y[trunc]),
                            "disagree_threshold": self.disagree, "fold_rmse_mean": float(np.mean(self.fold_rmse)), "fold_rmse_sd": float(np.std(self.fold_rmse))}
        # final models on ALL training engines
        self.model = QuantileRULModel(cap, self.seed).fit(X, y, self._weights(y))
        self.ridge = RidgeRUL(cap).fit(X, y)
        return self

    def predict(self, gold):
        """gold ordered by (unit,cycle). Streaming-equivalent: causal features + sequential smoother."""
        c = self.cfg; cap = self.cap; X = gold[self.cols].values; u = gold["unit"].values; age = gold["cycle"].values
        r10, r50, r90 = self.model.predict_raw(X)
        sh = lambda a: np.clip(a - self.shift, 0, cap)
        sm = lambda a: smooth_by_engine(u, a, self.alpha, c["D_MAX"], self.umax, cap)
        s10, s50, s90 = order_quantiles(sm(sh(r10)), sm(sh(r50)), sm(r90), cap)
        w10, w90 = self.conf.widen(s10, s90, age)
        return pd.DataFrame({"raw_p50": sh(r50), "p10": w10, "p50": s50, "p90": w90, "ridge_p50": sm(sh(self.ridge.predict(X)))}, index=gold.index)


# ======================================================================= fault-mode score (A8)
class FaultMode:
    """No labels exist: cluster end-of-life sensor signatures into 2 modes (offline, training only), then a causal
    classifier on degradation-phase features supplies P(mode B) as a feature. OOF probs used for training rows."""

    def fit_predict_oof(self, gold, sensors, seed=42):
        e = [f"{s}_ewma" for s in sensors]; m = [f"{s}_m15" for s in sensors]
        last = gold[gold["RUL"] <= 10].groupby("unit")[e].mean()
        km = KMeans(2, n_init=10, random_state=seed).fit(StandardScaler().fit_transform(last))
        lab = pd.Series(km.labels_, index=last.index)
        self.engine_mode = lab
        y = gold["unit"].map(lab).values; X = gold[m].values; u = gold["unit"].values; deg = gold["RUL_capped"].values < 125
        p = np.zeros(len(gold))
        for tr, va in GroupKFold(5).split(X, groups=u):
            t = tr[deg[tr]]
            clf = LogisticRegression(C=1.0, max_iter=300).fit(StandardScaler().fit(X[t]).transform(X[t]), y[t])
            sc = StandardScaler().fit(X[t]); p[va] = clf.predict_proba(sc.transform(X[va]))[:, 1]
        self.scaler = StandardScaler().fit(X[deg]); self.clf = LogisticRegression(C=1.0, max_iter=300).fit(self.scaler.transform(X[deg]), y[deg])
        self.m = m
        return p

    def predict(self, gold):
        return self.clf.predict_proba(self.scaler.transform(gold[self.m].values))[:, 1]


# ======================================================================= cost-calibrated thresholds (C1)
def calibrate_thresholds(oof, cfg, grid=None):
    """Grid-search severity thresholds on the OOF replay minimising C_fail*failures + C_early*life_discarded + C_order*orders."""
    cf, ce, co = cfg["COST_RATIO"]; per = []
    for u, g in oof.groupby("unit"):
        per.append((g["p10"].values, g["p50"].values, g["RUL"].values))
    grid = grid or {"crit_p10": [5, 10, 15], "crit_p50": [15, 20, 25, 30], "high_p50": [30, 40, 50, 60], "med_p50": [60, 70, 80, 90]}
    def run(c10, c50, h50, m50):
        cost = fails = orders = 0; disc = 0.0
        for p10, p50, rul in per:
            sev = np.where((p10 <= c10) | (p50 <= c50), 4, np.where(p50 <= h50, 3, np.where(p50 <= m50, 2, 0)))
            conf = np.minimum.reduce([sev[i:len(sev) - 2 + i] for i in range(3)]) if len(sev) >= 3 else np.zeros(0)
            hit = np.where(conf >= 3)[0]
            anyo = (conf >= 2).any()
            orders += int(anyo)
            if len(hit):
                t = hit[0] + 2; lead = 0 if conf[hit[0]] == 4 else 10
                if lead > rul[t]: fails += 1
                else: disc += rul[t] - lead
            else:
                fails += 1
        return cf * fails + ce * disc + co * orders, fails, disc, orders
    rows = []
    for c10 in grid["crit_p10"]:
        for c50 in grid["crit_p50"]:
            for h in grid["high_p50"]:
                for m in grid["med_p50"]:
                    if not (c50 < h < m): continue
                    cost, f, d, o = run(c10, c50, h, m)
                    rows.append({"CRIT_P10": c10, "CRIT_P50": c50, "HIGH_P50": h, "MED_P50": m, "cost": cost, "failures": f, "life_discarded": d, "orders": o})
    df = pd.DataFrame(rows).sort_values("cost")
    cur = run(cfg["CRIT_P10"], cfg["CRIT_P50"], cfg["HIGH_P50"], cfg["MED_P50"])
    return df.iloc[0].to_dict(), {"cost": cur[0], "failures": cur[1], "life_discarded": cur[2], "orders": cur[3]}, int(len(oof["unit"].unique()))


# ======================================================================= pipeline
class ShieldPipeline:
    def __init__(self, subset="FD001", data_dir="data", config_dir="shield/config", out_dir="outputs",
                 seed=42, tune_cap=False, no_regimes=False, inject=True):
        self.subset, self.data_dir, self.seed = subset, data_dir, seed
        self.cfg, self.sc = load_cfg(subset, config_dir)
        if no_regimes: self.sc["clustering"] = False
        self.out = os.path.join(out_dir, subset); os.makedirs(self.out, exist_ok=True)
        self.out_root = out_dir; self.tune_cap, self.inject = tune_cap, inject
        self.cap = float(self.cfg["CAP"]); self.tag = "_noregime" if no_regimes else ""

    # ---- optional cap cross-validation (A5) ----
    def run_cap_search(self, gold, cols):
        caps = [115, 120, 125, 130, 135]; res = []
        u = gold["unit"].values; X = gold[cols].values; yfull = gold["RUL"].values
        for cap in caps:
            pred = np.zeros(len(X))
            for tr, va in GroupKFold(5).split(X, groups=u):
                m = QuantileRULModel(cap, self.seed)
                from sklearn.ensemble import HistGradientBoostingRegressor
                r = HistGradientBoostingRegressor(max_iter=120, learning_rate=0.1, random_state=self.seed).fit(X[tr][::2], np.clip(yfull[tr], 0, cap)[::2])
                pred[va] = r.predict(X[va])
            tc = np.clip(yfull, 0, 125)                     # same yardstick for every cap
            tp = truncation_points(gold, 5, seed=1)
            res.append({"cap": cap, "rmse_vs_cap125_truth": rmse(np.clip(pred[tp], 0, 125), tc[tp]), "nasa_vs_cap125_truth": nasa_score(np.clip(pred[tp], 0, 125), tc[tp])})
        df = pd.DataFrame(res); df.to_csv(os.path.join(self.out, "cap_search.csv"), index=False)
        return df

    def run(self):
        t0 = time.time(); cfg, sc, cap = self.cfg, self.sc, self.cap
        train, test, source = load_cmapss(self.subset, self.data_dir, cap)
        print(f"\n{'='*70}\n SHIELD {VERSION}  subset={self.subset}  DATA SOURCE: {source.upper()}\n{'='*70}")
        # ---- Layer 1: data engineering
        prep = Preprocessor(cfg, sc, self.seed).fit(train)
        print(f"[1] sensors selected ({len(prep.sensors)}): {prep.sensors}" + (f"  regimes k={prep.k}" if prep.km is not None else ""))
        gate = SensorQualityGate(prep.sensors, cfg["MAX_NAN"], cfg["STUCK_WINDOW"], cfg["RANGE_MARGIN"], cfg["JUMP_K"]).fit(train, prep.normalize_raw(train))
        gtr, gte = prep.transform(train), prep.transform(test)
        cols = prep.feature_cols
        fm = None
        if sc.get("fault_modes", 1) > 1:
            fm = FaultMode(); gtr["fault_mode_p"] = fm.fit_predict_oof(gtr, prep.sensors, self.seed); gte["fault_mode_p"] = fm.predict(gte)
            cols = cols + ["fault_mode_p"]
            print(f"[1] fault-mode score added; end-of-life clusters: {fm.engine_mode.value_counts().to_dict()}")
        if self.tune_cap:
            print("[1] cap cross-validation:\n", self.run_cap_search(gtr, cols).round(2).to_string(index=False))
        data_hash = mlops.hash_df(train[["unit", "cycle", "s2", "s11"]]); cfg_hash = mlops.hash_obj({**cfg, **sc})
        # ---- Layer 2: models + calibration + anomaly
        print("[2] training quantile RUL models (GroupKFold by engine) ...")
        rul = RULSystem(cfg, cols, cap, self.seed).fit(gtr)
        om = rul.oof_metrics
        print(f"[2] OOF: shift={om['late_shift']}  smoother(alpha={om['smoother_alpha']},u_max={om['smoother_u_max']})  conformal q={om['conformal_q_standard']:.1f}  "
              f"coverage {om['raw_oof_coverage_before_conformal']*100:.0f}% -> {om['oof_coverage']*100:.0f}%")
        ad = AnomalyDetector(prep.anomaly_cols(), self.seed)
        best_a, table_a = ad.fit_with_oof(gtr, gtr["RUL"].values, cfg["ANOM_PERCENTILES"], cfg["ANOM_PERSIST"], cfg["ANOM_MAX_ENGINE_FA"], cfg["HEALTHY_RUL"])
        print(f"[2] anomaly threshold p{best_a['percentile']}: OOF median lead {best_a['median_lead_time']:.0f} cycles, engine false-alarm {best_a['engine_false_alarm_rate']*100:.1f}%")
        # ---- test scoring (official test set, scored ONCE after every choice is frozen)
        pred = rul.predict(gte)
        te = pd.concat([gte[["unit", "cycle", "RUL", "RUL_capped", "short_history", "missing_share"]], pred], axis=1)
        te["anomaly_score"] = ad.score_smoothed(gte)
        te["alert"] = AnomalyDetector.confirmed(te["unit"].values, te["anomaly_score"].values > ad.threshold, cfg["ANOM_PERSIST"])
        li = te.groupby("unit").tail(1)
        lw = last_window_metrics(li["unit"].values, li["cycle"].values, li["p10"].values, li["p50"].values, li["p90"].values,
                                 li["RUL_capped"].values, li["RUL"].values, cap, cfg["NEAR_FAILURE_RUL"])
        aw = all_window_metrics(te["p50"].values, te["RUL_capped"].values, te["RUL"].values)
        anom_test = AnomalyDetector.engine_metrics(te["unit"].values, te["RUL"].values, te["alert"].values, cfg["HEALTHY_RUL"])
        if fm is not None:
            md = (gte.groupby("unit")["fault_mode_p"].last() > 0.5).astype(int)
            lw["rmse_by_predicted_fault_mode"] = {int(k): rmse(li.loc[li["unit"].isin(md.index[md == k]), "p50"], li.loc[li["unit"].isin(md.index[md == k]), "RUL_capped"]) for k in (0, 1) if (md == k).any()}
        rt = test.sort_values(["unit", "cycle"]).reset_index(drop=True); flags = gate.flags(rt, prep.normalize_raw(rt)); flags.index = te.index
        print(f"[2] TEST last-window: RMSE {lw['rmse_capped_truth']:.2f} (vs capped truth) / {lw['rmse_uncapped_truth']:.2f} (uncapped)  NASA(uncapped) {lw['nasa_uncapped_truth']:.0f}  "
              f"late {lw['late_share']*100:.0f}%  coverage {lw['coverage']*100:.0f}%  [CI95 RMSE {lw['ci95']['rmse_capped_truth'][0]:.1f}-{lw['ci95']['rmse_capped_truth'][1]:.1f}]")
        print(f"[2] TEST all-window: RMSE {aw['rmse']:.2f} over {aw['n_windows']} windows; anomaly engine false-alarm {anom_test['engine_false_alarm_rate']*100:.1f}%")
        # ---- cost-calibrated thresholds (C1)
        best_thr, cur_thr, n_eng = calibrate_thresholds(rul.oof, cfg)
        if cfg.get("USE_CALIBRATED_THRESHOLDS"):
            cfg = {**cfg, **{k: best_thr[k] for k in ("CRIT_P10", "CRIT_P50", "HIGH_P50", "MED_P50")}}
        # ---- Layer 4/5: agent replay in fleet lockstep -> work orders
        db = os.path.join(self.out, "work_orders.db")
        if os.path.exists(db): os.remove(db)
        subsystem = {s: v["subsystem"] for s, v in cfg["SENSORS"].items()}
        om_ = OrderManager(db, subsystem, cfg["MEDIUM_BUDGET"], cfg["WINDOW_CYCLES"], VERSION, cfg["RULE_VERSION"], cfg_hash,
                           cfg["STALE_FACTOR"], cfg["REOPEN_WINDOW"], cfg["REOPEN_LIMIT"])
        dev = prep.deviation(gte); agree_cnt = (dev > cfg["AGREE_SD"]).sum(axis=1)
        te["agree_count"] = agree_cnt
        agent = TriageAgent({**cfg, "DISAGREE_CYCLES": rul.disagree})
        order = np.lexsort((te["unit"].values, te["cycle"].values))
        sev, st, unc, why = ["NORMAL"] * len(te), ["NORMAL"] * len(te), ["NORMAL"] * len(te), [""] * len(te)
        arr = {k: te[k].values for k in ("unit", "cycle", "p10", "p50", "p90", "alert", "ridge_p50")}
        okf, rsn = flags["ok"].values, flags["reason"].values; sens = np.array(prep.sensors); last_win = -1
        pos = {ix: i for i, ix in enumerate(te.index)}
        for i in order:
            w = int(arr["cycle"][i]) // cfg["WINDOW_CYCLES"]
            if w != last_win: om_.release_queued(w); last_win = w
            d = agent.evaluate(int(arr["unit"][i]), int(arr["cycle"][i]), arr["p10"][i], arr["p50"][i], arr["p90"][i], bool(arr["alert"][i]),
                               dq=(bool(okf[i]), rsn[i]), agree=(agree_cnt[i] >= cfg["MIN_AGREE_SENSORS"], int(agree_cnt[i])), second_model_p50=arr["ridge_p50"][i])
            sev[i], st[i], unc[i], why[i] = d["severity"], d["status"], d["unconfirmed_severity"], d["exception_reason"] or ""
            if d["status"] in ("AUTO_CREATED", "NEEDS_HUMAN"):
                top = sens[np.argsort(-dev[i])[:3]].tolist()
                om_.process_agent_decision(d, top)
            if i % 2000 == 0: om_.conn.commit()
        te["severity"], te["status"], te["unconfirmed_severity"], te["exception_reason"] = sev, st, unc, why
        om_.conn.commit()
        # simulated sensor faults -> human exception path (demo of C2/C4)
        fault_demo = {}
        if self.inject:
            fin = te.groupby("unit").tail(1); cand = fin[(fin["status"] == "NORMAL")]["unit"].tolist()[:3]
            if len(cand) == 3:
                raw_t = test.sort_values(["unit", "cycle"]).reset_index(drop=True)
                inj, kinds = inject_faults(raw_t, cand, self.seed)
                f2 = gate.flags(inj, prep.normalize_raw(inj))
                for u_, kind in kinds.items():
                    ix = np.where(inj["unit"].values == u_)[0][-1]; row = te.index[ix]
                    d = TriageAgent(cfg).evaluate(int(u_), int(inj["cycle"].iat[ix]), te.at[row, "p10"], te.at[row, "p50"], te.at[row, "p90"], False,
                                                  dq=(bool(f2["ok"].iat[ix]), f2["reason"].iat[ix]))
                    d["exception_reason"] = f"[SIMULATED FAULT: {kind}] " + (d["exception_reason"] or "")
                    om_.process_agent_decision(d, [])
                    fault_demo[int(u_)] = {"injected": kind, "status": d["status"], "reason": d["exception_reason"]}
                om_.conn.commit()
                print(f"[5] fault injection demo -> {sum(v['status']=='NEEDS_HUMAN' for v in fault_demo.values())}/3 routed to human queue")
        stale = om_.flag_stale(int(te["cycle"].max()))
        ok, msg = om_.verify_audit_chain()
        final = te.groupby("unit").tail(1)
        counts = final["severity"].where(final["status"] != "NEEDS_HUMAN", "NEEDS_HUMAN").value_counts().to_dict()
        n_orders = om_.conn.execute("SELECT COUNT(*) FROM work_orders WHERE order_id LIKE 'WO-%'").fetchone()[0]
        horizon = int(te["cycle"].max()); n_units = te["unit"].nunique()
        vol = {"work_orders": n_orders, "orders_per_100_engines_per_100_cycles": 100 * 100 * n_orders / (n_units * horizon),
               "orders_per_100_engines": 100 * n_orders / n_units, "stale_escalated": len(stale)}
        print(f"[5] final severity mix: {counts}   work orders: {n_orders}   audit: {msg}")
        om_.close()
        # ---- persist artifacts for dashboard
        keep = te.copy()
        for j, s in enumerate(prep.sensors): keep[f"dev_{s}"] = dev[:, j].round(2); keep[f"z_{s}"] = gte[f"{s}_norm"].values.round(3)
        keep.to_parquet(os.path.join(self.out, "predictions.parquet"))
        rul.oof.to_parquet(os.path.join(self.out, "oof_predictions.parquet"))
        json.dump(table_a, open(os.path.join(self.out, "anomaly_threshold_table.json"), "w"), indent=2)
        json.dump({"selected": prep.sensors, **{k: v for k, v in prep.sel_report.items() if k != "selected"}}, open(os.path.join(self.out, "selected_sensors.json"), "w"), indent=2)
        json.dump({"best": best_thr, "current_thresholds": cur_thr, "engines": n_eng, "cost_ratio": cfg["COST_RATIO"], "note": "placeholder costs"},
                  open(os.path.join(self.out, "thresholds_calibrated.json"), "w"), indent=2)
        gate_rates = mlops.data_quality_drift(flags)
        metrics = {"subset": self.subset, "version": VERSION, "data_source": source, "seconds": round(time.time() - t0),
                   "n_features": len(cols), "n_sensors": len(prep.sensors), "regimes": prep.k, "silhouette": prep.sel_report.get("silhouette"),
                   "test_last_window": lw, "test_all_window": aw, "oof": om, "anomaly_oof_best": best_a, "anomaly_test": anom_test,
                   "severity_mix": counts, "order_volume": vol, "audit_ok": ok, "audit_msg": msg, "fault_demo": fault_demo,
                   "data_quality": gate_rates, "config_hash": cfg_hash, "data_hash": data_hash}
        json.dump(metrics, open(os.path.join(self.out, f"metrics{self.tag}.json"), "w"), indent=2, default=float)
        bundle = {"prep": prep, "rul": rul, "anomaly": ad, "gate": gate, "cfg": cfg, "fm": fm}
        for o in (rul,): o.oof = None
        joblib.dump(bundle, os.path.join(self.out, f"model_{VERSION}.joblib"), compress=3)
        # ---- Layer 3: MLflow + registry
        flat = {"rmse": lw["rmse_capped_truth"], "mae": lw["mae_capped_truth"], "nasa": lw["nasa_uncapped_truth"], "late_share": lw["late_share"],
                "coverage": lw["coverage"], "near_recall": lw.get("near_recall", np.nan), "near_precision": lw.get("near_precision", np.nan), **{f"oof_{k}": v for k, v in om.items() if isinstance(v, float)}}
        mlops.log_mlflow(self.subset, {"subset": self.subset, "cap": cap, "seed": self.seed, "config_hash": cfg_hash, "data_hash": data_hash,
                                       "folds": 5, "fold_rmse": [round(x, 2) for x in rul.fold_rmse], "model": "HGB-quantile+Ridge"},
                         flat, {"stage": "train", "trigger": "initial", "version": VERSION}, db=os.path.join(self.out_root, "mlflow.db"))
        if not self.tag:
            reg = mlops.ModelRegistry(os.path.join(self.out_root, "registry.json"))
            reg.register_champion(self.subset, VERSION, flat, os.path.join(self.out, f"model_{VERSION}.joblib"))
        print(f"[done] {self.subset} in {time.time()-t0:.0f}s -> {self.out}")
        return metrics
