from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["data"][0]["status"] == "ok"


def test_meta_filters_shape():
    res = client.get("/api/meta/filters")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body


def test_model_predict_shape():
    res = client.post("/api/model/predict-next-month", json={"target_month": None, "region_ids": [], "feature_mode": "with_hardship"})
    assert res.status_code == 200
    body = res.json()
    assert "data" in body


def test_eda_endpoints_contract():
    endpoints = [
        "/api/eda/key-stats/arrest-domestic",
        "/api/eda/temporal/yearly",
        "/api/eda/temporal/monthly",
        "/api/eda/temporal/day-of-week",
        "/api/eda/temporal/hour-day-heatmap",
        "/api/eda/temporal/crime-types-yearly?limit=all",
        "/api/eda/geography/points?year=2024&limit=500",
        "/api/eda/geography/community-choropleth?year=2024",
        "/api/eda/geography/community-geojson",
        "/api/eda/geography/hardship-index",
        "/api/eda/categorical/top-crime-types?limit=10",
        "/api/eda/categorical/top-locations?limit=10",
        "/api/eda/categorical/crime-location-heatmap?limit=10",
    ]
    for endpoint in endpoints:
        res = client.get(endpoint)
        assert res.status_code == 200, endpoint
        body = res.json()
        assert "meta" in body and "data" in body, endpoint


def test_eda_overview_endpoints_removed():
    removed_total = client.get("/api/eda/overview/total-records")
    assert removed_total.status_code == 404

    removed_missing = client.get("/api/eda/overview/missing-values")
    assert removed_missing.status_code == 404


def test_eda_boundary_validation():
    bad_year = client.get("/api/eda/geography/points?year=2026&limit=100")
    assert bad_year.status_code == 422

    bad_limit = client.get("/api/eda/categorical/top-crime-types?limit=0")
    assert bad_limit.status_code == 422


def test_victim_endpoints_removed():
    removed_get = client.get("/api/eda/victim/filters")
    assert removed_get.status_code == 404

    removed_post = client.post("/api/eda/victim/dashboard", json={})
    assert removed_post.status_code == 404


def test_raw_and_model_lab_endpoints_removed():
    removed_raw = client.get("/api/eda/raw/recent?limit=200")
    assert removed_raw.status_code == 404

    removed_model_lab_ablation = client.get("/api/model-lab/ablation")
    assert removed_model_lab_ablation.status_code == 404

    removed_model_lab_generalization = client.get("/api/model-lab/generalization")
    assert removed_model_lab_generalization.status_code == 404

    removed_model_lab_reliability = client.get("/api/model-lab/reliability")
    assert removed_model_lab_reliability.status_code == 404
