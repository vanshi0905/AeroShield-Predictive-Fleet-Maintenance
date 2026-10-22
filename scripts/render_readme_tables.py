"""Render the README score tables straight from outputs/FD00x/metrics.json.

    python scripts/render_readme_tables.py --write   # rewrite the generated blocks in README.md
    python scripts/render_readme_tables.py --check   # exit 1 if README blocks differ from the metrics

No fallback values anywhere: a missing key raises, so a table can never show an invented number.
"""
import argparse, json, os, re, sqlite3, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "outputs")
README = os.path.join(ROOT, "README.md")
SUBSETS = ["FD001", "FD002", "FD003", "FD004"]
META = {
    "FD001": ("1 regime", "HPC Degradation"),
    "FD002": ("6 regimes", "HPC Degradation"),
    "FD003": ("1 regime", "HPC + Fan Degradation"),
    "FD004": ("6 regimes", "HPC + Fan Degradation")
}


def pct(x):
    return f"{x * 100:.1f}%"


def load(s):
    return json.load(open(os.path.join(OUT, s, "metrics.json")))


def blocks(M):
    t1 = [
        "| Dataset | Operating Regimes | Fault Modes | Test Engines | Uncapped RMSE | NASA Score (Uncapped) | Capped RMSE (95% CI) | Late % | Conformal Coverage (80% Target) | Coverage when RUL ≤ 50 | Engines Needing a Human (final) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for s in SUBSETS:
        m = M[s]
        lw = m["test_last_window"]
        ci = lw["ci95"]["rmse_capped_truth"]
        cond, fault = META[s]
        t1.append(
            f"| **{s}** | {cond} | {fault} | {lw['n_engines']} | **{lw['rmse_uncapped_truth']:.2f}** | **{lw['nasa_uncapped_truth']:,.1f}** | "
            f"{lw['rmse_capped_truth']:.2f} [{ci[0]:.1f}, {ci[1]:.1f}] | {pct(lw['late_share'])} | **{pct(lw['coverage'])}** | "
            f"{pct(lw['coverage_rul_le_50'])} | {m['severity_mix'].get('NEEDS_HUMAN', 0)} |"
        )
    t2 = [
        "| Dataset | Training: engines flagged | Training: false-alarm rate | Training: median lead (cycles) | Test: engines flagged | Test: false-alarm rate | Test: median lead (cycles) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for s in SUBSETS:
        a, t = M[s]["anomaly_oof_best"], M[s]["anomaly_test"]
        t2.append(
            f"| {s} | {pct(a['detection_rate'])} | {pct(a['engine_false_alarm_rate'])} | {a['median_lead_time']:.0f} | "
            f"{pct(t['detection_rate'])} ({t['alerted_engines']}/{t['engines']}) | {pct(t['engine_false_alarm_rate'])} | {t['median_lead_time']:.0f} |"
        )
    return {"SCORE_TABLE": "\n".join(t1), "ANOMALY_TABLE": "\n".join(t2)}


def db_open_exceptions(s):
    p = os.path.join(OUT, s, "work_orders.db")
    if not os.path.exists(p):
        return None
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        return c.execute("SELECT COUNT(*) FROM work_orders WHERE status='NEEDS_HUMAN'").fetchone()[0]
    finally:
        c.close()


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    M = {s: load(s) for s in SUBSETS}
    txt = open(README, encoding="utf-8").read()
    new = txt
    problems = []
    for name, body in blocks(M).items():
        b, e = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"
        pat = re.compile(re.escape(b) + r".*?" + re.escape(e), re.S)
        if not pat.search(new):
            problems.append(f"README is missing the {b} / {e} markers")
            continue
        block = f"{b}\n{body}\n{e}"
        if pat.search(new).group(0) != block:
            if a.write:
                new = pat.sub(lambda _: block, new)
            else:
                problems.append(f"README block {name} differs from outputs/*/metrics.json (run with --write)")
    stale = {s: M[s]["order_volume"]["stale_escalated"] for s in SUBSETS if M[s]["order_volume"].get("stale_escalated")}
    if stale:
        problems.append(f"metrics.json still show replay stale escalations {stale}: re-run `python run_all.py --all --reset`")
    print("Open NEEDS_HUMAN rows in each work_orders.db (these feed /api/exceptions):",
          {s: db_open_exceptions(s) for s in SUBSETS})
    if a.write and new != txt:
        open(README, "w", encoding="utf-8").write(new)
        print("README blocks rewritten from outputs/*/metrics.json")
    for p in problems:
        print("CHECK FAILED:", p)
    sys.exit(1 if (problems and a.check) else 0)


if __name__ == "__main__":
    main()
