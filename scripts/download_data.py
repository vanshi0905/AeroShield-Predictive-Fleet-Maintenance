#!/usr/bin/env python3
"""AeroShield: NASA C-MAPSS dataset verification and ingestion helper.
Fulfills Makefile 'data' target without missing-file errors.
"""

import sys
import os
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
PARENT_DIR = os.path.dirname(REPO_ROOT)
PARENT_CMAPSS = os.path.join(PARENT_DIR, "CMAPSSData")

FILES = [
    "train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt",
    "train_FD002.txt", "test_FD002.txt", "RUL_FD002.txt",
    "train_FD003.txt", "test_FD003.txt", "RUL_FD003.txt",
    "train_FD004.txt", "test_FD004.txt", "RUL_FD004.txt",
]


def check_and_prepare_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    missing = [f for f in FILES if not os.path.exists(os.path.join(DATA_DIR, f))]

    if not missing:
        print(f"[OK] All 12 NASA C-MAPSS files (FD001-FD004) present in {DATA_DIR}.")
        return True

    print(f"Missing {len(missing)} files in {DATA_DIR}. Checking local source directories...")

    # Check parent CMAPSSData folder
    copied = 0
    if os.path.exists(PARENT_CMAPSS):
        for f in missing:
            src = os.path.join(PARENT_CMAPSS, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(DATA_DIR, f))
                copied += 1

    remaining = [f for f in FILES if not os.path.exists(os.path.join(DATA_DIR, f))]
    if not remaining:
        print(f"[OK] Successfully ingested {copied} missing C-MAPSS files into {DATA_DIR}.")
        return True
    else:
        print(f"[WARN] {len(remaining)} files still missing: {remaining[:3]}...")
        return False


if __name__ == "__main__":
    ok = check_and_prepare_data()
    sys.exit(0 if ok else 1)
