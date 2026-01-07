"""
Training script for modeling the readmission project.

Core goals:
- Define a clear target: readmission within 30 days (binary classification)
- Build an sklearn Pipeline with:
    - Numeric: impute (median) + scale
    - Categorical: reduce high-cardinality (top-k) + impute + one-hot encode
- Evaluate with Stratified K-Fold CV
- Use metrics that matter for imbalanced classification:
    - ROC-AUC
    - PR-AUC (Average Precision)
    - F1 / Precision / Recall at a chosen threshold
- Select a decision threshold based on an explicit trade-off policy

Artifacts produced (in output directory):
- cv_results.csv
- threshold_analysis.csv
- model.joblib
- threshold.json

Run (from the project folder where data/processed/readmission.duckdb exists):
    python src/train.py

You can optionally specify:
    python src/train.py --db-path data/processed/readmission.duckdb --out-dir artifacts --n-splits 5
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier


DEFAULT_DB_PATH = Path("data/processed/readmission.duckdb")
DEFAULT_TABLE = "encounters"


class TopCategoryReducer(BaseEstimator, TransformerMixin):
    """
    Reduce high-cardinality categorical columns by keeping only the top-k most frequent categories.
    All other categories are mapped to the string "Other".

    This keeps one-hot dimensions manageable and improves stability for small categories.
    """

    def __init__(self, top_k: int = 30, other_label: str = "Other"):
        self.top_k = top_k
        self.other_label = other_label
        self.keep_values_: Dict[str, set] = {}

    def fit(self, X: pd.DataFrame, y=None):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)

        self.keep_values_ = {}
        for col in X.columns:
            vc = X[col].value_counts(dropna=True)
            self.keep_values_[col] = set(vc.head(self.top_k).index.astype(str).tolist())
        return self

    def transform(self, X: pd.DataFrame):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)

        X_out = X.copy()
        for col in X_out.columns:
            keep = self.keep_values_.get(col, set())
            s = X_out[col].astype("string")
            mask = s.notna() & (~s.isin(list(keep)))
            X_out.loc[mask, col] = self.other_label
        return X_out


@dataclass
class CVResult:
    model_name: str
    roc_auc: float
    pr_auc: float
    precision: float
    recall: float
    f1: float
    threshold: float


def load_encounters(db_path: Path, table: str = DEFAULT_TABLE) -> pd.DataFrame:
    """Load the encounters table from DuckDB into a pandas DataFrame."""
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {db_path}")
    con = duckdb.connect(str(db_path))
    try:
        df = con.execute(f"SELECT * FROM {table}").df()
    finally:
        con.close()
    return df


def prepare_xy(df: pd.DataFrame, target_col: str = "readmission_30d") -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare features X and target y; drop obvious leakage and identifiers."""
    if target_col not in df.columns:
        raise ValueError(f"Target column not found: {target_col}")

    y = df[target_col].astype(int)

    drop_cols = [
        "readmitted",
        "readmission_30d",
        "readmission_any",
        "encounter_id",
        "patient_nbr",
    ]
    drop_cols = [c for c in drop_cols if c in df.columns]

    X = df.drop(columns=drop_cols)
    X.columns = [str(c) for c in X.columns]
    return X, y


def split_feature_types(X: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """Infer numeric and categorical columns from dtypes."""
    numeric_cols = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [c for c in X.columns if c not in numeric_cols]
    return numeric_cols, categorical_cols


def build_preprocessor(numeric_cols: List[str], categorical_cols: List[str]) -> ColumnTransformer:
    """Build a ColumnTransformer for numeric + categorical preprocessing."""
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipe = Pipeline(
        steps=[
            ("reduce_cardinality", TopCategoryReducer(top_k=30)),
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_cols),
            ("cat", categorical_pipe, categorical_cols),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )
    return preprocessor


def build_models(random_state: int = 42) -> Dict[str, BaseEstimator]:
    """Define baseline and stronger models."""
    models: Dict[str, BaseEstimator] = {}

    models["logreg"] = LogisticRegression(
        solver="saga",
        penalty="l2",
        max_iter=2000,
        n_jobs=-1,
        class_weight="balanced",
        random_state=random_state,
    )

    models["rf"] = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=2,
        n_jobs=-1,
        class_weight="balanced",
        random_state=random_state,
    )

    return models


