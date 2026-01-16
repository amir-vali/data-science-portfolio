from __future__ import annotations

import os
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import requests

import importlib


# Feature flags (controlled by env vars)
# - In Docker: set ENABLE_LOCAL_MODEL=0 to hide local mode and avoid joblib dependency
# - In local dev: default is enabled
ENABLE_LOCAL_MODEL = os.getenv("ENABLE_LOCAL_MODEL", "1").strip().lower() in {"1", "true", "yes", "y"}

APP_ROOT = Path(__file__).resolve().parent.parent
ART_DIR = APP_ROOT / "artifacts"
FASTAPI_BASE_URL_DEFAULT = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")


@dataclass(frozen=True)
class RuntimeConfig:
    """Non-model artifacts needed for both API mode and local mode."""
    model_name: str
    threshold: float
    feature_columns: List[str]
    perm_importance: Optional[pd.DataFrame]


def ensure_unpickle_deps() -> None:
    """Ensure custom modules required by joblib artifacts are importable."""
    try:
        importlib.import_module("readmission_risk.custom_transformers")
    except Exception as e:
        raise RuntimeError(
            "Missing package dependency for unpickling. "
            "Run: pip install -e . (from project root)"
        ) from e


@st.cache_data(show_spinner=False)
def load_runtime_config(art_dir: Path) -> RuntimeConfig:
    """Load threshold + schema + optional permutation importance (no model load)."""
    thr_path = art_dir / "threshold.json"
    cols_path = art_dir / "feature_columns.json"

    if not thr_path.exists():
        raise FileNotFoundError(f"Missing: {thr_path}")
    if not cols_path.exists():
        raise FileNotFoundError(f"Missing: {cols_path}")

    thr_cfg = json.loads(thr_path.read_text(encoding="utf-8"))
    threshold = float(thr_cfg["threshold"])
    model_name = str(thr_cfg.get("model_name", "unknown"))

    cols_cfg = json.loads(cols_path.read_text(encoding="utf-8"))
    feature_columns = list(cols_cfg["columns"])

    # Optional global explanation artifact (produced in Phase 4)
    perm_csv = art_dir / "reports" / model_name / "permutation_importance.csv"
    perm_df = None
    if perm_csv.exists():
        perm_df = pd.read_csv(perm_csv)

    return RuntimeConfig(
        model_name=model_name,
        threshold=threshold,
        feature_columns=feature_columns,
        perm_importance=perm_df,
    )


def get_prediction_mode() -> str:
    """Return the selected prediction mode, respecting Docker feature flags."""
    st.sidebar.header("Settings")

    st.sidebar.text_input("FastAPI base URL", value=FASTAPI_BASE_URL_DEFAULT, key="fastapi_base_url")

    if ENABLE_LOCAL_MODEL:
        mode = st.sidebar.radio(
            "Prediction mode",
            options=["Call FastAPI (recommended)", "Local model (no API)"],
            index=0,
        )
        return mode

    # Docker / API-only mode: do not show Local option at all
    st.sidebar.radio(
        "Prediction mode",
        options=["Call FastAPI (recommended)"],
        index=0,
        disabled=True,
    )
    st.sidebar.caption("Local model is disabled in this Docker build.")
    return "Call FastAPI (recommended)"


@st.cache_resource(show_spinner=False)
def load_local_model(model_path: Path) -> Any:
    """Load the joblib model only when needed (lazy-load)."""
    import joblib  # lazy import to avoid dependency unless local mode is used
    if not model_path.exists():
        raise FileNotFoundError(f"Missing: {model_path}")
    ensure_unpickle_deps()
    model = joblib.load(model_path)
    return model


def make_frame(feature_columns: List[str], provided: Dict[str, Any]) -> pd.DataFrame:
    """Create a 1-row DataFrame with the exact training columns."""
    row = {c: None for c in feature_columns}
    for k, v in provided.items():
        row[k] = v
    return pd.DataFrame([row], columns=feature_columns)


def risk_level(prob: float, threshold: float) -> str:
    """Map probability to a simple 3-level risk label for a cleaner demo."""
    if prob < threshold:
        return "Low"
    if prob < min(0.95, threshold + 0.15):
        return "Medium"
    return "High"


