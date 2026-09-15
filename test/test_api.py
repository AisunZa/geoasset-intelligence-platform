import os

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)

EXPECTED_TOTAL_PIPELINES = int(
    os.getenv("GEOASSET_EXPECTED_PIPELINE_COUNT", "500")
)

EXPECTED_TOTAL_FAILURES = int(
    os.getenv("GEOASSET_EXPECTED_FAILURE_COUNT", "267")
)

# ---------------------------------------------------------
# Database test configuration
# ---------------------------------------------------------

requires_database = pytest.mark.skipif(
    not os.getenv("GEOASSET_DB_PASSWORD"),
    reason="GEOASSET_DB_PASSWORD is not set",
)


# ---------------------------------------------------------
# Basic API tests
# ---------------------------------------------------------

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok"
    }


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "GeoAsset Intelligence API is running"
    }


# ---------------------------------------------------------
# Database health
# ---------------------------------------------------------

@requires_database
def test_database_health():
    response = client.get("/database-health")

    assert response.status_code == 200

    data = response.json()

    assert data["database"] == "connected"
    assert "postgis_version" in data
    assert data["postgis_version"] is not None


# ---------------------------------------------------------
# Pipeline collection
# ---------------------------------------------------------

@requires_database
def test_get_pipelines():
    response = client.get("/pipelines")

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert "pipelines" in data

    assert data["count"] > 0
    assert len(data["pipelines"]) == data["count"]

    pipeline = data["pipelines"][0]

    assert "pipeline_id" in pipeline
    assert "asset_code" in pipeline
    assert "material" in pipeline
    assert "diameter_mm" in pipeline
    assert "installation_year" in pipeline
    assert "condition" in pipeline
    assert "status" in pipeline


# ---------------------------------------------------------
# Single pipeline
# ---------------------------------------------------------

@requires_database
def test_get_pipeline():
    response = client.get("/pipelines/469")

    assert response.status_code == 200

    data = response.json()

    assert data["pipeline_id"] == 469
    assert data["asset_code"] == "PIPE-00469"

    assert "material" in data
    assert "diameter_mm" in data
    assert "installation_year" in data
    assert "risk_score" in data
    assert "risk_level" in data

    assert data["risk_level"] == "Critical"


@requires_database
def test_pipeline_not_found():
    response = client.get("/pipelines/9999")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Pipeline not found"
    }


# ---------------------------------------------------------
# Pipeline GeoJSON
# ---------------------------------------------------------

