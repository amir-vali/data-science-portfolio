from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import PredictRequest, PredictResponse
from app.model_loader import load_assets, make_input_frame, ModelAssets

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


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    """Predict readmission probability for a single patient encounter."""
    if ASSETS is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

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

    try:
        proba = float(ASSETS.model.predict_proba(X)[:, 1][0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {e}")

    label = 1 if proba >= ASSETS.threshold else 0

    return PredictResponse(
        probability=proba,
        label=label,
        threshold=float(ASSETS.threshold),
        model_name=str(ASSETS.model_name),
    )