def choose_threshold_by_policy(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    recall_target: float = 0.70,
) -> Tuple[float, pd.DataFrame]:
    """
    Choose a probability threshold using an explicit trade-off policy:

    1) Prefer thresholds with recall >= recall_target (e.g., 0.70)
       Among them, choose the one with the best F1.
    2) If none meets the recall target, choose the threshold that maximizes F1.

    Returns:
        best_threshold, threshold_table (precision/recall/f1 for thresholds)
    """
    thresholds = np.linspace(0.05, 0.95, 91)
    rows = []
    for t in thresholds:
        y_pred = (y_proba >= t).astype(int)
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        rows.append({"threshold": float(t), "precision": float(prec), "recall": float(rec), "f1": float(f1)})

    tbl = pd.DataFrame(rows)

    candidates = tbl[tbl["recall"] >= recall_target]
    if len(candidates) > 0:
        best_row = candidates.sort_values(["f1", "precision"], ascending=False).iloc[0]
    else:
        best_row = tbl.sort_values(["f1", "precision"], ascending=False).iloc[0]

    return float(best_row["threshold"]), tbl


def evaluate_model_cv(
    model_name: str,
    estimator: BaseEstimator,
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
    random_state: int = 42,
) -> Tuple[CVResult, np.ndarray, pd.DataFrame]:
    """
    Evaluate a model using Stratified K-Fold CV.

    We compute:
    - out-of-fold predicted probabilities (OOF)
    - ROC-AUC and PR-AUC using OOF probs
    - threshold selection on OOF probs
    - precision/recall/F1 at selected threshold
    """
    numeric_cols, categorical_cols = split_feature_types(X)
    preprocessor = build_preprocessor(numeric_cols, categorical_cols)

    pipe = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", estimator),
        ]
    )

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    oof_proba = cross_val_predict(
        pipe,
        X,
        y,
        cv=cv,
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]

    roc_auc = roc_auc_score(y, oof_proba)
    pr_auc = average_precision_score(y, oof_proba)

    best_t, tbl = choose_threshold_by_policy(y_true=y.to_numpy(), y_proba=oof_proba, recall_target=0.70)

    y_pred = (oof_proba >= best_t).astype(int)
    prec = precision_score(y, y_pred, zero_division=0)
    rec = recall_score(y, y_pred, zero_division=0)
    f1 = f1_score(y, y_pred, zero_division=0)

    res = CVResult(
        model_name=model_name,
        roc_auc=float(roc_auc),
        pr_auc=float(pr_auc),
        precision=float(prec),
        recall=float(rec),
        f1=float(f1),
        threshold=float(best_t),
    )
    return res, oof_proba, tbl


def fit_final_model(estimator: BaseEstimator, X: pd.DataFrame, y: pd.Series, random_state: int = 42) -> Pipeline:
    """Fit the full preprocessing+model pipeline on all data."""
    numeric_cols, categorical_cols = split_feature_types(X)
    preprocessor = build_preprocessor(numeric_cols, categorical_cols)
    pipe = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", estimator),
        ]
    )
    pipe.fit(X, y)
    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 2 training script (CV + threshold selection).")
    p.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to DuckDB file.")
    p.add_argument("--table", type=str, default=DEFAULT_TABLE, help="Table name (default: encounters).")
    p.add_argument("--target", type=str, default="readmission_30d", help="Target column.")
    p.add_argument("--out-dir", type=Path, default=Path("artifacts"), help="Output directory for artifacts.")
    p.add_argument("--n-splits", type=int, default=5, help="Number of CV folds.")
    p.add_argument("--random-state", type=int, default=42, help="Random seed.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = load_encounters(args.db_path, table=args.table)
    X, y = prepare_xy(df, target_col=args.target)

    models = build_models(random_state=args.random_state)

    results: List[CVResult] = []
    threshold_tables: Dict[str, pd.DataFrame] = {}

    for name, est in models.items():
        print(f"Evaluating model: {name}")
        res, oof_proba, tbl = evaluate_model_cv(
            model_name=name,
            estimator=est,
            X=X,
            y=y,
            n_splits=args.n_splits,
            random_state=args.random_state,
        )
        results.append(res)
        threshold_tables[name] = tbl

    df_results = pd.DataFrame([r.__dict__ for r in results]).sort_values(
        by=["pr_auc", "roc_auc"], ascending=False
    )
    df_results.to_csv(args.out_dir / "cv_results.csv", index=False)

    best_name = df_results.iloc[0]["model_name"]
    best_threshold = float(df_results.iloc[0]["threshold"])

    print("\nCV results (sorted by PR-AUC):")
    print(df_results.to_string(index=False))
    print(f"\nSelected final model: {best_name} (threshold={best_threshold:.2f})")

    threshold_tables[best_name].to_csv(args.out_dir / "threshold_analysis.csv", index=False)

    final_estimator = models[best_name]
    final_pipe = fit_final_model(final_estimator, X, y, random_state=args.random_state)
    joblib.dump(final_pipe, args.out_dir / "model.joblib")

    with open(args.out_dir / "threshold.json", "w", encoding="utf-8") as f:
        json.dump({"model_name": best_name, "threshold": best_threshold}, f, indent=2)

    print(f"\nSaved artifacts to: {args.out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
