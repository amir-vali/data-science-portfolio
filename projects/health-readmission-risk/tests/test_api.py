from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    payload = r.json()
    assert "status" in payload


def test_predict_minimal_payload() -> None:
    # Provide only a few known columns; missing columns will be filled with None.
    # Note: this requires artifacts/feature_columns.json to exist.
    payload = {
        "features": {
            "time_in_hospital": 3,
            "num_lab_procedures": 42,
            "num_medications": 10,
        }
    }
    r = client.post("/predict", json=payload)
    assert r.status_code in (200, 422)  # 422 if any of these keys are not in your schema
    if r.status_code == 200:
        out = r.json()
        assert "probability" in out
        assert "label" in out
        assert "threshold" in out
