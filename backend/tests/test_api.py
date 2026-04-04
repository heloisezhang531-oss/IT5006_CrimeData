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
        "/api/eda/overview/total-records",
        "/api/eda/overview/missing-values",
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
        "/api/eda/raw/recent?limit=200",
        "/api/eda/victim/filters",
    ]
    for endpoint in endpoints:
        res = client.get(endpoint)
        assert res.status_code == 200, endpoint
        body = res.json()
        assert "meta" in body and "data" in body, endpoint


def test_eda_victim_dashboard_contract():
    payload = {
        "age_min": 18,
        "age_max": 65,
        "offense_categories": ["Assault", "Robbery"],
        "include_raw_sample": True,
        "raw_limit": 50,
    }
    res = client.post("/api/eda/victim/dashboard", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    if body["data"]:
        row = body["data"][0]
        assert "kpi" in row
        assert "demographics" in row
        assert "relationships" in row
        assert "activity_heatmap" in row


def test_eda_boundary_validation():
    bad_year = client.get("/api/eda/geography/points?year=2026&limit=100")
    assert bad_year.status_code == 422

    bad_limit = client.get("/api/eda/categorical/top-crime-types?limit=0")
    assert bad_limit.status_code == 422

    bad_body = client.post(
        "/api/eda/victim/dashboard",
        json={"age_min": 30, "age_max": 20, "raw_limit": 0},
    )
    assert bad_body.status_code == 422
