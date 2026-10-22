SUBSET ?= FD001

all:            ## one command, no manual steps (one subset)
	python run_all.py --subset $(SUBSET) --reset

all-subsets:    ## FD001..FD004
	python run_all.py --all --reset

retrain-demo:   ## drift -> censoring-aware retrain -> gated promotion
	python retrain_demo.py --scenario adaptive

test:
	python -m pytest -q

verify-audit:   ## recompute SHA-256 chain; fails if any row was altered
	python scripts/verify_audit.py $(SUBSET)

dashboard:      ## launch production FastAPI avionics dashboard
	python -m uvicorn platform.backend.main:app --host 0.0.0.0 --port 8000

check-docs:     ## fail if README tables differ from outputs/*/metrics.json
	python scripts/render_readme_tables.py --check

mlflow-ui:
	mlflow ui --backend-store-uri sqlite:///outputs/mlflow.db

data:           ## verify and ingest NASA C-MAPSS files into data/
	python scripts/download_data.py