def validate_feature_keys(feature_columns: List[str], provided: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (ok, extra_keys)."""
    extra_keys = sorted(set(provided.keys()) - set(feature_columns))
    return (len(extra_keys) == 0, extra_keys)


def predict_via_api(api_url: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """Call FastAPI /predict endpoint."""
    r = requests.post(f"{api_url}/predict", json={"features": features}, timeout=15)
    r.raise_for_status()
    return r.json()


def try_api_health(api_url: str) -> Dict[str, Any]:
    """Call FastAPI /health endpoint."""
    r = requests.get(f"{api_url}/health", timeout=10)
    r.raise_for_status()
    return r.json()


def predict_locally(model: Any, feature_columns: List[str], threshold: float, features: Dict[str, Any]) -> Dict[str, Any]:
    """Run local prediction using model.joblib without API."""
    X = make_frame(feature_columns, features)
    proba = float(model.predict_proba(X)[:, 1][0])
    label = 1 if proba >= threshold else 0
    return {"probability": proba, "label": label, "threshold": threshold}


def _normalize_api_url(url: str) -> str:

    url = (url or "").strip()

    return url[:-1] if url.endswith("/") else url


def main() -> None:
    st.set_page_config(page_title="Readmission Risk Demo", layout="wide")
    st.title("Hospital Readmission Risk – Demo")
    st.caption("Streamlit UI (Phase 6): Fast interactive demo + optional FastAPI integration.")

    # Load non-model artifacts (fast + safe).
    try:
        cfg = load_runtime_config(ART_DIR)
    except Exception as e:
        st.error(f"Failed to load runtime artifacts from {ART_DIR}: {e}")
        st.stop()

    # Sidebar configuration
    st.sidebar.header("Settings")
    mode = get_prediction_mode()
    api_url = _normalize_api_url(st.session_state.get("fastapi_base_url", FASTAPI_BASE_URL_DEFAULT))

    st.sidebar.markdown("---")
    st.sidebar.write("**Model**:", cfg.model_name)
    st.sidebar.write("**Threshold**:", cfg.threshold)
    st.sidebar.write("**#Features (schema)**:", len(cfg.feature_columns))

    # Optional API sanity check (only relevant in API mode)
    if mode.startswith("Call FastAPI"):
        if st.sidebar.button("Check API /health"):
            try:
                health = try_api_health(api_url)
                st.sidebar.success(f"API OK: {health}")
            except Exception as e:
                st.sidebar.error(f"API health check failed: {e}")

    # Lazy-load model only if local mode is selected
    local_model: Optional[Any] = None
    if mode.startswith("Local model"):
        with st.sidebar.status("Loading local model...", expanded=False):
            try:
                local_model = load_local_model(ART_DIR / "model.joblib")
                st.sidebar.success("Local model loaded.")
            except Exception as e:
                st.sidebar.error(
                    "Failed to load local model. "
                    "This is usually an import-path issue for custom modules during joblib unpickling.\n\n"
                    f"Error: {e}"
                )
                st.stop()

    tab1, tab2, tab3 = st.tabs(["Single Prediction", "Batch CSV", "Model Insights"])

    # -------------------------------------------------------------------
    # Tab 1: Single prediction
    # -------------------------------------------------------------------
    with tab1:
        st.subheader("Single prediction")

        # Use a small, human-friendly subset for the form
        suggested = [
            "time_in_hospital",
            "num_lab_procedures",
            "num_procedures",
            "num_medications",
            "number_inpatient",
            "number_emergency",
            "number_outpatient",
        ]
        suggested = [c for c in suggested if c in cfg.feature_columns]

        st.write(
            "Provide a few intuitive inputs. Missing features will be handled by the trained pipeline "
            "(imputers + encoders)."
        )

        with st.form("predict_form"):
            features: Dict[str, Any] = {}

            cols = st.columns(3)
            for i, colname in enumerate(suggested):
                with cols[i % 3]:
                    features[colname] = st.number_input(colname, value=0.0, step=1.0)

            raw_json = st.text_area(
                "Optional: Additional features as JSON (advanced)",
                value="{}",
                help='Example: {"race": "Caucasian", "gender": "Male", "age": "[70-80)"}',
            )

            submitted = st.form_submit_button("Predict")

        if submitted:
            try:
                extra = json.loads(raw_json) if raw_json.strip() else {}
                if not isinstance(extra, dict):
                    raise ValueError("Advanced JSON must be an object/dict.")
                features.update(extra)

                ok, extra_keys = validate_feature_keys(cfg.feature_columns, features)
                if not ok:
                    st.error(f"Unknown feature keys: {extra_keys}")
                    st.stop()

                if mode.startswith("Call FastAPI"):
                    out = predict_via_api(api_url, features)
                else:
                    assert local_model is not None
                    out = predict_locally(local_model, cfg.feature_columns, cfg.threshold, features)

                proba = float(out["probability"])
                lbl = int(out["label"])
                thr = float(out["threshold"])
                level = risk_level(proba, thr)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Probability", f"{proba:.3f}")
                c2.metric("Label", str(lbl))
                c3.metric("Threshold", f"{thr:.2f}")
                c4.metric("Risk level", level)

                st.progress(min(max(proba, 0.0), 1.0))
                st.success("Prediction completed.")

            except requests.RequestException as e:
                st.error(f"API request failed: {e}")
            except Exception as e:
                st.error(f"Prediction failed: {e}")

    # -------------------------------------------------------------------
    # Tab 2: Batch prediction via CSV
    # -------------------------------------------------------------------
    with tab2:
        st.subheader("Batch prediction (CSV upload)")
        st.write("Upload a CSV with a subset of schema columns. Unknown columns will be ignored.")

        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded is not None:
            df_in = pd.read_csv(uploaded)
            st.write("Preview:", df_in.head())

            unknown_cols = sorted(set(df_in.columns) - set(cfg.feature_columns))
            if unknown_cols:
                st.warning(f"Unknown columns (ignored): {unknown_cols}")

            # Keep only known schema columns
            df_known = df_in[[c for c in df_in.columns if c in cfg.feature_columns]].copy()

            # Expand to full schema (missing columns become None)
            full = pd.DataFrame({c: (df_known[c] if c in df_known.columns else None) for c in cfg.feature_columns})

            if st.button("Run batch prediction"):
                try:
                    if mode.startswith("Call FastAPI"):
                        probs = []
                        labels = []
                        for _, row in full.iterrows():
                            # Send only non-null fields to the API (cleaner payload)
                            payload = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
                            out = predict_via_api(api_url, payload)
                            probs.append(float(out["probability"]))
                            labels.append(int(out["label"]))

                        out_df = df_in.copy()
                        out_df["probability"] = probs
                        out_df["label"] = labels

                    else:
                        assert local_model is not None
                        proba = local_model.predict_proba(full)[:, 1]
                        out_df = df_in.copy()
                        out_df["probability"] = proba
                        out_df["label"] = (proba >= cfg.threshold).astype(int)

                    st.write("Results preview:", out_df.head())
                    st.download_button(
                        "Download results CSV",
                        data=out_df.to_csv(index=False).encode("utf-8"),
                        file_name="predictions.csv",
                        mime="text/csv",
                    )
                    st.success("Batch prediction completed.")

                except requests.RequestException as e:
                    st.error(f"API request failed: {e}")
                except Exception as e:
                    st.error(f"Batch prediction failed: {e}")

    # -------------------------------------------------------------------
    # Tab 3: Model insights (global)
    # -------------------------------------------------------------------
    with tab3:
        st.subheader("Model insights")
        st.write("Global explanations derived from permutation importance (Phase 4).")

        if cfg.perm_importance is None or cfg.perm_importance.empty:
            st.info(
                "Permutation importance not found.\n\n"
                "Expected path:\n"
                f"{(ART_DIR / 'reports' / cfg.model_name / 'permutation_importance.csv')}"
            )
        else:
            imp = cfg.perm_importance.sort_values("importance_mean", ascending=False).head(20)
            st.dataframe(imp, use_container_width=True)

            chart_df = imp.iloc[::-1].set_index("feature")["importance_mean"]
            st.bar_chart(chart_df)

        st.markdown("---")
        st.write("Notes:")
        st.write(
            "- API mode demonstrates end-to-end serving (UI → API → model).\n"
            "- Local mode demonstrates that artifacts alone are enough to run inference.\n"
            "- The UI supports partial inputs; missing values are handled by the sklearn pipeline."
        )


if __name__ == "__main__":
    main()
