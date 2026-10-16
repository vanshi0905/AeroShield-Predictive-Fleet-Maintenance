SUBSET ?= FD001
all:            ## one command, no manual steps (one subset)
	python run_all.py --subset $(SUBSET) --reset
all-subsets:    ## FD001..FD004
	python run_all.py --all --reset
retrain-demo:   ## drift -> censoring-aware retrain -> gated promotion (gentle + strong shift)
	python retrain_demo.py
test:
	python -m pytest -q
verify-audit:   ## recompute SHA-256 chain; fails if any row was altered
	python scripts/verify_audit.py $(SUBSET)
dashboard:
	streamlit run app/dashboard.py
mlflow-ui:
	mlflow ui --backend-store-uri sqlite:///outputs/mlflow.db
data:           ## re-download the public C-MAPSS files (only needed if data/ is empty)
	python scripts/download_data.py