@requires_database
def test_pipeline_geojson():
    response = client.get(
        "/pipelines/469/geojson"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["type"] == "Feature"

    assert "geometry" in data
    assert "properties" in data

    assert data["geometry"]["type"] == "LineString"

    assert (
        data["properties"]["pipeline_id"]
        == 469
    )

    assert (
        data["properties"]["asset_code"]
        == "PIPE-00469"
    )

    assert (
        data["properties"]["risk_level"]
        == "Critical"
    )


@requires_database
def test_pipeline_geojson_not_found():
    response = client.get(
        "/pipelines/9999/geojson"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Pipeline not found"
    }


# ---------------------------------------------------------
# Failures
# ---------------------------------------------------------

@requires_database
def test_pipeline_failures():
    response = client.get(
        "/pipelines/469/failures"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["pipeline_id"] == 469
    assert data["failure_count"] == 3
    assert len(data["failures"]) == 3

    failure = data["failures"][0]

    assert "failure_id" in failure
    assert "failure_date" in failure
    assert "failure_type" in failure
    assert "severity" in failure
    assert "repair_cost" in failure


@requires_database
def test_pipeline_failures_not_found():
    response = client.get(
        "/pipelines/9999/failures"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Pipeline not found"
    }


# ---------------------------------------------------------
# Inspections
# ---------------------------------------------------------

@requires_database
def test_pipeline_inspections():
    response = client.get(
        "/pipelines/469/inspections"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["pipeline_id"] == 469
    assert data["inspection_count"] == 4
    assert len(data["inspections"]) == 4

    inspection = data["inspections"][0]

    assert "inspection_id" in inspection
    assert "inspection_date" in inspection
    assert "inspector" in inspection
    assert "condition_score" in inspection
    assert "corrosion_level" in inspection
    assert "leakage_detected" in inspection


@requires_database
def test_pipeline_inspections_not_found():
    response = client.get(
        "/pipelines/9999/inspections"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Pipeline not found"
    }


# ---------------------------------------------------------
# Maintenance
# ---------------------------------------------------------

@requires_database
def test_pipeline_maintenance():
    response = client.get(
        "/pipelines/469/maintenance"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["pipeline_id"] == 469
    assert data["maintenance_count"] == 3
    assert len(data["maintenance"]) == 3

    maintenance = data["maintenance"][0]

    assert "maintenance_id" in maintenance
    assert "maintenance_date" in maintenance
    assert "maintenance_type" in maintenance
    assert "cost" in maintenance
    assert "description" in maintenance


@requires_database
def test_pipeline_maintenance_not_found():
    response = client.get(
        "/pipelines/9999/maintenance"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Pipeline not found"
    }


# ---------------------------------------------------------
# High-risk pipelines
# ---------------------------------------------------------

@requires_database
def test_high_risk_pipelines():
    response = client.get("/risk/high")

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert "pipelines" in data

    assert data["count"] > 0

    for pipeline in data["pipelines"]:
        assert pipeline["risk_level"] in {
            "High",
            "Critical",
        }


# ---------------------------------------------------------
# High-risk GeoJSON
# ---------------------------------------------------------

@requires_database
def test_high_risk_geojson():
    response = client.get(
        "/risk/high/geojson"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["type"] == "FeatureCollection"
    assert "features" in data

    assert len(data["features"]) > 0

    feature = data["features"][0]

    assert feature["type"] == "Feature"
    assert "geometry" in feature
    assert "properties" in feature

    assert feature["geometry"]["type"] == "LineString"

    assert feature["properties"]["risk_level"] in {
        "High",
        "Critical",
    }


# ---------------------------------------------------------
# Risk summary
# ---------------------------------------------------------

@requires_database
def test_risk_summary():
    response = client.get("/risk/summary")

    assert response.status_code == 200

    data = response.json()

    assert "summary" in data

    summary = data["summary"]

    assert len(summary) > 0

    risk_levels = {
        row["risk_level"]
        for row in summary
    }

    assert "Low" in risk_levels
    assert "Medium" in risk_levels
    assert "High" in risk_levels
    assert "Critical" in risk_levels

    total_pipelines = sum(
        row["pipeline_count"]
        for row in summary
    )

    assert total_pipelines == EXPECTED_TOTAL_PIPELINES


# ---------------------------------------------------------
# Network statistics
# ---------------------------------------------------------

@requires_database
def test_network_statistics():
    response = client.get("/stats")

    assert response.status_code == 200

    data = response.json()

    assert data["total_pipelines"] == EXPECTED_TOTAL_PIPELINES
    assert data["total_length_km"] > 0
    assert data["average_age_years"] > 0
    assert data["average_diameter_mm"] > 0
    assert data["total_failures"] == EXPECTED_TOTAL_FAILURES


# ---------------------------------------------------------
# Bounding-box spatial query
# ---------------------------------------------------------

@requires_database
def test_bbox_query():
    response = client.get(
        "/pipelines/bbox",
        params={
            "min_lon": 8.68,
            "min_lat": 50.10,
            "max_lon": 8.69,
            "max_lat": 50.11,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) > 0

    feature = data["features"][0]

    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "LineString"

    assert "pipeline_id" in feature["properties"]
    assert "asset_code" in feature["properties"]
    assert "risk_score" in feature["properties"]
    assert "risk_level" in feature["properties"]


# ---------------------------------------------------------
# Invalid bounding boxes
# ---------------------------------------------------------

@requires_database
def test_bbox_invalid_longitude():
    response = client.get(
        "/pipelines/bbox",
        params={
            "min_lon": 8.70,
            "min_lat": 50.10,
            "max_lon": 8.60,
            "max_lat": 50.11,
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail":
            "min_lon must be smaller than max_lon"
    }


@requires_database
def test_bbox_invalid_latitude():
    response = client.get(
        "/pipelines/bbox",
        params={
            "min_lon": 8.68,
            "min_lat": 50.20,
            "max_lon": 8.69,
            "max_lat": 50.10,
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail":
            "min_lat must be smaller than max_lat"
    }