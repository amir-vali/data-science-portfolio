from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """Incoming payload for prediction."""
    features: Dict[str, Any] = Field(..., description="Feature dictionary (column_name -> value).")


class PredictResponse(BaseModel):
    """Prediction response."""
    probability: float
    label: int
    threshold: float
    model_name: str
