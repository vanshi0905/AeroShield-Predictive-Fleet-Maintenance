# Repository Operating Guidelines & Rules

All AI agents, contributors, and automated tooling operating in this repository must strictly adhere to the following rules:

1. **Deterministic Metrics & No Manual Output Edits**:
   - Never edit files in `outputs/` by hand.
   - All benchmark tables and metric claims in documentation and presentations must be generated directly from `outputs/*/metrics.json` via `python scripts/render_readme_tables.py`.

2. **Codebase-Grounded Technical Claims**:
   - Never claim an algorithm, library, framework, or architecture that is not implemented in the active pipeline (`shield/src/`) or specified in `requirements.txt` / `requirements-dev.txt`.
   - The production RUL architecture is **HistGradientBoosting Quantile Regressors** (p10, p50, p90) with an independent **Random Forest consensus estimator**, cross-conformal prediction interval calibration, step-bounded exponential smoothing, and asymmetric late-shift calibration.

3. **Mandatory Pre-Commit Verification**:
   - Before committing any changes, run:
     ```bash
     python -m pytest -q
     python scripts/render_readme_tables.py --check
     python scripts/verify_audit.py FD001
     ```
   - Commit only when all tests, doc-checks, and audit chain verifications pass with 0 errors.

4. **Factual Reporting**:
   - Report raw execution commands and their exact outputs rather than subjective assertions.
   - Distinctly separate empirical measurements (e.g. capped RMSE, NASA asymmetric loss, coverage) from aspirational business objectives.
