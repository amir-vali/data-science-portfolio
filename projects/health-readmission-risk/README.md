# Hospital Readmission Risk Prediction (End-to-End)

Predict hospital readmission risk (e.g., within 30 days) from patient/hospital data using a reproducible, portfolio-ready ML workflow.

## 📊 Project Overview

This project is structured as an end-to-end machine learning system:

- **Data ingestion** into a local **DuckDB** database
- **SQL + EDA** notebooks for exploration and sanity checks
- **scikit-learn Pipeline** training with cross-validation and threshold selection
- **Reporting artifacts** (plots + CSVs) for interpretability
- **FastAPI** inference service
- **Streamlit** demo UI
- **MLflow** experiment tracking (optional)
- **Docker Compose** for a portable demo environment

## 💾 Dataset

The ingestion script supports the public UCI dataset “Diabetes 130-US hospitals (1999–2008)”. Raw data is not committed to this repository.

## 🏗️ Model & System Architecture

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

## 📁 Repository Structure

- `notebooks/` : EDA + SQL exploration + modeling notebooks
- `src/`       : reproducible training / evaluation pipeline
    - `data_ingest.py` — download, clean dataset, build DuckDB tables
    - `train.py`       — training + CV + threshold policy + artifact export
- `app/`       : FastAPI inference service (loads exported artifacts)
- `ui/`        : Streamlit demo UI (API mode; optional local-model mode)
- `data/`      : local-only data (ignored by git)
- `artifacts/` : exported artifacts (threshold/schema are versioned; model is reproduced locally)
- `docker-compose.yml` — containerized demo (API + UI)

## 🚀 Quick Start (Local)

### Prerequisites

- Python 3.10+ (recommended)

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 2) Install dependencies

#### Option A — Quick start (recommended for local development)
Install everything (API + UI + notebooks + dev tools) in one go:

```bash
pip install -r requirements.txt
pip install -e .
```

#### Option B — Minimal installs (recommended for production/Docker)
Use the split requirement files to keep environments lightweight:

```bash
pip install -r requirements-dev.txt
pip install -r requirements-api.txt
pip install -r requirements-ui.txt
pip install -e .
```

#### Why multiple requirements files?

- `requirements.txt`: convenience (everything installed) for local exploration and quick setup. 
- `requirements-api.txt`: minimal runtime for the API container. 
- `requirements-ui.txt`: minimal runtime for Streamlit container. 
- `requirements-dev.txt`: extra tooling used during development (notebooks/tests/EDA/tracking). 

`pip install -e .` is important so that `readmission_risk.custom_transformers` is importable when loading the exported `model.joblib`.

### 3) Ingest data into DuckDB

```bash
python src/data_ingest.py --download
```

This produces DuckDB database (locally):

- `data/processed/readmission.duckdb`

### 4) Train and export artifacts

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

#### Model artifact policy

The trained model (`model.joblib`) is intentionally **not versioned in Git** due to its large size (~670 MB).
This project follows common industry practice: source code and configurations are version-controlled, while large
binary artifacts are reproducible rather than stored in Git history.

## 🧪 Run the Services (Local)

### FastAPI

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

### Streamlit

```bash
streamlit run ui/streamlit_app.py
```

The UI supports:
- **API mode** (recommended): UI → FastAPI → model
- **Local mode** (optional): UI loads `model.joblib` directly (useful for offline demos)

In the sidebar, set **FastAPI base URL** (default is `http://127.0.0.1:8000`).

## 🐳 Docker (Portable Demo)

Build and run:

```bash
docker compose up --build
```

Services:

- FastAPI: `http://localhost:8000`
- Streamlit UI: `http://localhost:8501`
- MLflow (optional): `http://localhost:5000`

📌 Note: the API requires `artifacts/model.joblib`. If you have not trained the model yet, run the training step first (see **Train and export artifacts**).

## 📈 MLflow (Optional)

Training can log runs to MLflow for experiment tracking:

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

```bash
python src/train.py --db-path data/processed/readmission.duckdb --out-dir artifacts --mlflow
```

Note: If `--tracking-uri` is not provided, MLflow defaults to the local file-based backend.

## 🧾 Notes

- This is a portfolio / research project, **not** clinical decision support software.
- Any claims about generalization, fairness, or safety require domain-specific validation.
- The dataset is public; **raw data is not committed** to this repository.
- `data/` is ignored by git and intended for local use only.
- Only small artifacts required for the UI (e.g., schema, thresholds) are versioned.
- Large model binaries are **reproduced locally**, not stored in the repository.

## 👤 Author

Amir Hosein