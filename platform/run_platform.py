"""Tata Elxsi Predictive Fleet Maintenance Platform (Case Study 1)
Interactive Web Cockpit Launcher
"""

import sys
import os
import uvicorn

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "platform"))

if __name__ == "__main__":
    print("\n" + "="*75)
    print("  AUTONOMOUS PREDICTIVE FLEET MAINTENANCE PLATFORM")
    print("  TATA ELXSI CASE STUDY 1: SELF-HEALING MACHINES")
    print("  AeroShield Engine • NASA C-MAPSS FD001-FD004 Benchmark")
    print("="*75)
    print("  * Interactive Web Cockpit: http://127.0.0.1:8050/dashboard")
    print("  * REST API Documentation:  http://127.0.0.1:8050/docs")
    print("="*75 + "\n")

    try:
        from platform.backend.main import app
    except ImportError:
        from backend.main import app

    uvicorn.run(app, host="127.0.0.1", port=8050, log_level="info")
