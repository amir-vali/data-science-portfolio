# Hospital Readmission Risk Prediction (End-to-End)

This project predicts hospital readmission risk (e.g., within 30 days) from patient/hospital data.
It is built as an end-to-end machine learning project: data ingestion + SQL analysis + ML pipeline + evaluation + API + demo app.

## Project structure
- `notebooks/` : EDA + SQL exploration + modeling notebooks
- `src/`       : training/evaluation scripts (reproducible runs)
- `app/`       : FastAPI inference service
- `ui/`        : Streamlit demo UI
- `data/`      : local-only data (ignored by git)
- `artifacts/` : exported models/plots (optional)

## Setup
```bash
python -m venv .venv
# activate venv (see below)
pip install -r requirements.txt
```

## Next steps
- Phase 1: Ingest dataset into DuckDB + SQL EDA notebook
- Phase 2: Build sklearn Pipeline + CV + metrics
- Phase 3: Interpretability + reporting
- Phase 4: MLflow tracking
- Phase 5: FastAPI prediction endpoint
- Phase 6: Streamlit demo
- Phase 7: Docker
