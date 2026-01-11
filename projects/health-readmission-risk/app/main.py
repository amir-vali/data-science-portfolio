from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import PredictRequest, PredictResponse, MetadataResponse
from app.model_loader import load_assets, make_input_frame, ModelAssets

import time

APP_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = APP_ROOT / "artifacts"

app = FastAPI(title="Readmission Risk API", version="1.0.0")

ASSETS: ModelAssets | None = None


@app.on_event("startup")
def startup_event() -> None:
    """Load artifacts once when the API starts."""
    global ASSETS
    ASSETS = load_assets(ARTIFACTS_DIR)


@app.get("/health")
def health() -> Dict[str, Any]:
    """Sanity check endpoint."""
    ok = ASSETS is not None
    return {
        "status": "ok" if ok else "not_ready",
        "model_loaded": ok,
        "model_name": ASSETS.model_name if ok else None,
    }

@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    """Return basic model metadata for transparency and debugging."""
    if ASSETS is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    return MetadataResponse(
        model_name=str(ASSETS.model_name),
        threshold=float(ASSETS.threshold),
        n_features=len(ASSETS.feature_columns),
        feature_columns=list(ASSETS.feature_columns),
    )

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    """Predict readmission probability for a single patient encounter."""
    if ASSETS is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    start = time.perf_counter()

    provided = req.features

    # Reject unknown feature keys (professional-grade input hygiene)
    extra_keys = sorted(set(provided.keys()) - set(ASSETS.feature_columns))
    if extra_keys:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Unknown feature keys were provided.",
                "extra_keys": extra_keys,
            },
        )

    X = make_input_frame(ASSETS.feature_columns, provided)

    # Count missing values in the 1-row input (None/NaN)
    missing_count = int(X.isna().sum(axis=1).iloc[0])
    provided_count = len(provided)
    total_features = len(ASSETS.feature_columns)

    try:
        proba = float(ASSETS.model.predict_proba(X)[:, 1][0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {e}")

    label = 1 if proba >= ASSETS.threshold else 0

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Simple structured log (stdout)
    print(
        f"[predict] model={ASSETS.model_name} "
        f"proba={proba:.4f} label={label} "
        f"elapsed_ms={elapsed_ms:.2f} "
        f"provided={provided_count}/{total_features} missing={missing_count}"
    )
    
    return PredictResponse(
        probability=proba,
        label=label,
        threshold=float(ASSETS.threshold),
        model_name=str(ASSETS.model_name),
    )
