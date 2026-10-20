"""AeroShield Autonomous Self-Improvement & Tournament Optimization Runner.

Executes closed-loop hyperparameter tournaments, Bayesian-style search,
and 4-gate validation to iteratively improve model accuracy toward and beyond SOTA.

Usage:
    python run_self_improvement.py --subset FD001 --iterations 10 --auto-promote
    python run_self_improvement.py --all --iterations 15 --auto-promote
"""

import argparse
import os
import sys
import time

from shield.src.pipeline import load_cfg
from shield.src.data import load_cmapss
from shield.src.features import Preprocessor
from shield.src.self_improver import SelfImprovementEngine, DEFAULT_SEARCH_SPACE, COMPACT_SEARCH_SPACE


def run_self_improvement_for_subset(subset, data_dir="data", config_dir="shield/config",
                                    out_dir="outputs", iterations=10, rounds=3,
                                    search_type="compact", auto_promote=False, seed=42,
                                    allow_synthetic=False):
    print("\n" + "=" * 78)
    print(f"  AEROSHIELD AUTONOMOUS SELF-IMPROVEMENT FLYWHEEL: {subset}")
    print(f"  Target: Elevating performance toward SOTA benchmarks")
    print(f"  Iterations: {iterations} | Rounds: {rounds} | Auto-Promote: {auto_promote}")
    print("=" * 78)

    cfg, sc = load_cfg(subset, config_dir)
    cap = float(cfg["CAP"])
    
    # 1. Load operational data
    print(f"[1/4] Loading {subset} fleet data from '{data_dir}'...")
    train, test, source = load_cmapss(subset, data_dir, cap, allow_synthetic=allow_synthetic)
    print(f"      Loaded {train['unit'].nunique()} training engines ({len(train)} cycles), data source: {source}")

    # 2. Extract features
    print(f"[2/4] Fitting preprocessor and generating causal features...")
    t0 = time.time()
    prep = Preprocessor(cfg, sc, seed).fit(train)
    gold = prep.transform(train)
    print(f"      Features generated ({len(prep.feature_cols)} cols) in {time.time()-t0:.1f}s")

    # 3. Setup self-improvement engine
    space = DEFAULT_SEARCH_SPACE if search_type == "full" else COMPACT_SEARCH_SPACE
    engine = SelfImprovementEngine(
        subset=subset,
        gold=gold,
        feature_cols=prep.feature_cols,
        cap=cap,
        seed=seed,
        out_dir=out_dir,
        search_space=space,
    )

    # 4. Run tournament rounds
    print(f"[3/4] Launching tournament iterations with 4-gate validation...")
    round_results = engine.run_iterative(
        total_iterations=iterations,
        batch_size=max(2, iterations // rounds),
        max_rounds=rounds,
        verbose=True,
        auto_promote=auto_promote,
    )

    # 5. Summary & Promotion
    print(f"\n[4/4] Tournament complete. Analyzing promotion candidates...")
    any_promoted = False
    for r_idx, res in enumerate(round_results, 1):
        if res.get("promoted") and res.get("best_challenger"):
            any_promoted = True
            bm = res["best_challenger"]["metrics"]
            cb = res["champion_before"]
            print(f"  >>> Winner in Round {r_idx}:")
            print(f"      RMSE: {cb['rmse']:.2f} -> {bm['rmse']:.2f} ({bm['rmse']-cb['rmse']:+.2f})")
            print(f"      NASA: {cb['nasa']:.1f} -> {bm['nasa']:.1f} ({bm['nasa']-cb['nasa']:+.1f})")
            print(f"      Coverage: {bm['coverage']*100:.1f}% (target >= 80%)")
            print(f"      Late Share: {bm['late_share']*100:.1f}%")

    if not any_promoted:
        print("  [i] All evaluated challengers failed to beat the champion on all 4 gates.")
        print("      Champion retained in active production serving.")

    return round_results


def main():
    parser = argparse.ArgumentParser(
        description="AeroShield Autonomous Self-Improvement Flywheel"
    )
    parser.add_argument(
        "--subset",
        type=str,
        default="FD001",
        help="Target C-MAPSS subset (FD001, FD002, FD003, FD004)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run self-improvement across all 4 subsets (FD001-FD004)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=6,
        help="Total challenger configurations to evaluate (default: 6)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=2,
        help="Number of tournament rounds with adaptive narrowing (default: 2)",
    )
    parser.add_argument(
        "--search-space",
        choices=["compact", "full"],
        default="compact",
        help="Search space size: compact (faster) or full (thorough)",
    )
    parser.add_argument(
        "--auto-promote",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically promote candidates passing all 4 gates (default: --auto-promote, disable with --no-auto-promote)",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Allow running on synthetic fleet if raw NASA files are missing",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing NASA C-MAPSS files",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="outputs",
        help="Directory for logs, models, and tournament results",
    )

    args = parser.parse_args()

    subsets = ["FD001", "FD002", "FD003", "FD004"] if args.all else [args.subset.upper()]

    start = time.time()
    for sub in subsets:
        run_self_improvement_for_subset(
            subset=sub,
            data_dir=args.data_dir,
            out_dir=args.out_dir,
            iterations=args.iterations,
            rounds=args.rounds,
            search_type=args.search_space,
            auto_promote=args.auto_promote,
            allow_synthetic=args.allow_synthetic,
        )

    print("\n" + "=" * 78)
    print(f"  SELF-IMPROVEMENT RUN FINISHED IN {time.time()-start:.1f}s")
    print("=" * 78)


if __name__ == "__main__":
    main()
