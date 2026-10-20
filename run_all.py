"""AeroShield: One-command end-to-end pipeline execution from raw files to work orders.
Fulfills Requirement R12 and Review Fault F6.
Usage:
    python run_all.py --subset FD001 --reset
    python run_all.py --all --reset
"""

import argparse
import os
import sys
import time

from shield.src.pipeline import ShieldPipeline as Pipeline


def main():
    parser = argparse.ArgumentParser(
        description="AeroShield End-to-End Predictive Maintenance Pipeline (NASA C-MAPSS)"
    )
    parser.add_argument(
        "--subset",
        type=str,
        default="FD001",
        help="C-MAPSS fleet partition to process (FD001, FD002, FD003, FD004)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all four C-MAPSS fleet partitions (FD001-FD004) sequentially",
    )
    parser.add_argument(
        "--data_dir", "--data-dir",
        dest="data_dir",
        type=str,
        default="data",
        help="Directory containing NASA C-MAPSS raw text files",
    )
    parser.add_argument(
        "--out_dir", "--out-dir",
        dest="out_dir",
        type=str,
        default="outputs",
        help="Output directory for predictions, models, databases, and logs",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset/overwrite existing output artifacts for the partition",
    )
    parser.add_argument(
        "--tune_cap", "--tune-cap",
        dest="tune_cap",
        action="store_true",
        default=False,
        help="Run cross-validation grid search for RUL clipping cap (default: False)",
    )
    parser.add_argument(
        "--inject",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Inject simulated sensor faults to exercise human-exception queue (default: --inject, disable with --no-inject)",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Allow running on synthetic fleet if raw NASA files are missing",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    subsets = ["FD001", "FD002", "FD003", "FD004"] if args.all else [args.subset.upper()]

    print("=" * 80)
    print("  AEROSHIELD: AUTONOMOUS PREDICTIVE FLEET MAINTENANCE PIPELINE")
    print(f"  Target Partitions: {', '.join(subsets)}")
    print(f"  Data Directory:    {os.path.abspath(args.data_dir)}")
    print(f"  Outputs Directory: {os.path.abspath(args.out_dir)}")
    print("=" * 80)

    start_total = time.time()
    results = {}

    for sub in subsets:
        print(f"\n>>> Running End-to-End Pipeline for {sub} ...")
        t0 = time.time()
        pipeline = Pipeline(
            subset=sub,
            data_dir=args.data_dir,
            out_dir=args.out_dir,
            tune_cap=args.tune_cap,
            inject=args.inject,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )
        metrics = pipeline.run()
        elapsed = time.time() - t0
        results[sub] = metrics
        print(f">>> {sub} finished in {elapsed:.1f}s. Data source: {metrics.get('data_source', 'unknown')}")

    total_elapsed = time.time() - start_total
    print("\n" + "=" * 80)
    print(f"  ALL PARTITIONS COMPLETE (Total Elapsed: {total_elapsed:.1f}s)")
    print("=" * 80)
    for sub, m in results.items():
        lw = m.get("test_last_window", {})
        print(
            f"  {sub:6s} | Data: {m.get('data_source'):9s} | "
            f"Capped RMSE: {lw.get('rmse_capped_truth', 0):.2f} | "
            f"Uncapped RMSE: {lw.get('rmse_uncapped_truth', 0):.2f} | "
            f"NASA Score: {lw.get('nasa_uncapped_truth', 0):.1f} | "
            f"Coverage: {lw.get('coverage', 0)*100:.1f}% | "
            f"Late Share: {lw.get('late_share', 0)*100:.1f}% | "
            f"Audit: {m.get('audit_msg', 'OK')}"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()
