#!/usr/bin/env python3
"""AeroShield: Standalone cryptographic audit log verification script.
Validates monotonic SHA-256 / HMAC hash chain across work order event blocks.
"""

import sys
import os
import sqlite3
import hmac
import hashlib
import argparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISHED_DEMO_HMAC_KEY = "aeroshield-v3-secret-key"
_configured_hmac = os.environ.get("AEROSHIELD_HMAC_KEY", "").strip()
HMAC_SECRET = (
    _configured_hmac.encode()
    if _configured_hmac and _configured_hmac != PUBLISHED_DEMO_HMAC_KEY
    else PUBLISHED_DEMO_HMAC_KEY.encode()
)


def compute_audit_hash(prev_h: str, ts: str, order_id: str, event: str, details_str: str) -> str:
    payload = f"{prev_h}|{ts}|{order_id}|{event}|{details_str}".encode()
    return hmac.new(HMAC_SECRET, payload, hashlib.sha256).hexdigest()


def verify_audit(subset: str = "FD001") -> bool:
    db_path = os.path.join(REPO_ROOT, "outputs", subset, "work_orders.db")
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}. Run 'python run_all.py --subset {subset}' first.")
        return False

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT entry_id, prev_hash, current_hash, timestamp, order_id, event_type, details FROM audit_log ORDER BY entry_id ASC")
        rows = cur.fetchall()

    if not rows:
        print(f"[WARN] Audit log is empty for {subset}.")
        return True

    exp = "GENESIS_" + "0" * 32
    for r in rows:
        eid = r["entry_id"]
        prev_h = r["prev_hash"]
        cur_h = r["current_hash"]
        ts = r["timestamp"]
        oid = r["order_id"]
        ev = r["event_type"]
        det = r["details"]

        if prev_h != exp:
            print(f"[FAIL] Chain broken at entry {eid}: expected prev {exp}, got {prev_h}")
            return False

        expected_h = compute_audit_hash(prev_h, ts, oid, ev, det)
        if expected_h != cur_h:
            print(f"[FAIL] Tampered entry {eid}: current_hash mismatch.")
            return False

        exp = cur_h

    print(f"[PASS] Successfully verified {len(rows)} cryptographically linked audit blocks for {subset}.")
    print(f"       Head block seal: {exp[:16]}... Monotonic continuity 100% intact.")
    return True


def verify_all_subsets() -> bool:
    subsets = ["FD001", "FD002", "FD003", "FD004"]
    print(f"[*] Verifying cryptographic audit chains across all {len(subsets)} subsets...")
    all_ok = True
    for s in subsets:
        ok = verify_audit(s)
        if not ok:
            all_ok = False
    if all_ok:
        print("[SUCCESS] All C-MAPSS audit chains (FD001-FD004) verified successfully.")
    else:
        print("[FAILURE] One or more audit chains failed cryptographic verification.")
    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify AeroShield cryptographic audit hash chain.")
    parser.add_argument("positional_subset", nargs="?", default=None, help="Subset to verify (e.g. FD001)")
    parser.add_argument("--subset", "-s", default="FD001", help="Subset to verify (default: FD001)")
    parser.add_argument("--all", "-a", action="store_true", help="Verify all subsets (FD001-FD004)")
    args = parser.parse_args()

    if args.all:
        ok = verify_all_subsets()
    else:
        target_subset = args.positional_subset or args.subset
        ok = verify_audit(target_subset)
    sys.exit(0 if ok else 1)
