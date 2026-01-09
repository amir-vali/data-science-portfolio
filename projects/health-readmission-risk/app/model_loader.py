from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd


@dataclass(frozen=True)
class ModelAssets:
    model: Any
    threshold: float
    model_name: str
    feature_columns: List[str]


def load_assets(artifacts_dir: Path) -> ModelAssets:
    """Load model + threshold + feature schema from the artifacts directory."""
    model_path = artifacts_dir / "model.joblib"
    threshold_path = artifacts_dir / "threshold.json"
    schema_path = artifacts_dir / "feature_columns.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Missing model artifact: {model_path}")
    if not threshold_path.exists():
        raise FileNotFoundError(f"Missing threshold artifact: {threshold_path}")
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Missing schema artifact: {schema_path}. "
            f"Create it in Phase 4 by saving X.columns to feature_columns.json."
        )

    model = joblib.load(model_path)

    threshold_cfg = json.loads(threshold_path.read_text(encoding="utf-8"))
    threshold = float(threshold_cfg["threshold"])
    model_name = str(threshold_cfg.get("model_name", "unknown"))

    schema_cfg = json.loads(schema_path.read_text(encoding="utf-8"))
    cols = list(schema_cfg["columns"])

    return ModelAssets(
        model=model,
        threshold=threshold,
        model_name=model_name,
        feature_columns=cols,
    )


def make_input_frame(feature_columns: List[str], provided_features: Dict[str, Any]) -> pd.DataFrame:
    """
    Create a 1-row DataFrame with the exact training columns.
    Missing columns are filled with None; extra keys are rejected by request validation.
    """
    row = {c: None for c in feature_columns}
    for k, v in provided_features.items():
        row[k] = v
    return pd.DataFrame([row], columns=feature_columns)
