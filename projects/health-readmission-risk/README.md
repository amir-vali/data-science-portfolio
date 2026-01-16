# Hospital Readmission Risk Prediction (End-to-End)

Predict hospital readmission risk (e.g., within 30 days) using patient/encounter features.

This project is intentionally designed as an **end-to-end, recruiter-friendly ML deliverable**:

- Data ingestion into DuckDB for SQL-style exploration
- A scikit-learn training pipeline with cross-validation and threshold selection
- Evaluation artifacts (metrics + plots)
- Optional experiment tracking with MLflow
- A FastAPI inference service (typed request/response)
- A Streamlit UI for interactive testing
- Docker/Docker Compose for a one-command demo

## Dataset

The ingestion script supports the public UCI dataset “Diabetes 130-US hospitals (1999–2008)”.
Raw data is not committed to this repository.

## Architecture

```text
             +-------------------+
             |  data_ingest.py    |
             |  (DuckDB build)    |
             +---------+---------+
                       |
                       v
+----------------------+---------------------+
|        src/train.py (sklearn Pipeline)     |
|  CV metrics + threshold + exported model   |
+----------------------+---------------------+
                       |
              artifacts/ (exported)
                       |
        +--------------+--------------+
        |                             |
        v                             v
  FastAPI API (/predict)        Streamlit UI (demo)
```

## Project structure

- `src/data_ingest.py` — download/clean dataset and build DuckDB tables
- `src/train.py` — training + CV + threshold policy + artifact export (+ optional MLflow)
- `app/` — FastAPI service (loads exported artifacts)
- `ui/` — Streamlit demo (API mode; optional local-model mode)
- `notebooks/` — EDA / modeling / evaluation notebooks
- `artifacts/` — exported schema/threshold/model and evaluation outputs
- `docker-compose.yml` / `Dockerfile.*` — containerized demo

## Run locally

### 0) Create a virtual environment

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
```

### 1) Install dependencies

For development (EDA + training + MLflow + tests):

```bash
pip install -r requirements-dev.txt
pip install -r requirements-api.txt
pip install -r requirements-ui.txt
pip install -e .
```

`pip install -e .` is important so that `readmission_risk.custom_transformers` is importable when
loading the exported `model.joblib`.

### 2) Ingest data (build DuckDB)

```bash
python src/data_ingest.py --download
```

This creates a DuckDB database (default): `data/processed/readmission.duckdb`.

### 3) Train and export artifacts

```bash
python src/train.py --db-path data/processed/readmission.duckdb --out-dir artifacts
```

This step exports evaluation artifacts and (optionally) a trained model.

**Versioned artifacts (committed to this repository):**
- `artifacts/feature_columns.json`
- `artifacts/threshold.json`
- `artifacts/cv_results.csv`
- `artifacts/threshold_analysis.csv`
- `artifacts/reports/<model_name>/...` (plots + CSVs)

**Non-versioned artifact (not committed due to size):**
- `artifacts/model.joblib`

**Model artifact policy**  
The trained model (`model.joblib`) is intentionally **not versioned in Git** due to its large size (~670 MB).
This project follows common industry practice: source code and configurations are version-controlled, while large
binary artifacts are reproducible rather than stored in Git history.

To reproduce the model locally:

```bash
python src/data_ingest.py --download
python src/train.py --db-path data/processed/readmission.duckdb --out-dir artifacts
```

### 4) Run the API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Predict (example):

```bash
curl -X POST http://127.0.0.1:8000/predict   -H "Content-Type: application/json"   -d '{"features": {"time_in_hospital": 3, "num_lab_procedures": 42, "num_medications": 10}}'
```

### 5) Run the Streamlit UI

```bash
streamlit run ui/streamlit_app.py
```

The UI supports:
- **API mode** (recommended): UI → FastAPI → model
- **Local mode** (optional): UI loads `model.joblib` directly (useful for offline demos)

## MLflow (optional)

### Option A: Start MLflow via Docker

```bash
docker compose up -d mlflow
```

Then run training with tracking:

```bash
python src/train.py --out-dir artifacts --mlflow --tracking-uri http://127.0.0.1:5000
```

### Option B: Local MLflow UI

```bash
mlflow ui
```

## Docker demo

From `projects/health-readmission-risk/`:

```bash
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- UI: `http://localhost:8501`
- MLflow (optional): `http://localhost:5000`

## Tests

```bash
pytest -q
```

## Notes and limitations

- This is a portfolio project, not clinical decision support software.
- Any claims about generalization, fairness, or safety require domain validation.
- The dataset is public; raw data is not committed to this repository.
