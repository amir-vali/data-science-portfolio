# Data Science Portfolio (Evolving)

This repository is an evolving, recruiter-oriented **data science portfolio**: multiple projects that demonstrate practical skills across machine learning, analytics, and production-style engineering (reproducibility, clean code organization, and deployable demos).

## Projects

- **Health Readmission Risk** — End-to-end ML project (ingestion → modeling → evaluation → MLflow tracking → FastAPI inference → Streamlit demo → Docker).
  - Folder: `projects/health-readmission-risk`
  - Start here: `projects/health-readmission-risk/README.md`

- **Healthcare Outcomes (SQL)** — SQL data modeling + synthetic data generation + analysis queries.
  - Folder: `projects/healthcare-outcomes`
  - Start here: `projects/healthcare-outcomes/README.md`

## What this portfolio emphasizes

- Reproducible pipelines (scripts + clear run commands, not notebook-only)
- Production-style separation (training vs serving vs UI)
- Traceability (experiment tracking and exported artifacts)
- Practical delivery (API contract, containerized run, minimal automated tests)

## Repository layout

```text
projects/
  health-readmission-risk/
  healthcare-outcomes/
```

## How to review quickly

1. Open the README of the project you care about.
2. Skim **Architecture** and **How to run**.
3. Optionally run the Docker demo to verify the end-to-end flow.

## About the author

Amir Hosein (GitHub: `amir-vali`)
