import json

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from api.database import get_engine


app = FastAPI(
    title="GeoAsset Intelligence API",
    description=(
        "REST API for pipeline infrastructure, "
        "risk assessment, failures, inspections, "
        "and maintenance data."
    ),
    version="1.0.0",
)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def require_pipeline(connection, pipeline_id: int):
    """
    Verify that a pipeline exists.

    Raises HTTP 404 if the pipeline does not exist.
    """

    exists = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pipelines
                WHERE pipeline_id = :pipeline_id
            );
            """
        ),
        {
            "pipeline_id": pipeline_id
        },
    ).scalar()

    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Pipeline not found",
        )


# -------------------------------------------------------------------
# General API endpoints
# -------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "GeoAsset Intelligence API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/database-health")
def database_health():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT PostGIS_Version();")
            )

            postgis_version = result.scalar()

        return {
            "database": "connected",
            "postgis_version": postgis_version,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Pipeline collection
# -------------------------------------------------------------------

@app.get("/pipelines")
def get_pipelines():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        pipeline_id,
                        asset_code,
                        material,
                        diameter_mm,
                        installation_year,
                        condition,
                        status
                    FROM pipelines
                    ORDER BY pipeline_id
                    LIMIT 100;
                    """
                )
            )

            pipelines = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "count": len(pipelines),
            "pipelines": pipelines,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Spatial bounding-box query
#
# Important:
# This route must remain ABOVE /pipelines/{pipeline_id}
# so FastAPI does not interpret "bbox" as a pipeline ID.
# -------------------------------------------------------------------

@app.get("/pipelines/bbox")
def get_pipelines_bbox(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
):
    if min_lon >= max_lon:
        raise HTTPException(
            status_code=400,
            detail="min_lon must be smaller than max_lon",
        )

    if min_lat >= max_lat:
        raise HTTPException(
            status_code=400,
            detail="min_lat must be smaller than max_lat",
        )

    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        p.pipeline_id,
                        p.asset_code,
                        r.risk_score,
                        r.risk_level,

                        ST_AsGeoJSON(
                            ST_Transform(
                                p.geom,
                                4326
                            )
                        ) AS geometry

                    FROM pipelines p

                    JOIN pipeline_risk_assessment r
                        ON p.pipeline_id = r.pipeline_id

                    WHERE ST_Intersects(
                        p.geom,
                        ST_Transform(
                            ST_MakeEnvelope(
                                :min_lon,
                                :min_lat,
                                :max_lon,
                                :max_lat,
                                4326
                            ),
                            25832
                        )
                    )

                    ORDER BY p.pipeline_id;
                    """
                ),
                {
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat,
                },
            )

            features = []

            for row in result:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": json.loads(
                            row._mapping["geometry"]
                        ),
                        "properties": {
                            "pipeline_id":
                                row._mapping["pipeline_id"],

                            "asset_code":
                                row._mapping["asset_code"],

                            "risk_score":
                                float(
                                    row._mapping["risk_score"]
                                ),

                            "risk_level":
                                row._mapping["risk_level"],
                        },
                    }
                )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Single pipeline
# -------------------------------------------------------------------

@app.get("/pipelines/{pipeline_id}")
def get_pipeline(pipeline_id: int):
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        p.pipeline_id,
                        p.asset_code,
                        p.material,
                        p.diameter_mm,
                        p.installation_year,
                        p.pressure_bar,
                        p.condition,
                        p.status,
                        p.last_inspection,

                        r.age_years,
                        r.days_since_last_inspection,
                        r.failure_count,
                        r.buildings_within_100m,
                        r.flood_exposure_percent,
                        r.risk_score,
                        r.risk_level

                    FROM pipelines p

                    JOIN pipeline_risk_assessment r
                        ON p.pipeline_id = r.pipeline_id

                    WHERE p.pipeline_id = :pipeline_id;
                    """
                ),
                {
                    "pipeline_id": pipeline_id
                },
            )

            row = result.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Pipeline not found",
            )

        return dict(row._mapping)

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Single pipeline GeoJSON
# -------------------------------------------------------------------

@app.get("/pipelines/{pipeline_id}/geojson")
def get_pipeline_geojson(pipeline_id: int):
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        p.pipeline_id,
                        p.asset_code,
                        r.risk_score,
                        r.risk_level,

                        ST_AsGeoJSON(
                            ST_Transform(
                                p.geom,
                                4326
                            )
                        ) AS geometry

                    FROM pipelines p

                    JOIN pipeline_risk_assessment r
                        ON p.pipeline_id = r.pipeline_id

                    WHERE p.pipeline_id = :pipeline_id;
                    """
                ),
                {
                    "pipeline_id": pipeline_id
                },
            )

            row = result.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Pipeline not found",
            )

        return {
            "type": "Feature",
            "geometry": json.loads(
                row._mapping["geometry"]
            ),
            "properties": {
                "pipeline_id":
                    row._mapping["pipeline_id"],

                "asset_code":
                    row._mapping["asset_code"],

                "risk_score":
                    float(
                        row._mapping["risk_score"]
                    ),

                "risk_level":
                    row._mapping["risk_level"],
            },
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Pipeline failures
# -------------------------------------------------------------------

@app.get("/pipelines/{pipeline_id}/failures")
def get_pipeline_failures(pipeline_id: int):
    engine = get_engine()

    try:
        with engine.connect() as connection:

            require_pipeline(
                connection,
                pipeline_id,
            )

            result = connection.execute(
                text(
                    """
                    SELECT
                        failure_id,
                        failure_date,
                        failure_type,
                        severity,
                        description,
                        repair_cost
                    FROM pipeline_failures
                    WHERE pipeline_id = :pipeline_id
                    ORDER BY failure_date DESC;
                    """
                ),
                {
                    "pipeline_id": pipeline_id
                },
            )

            failures = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "pipeline_id": pipeline_id,
            "failure_count": len(failures),
            "failures": failures,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Pipeline inspections
# -------------------------------------------------------------------

@app.get("/pipelines/{pipeline_id}/inspections")
def get_pipeline_inspections(pipeline_id: int):
    engine = get_engine()

    try:
        with engine.connect() as connection:

            require_pipeline(
                connection,
                pipeline_id,
            )

            result = connection.execute(
                text(
                    """
                    SELECT
                        inspection_id,
                        inspection_date,
                        inspector,
                        condition_score,
                        corrosion_level,
                        leakage_detected,
                        notes
                    FROM inspections
                    WHERE pipeline_id = :pipeline_id
                    ORDER BY inspection_date DESC;
                    """
                ),
                {
                    "pipeline_id": pipeline_id
                },
            )

            inspections = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "pipeline_id": pipeline_id,
            "inspection_count": len(inspections),
            "inspections": inspections,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Pipeline maintenance
# -------------------------------------------------------------------

@app.get("/pipelines/{pipeline_id}/maintenance")
def get_pipeline_maintenance(pipeline_id: int):
    engine = get_engine()

    try:
        with engine.connect() as connection:

            require_pipeline(
                connection,
                pipeline_id,
            )

            result = connection.execute(
                text(
                    """
                    SELECT
                        maintenance_id,
                        maintenance_date,
                        maintenance_type,
                        cost,
                        description
                    FROM maintenance
                    WHERE pipeline_id = :pipeline_id
                    ORDER BY maintenance_date DESC;
                    """
                ),
                {
                    "pipeline_id": pipeline_id
                },
            )

            maintenance_records = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "pipeline_id": pipeline_id,
            "maintenance_count":
                len(maintenance_records),
            "maintenance":
                maintenance_records,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# High-risk pipelines
# -------------------------------------------------------------------

@app.get("/risk/high")
def get_high_risk_pipelines():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        pipeline_id,
                        asset_code,
                        risk_score,
                        risk_level,
                        failure_count,
                        buildings_within_100m,
                        flood_exposure_percent
                    FROM pipeline_risk_assessment
                    WHERE risk_level IN (
                        'High',
                        'Critical'
                    )
                    ORDER BY risk_score DESC;
                    """
                )
            )

            pipelines = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "count": len(pipelines),
            "pipelines": pipelines,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# High-risk pipelines GeoJSON
# -------------------------------------------------------------------

@app.get("/risk/high/geojson")
def get_high_risk_geojson():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        p.pipeline_id,
                        p.asset_code,
                        r.risk_score,
                        r.risk_level,

                        ST_AsGeoJSON(
                            ST_Transform(
                                p.geom,
                                4326
                            )
                        ) AS geometry

                    FROM pipelines p

                    JOIN pipeline_risk_assessment r
                        ON p.pipeline_id = r.pipeline_id

                    WHERE r.risk_level IN (
                        'High',
                        'Critical'
                    )

                    ORDER BY r.risk_score DESC;
                    """
                )
            )

            features = []

            for row in result:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": json.loads(
                            row._mapping["geometry"]
                        ),
                        "properties": {
                            "pipeline_id":
                                row._mapping["pipeline_id"],

                            "asset_code":
                                row._mapping["asset_code"],

                            "risk_score":
                                float(
                                    row._mapping["risk_score"]
                                ),

                            "risk_level":
                                row._mapping["risk_level"],
                        },
                    }
                )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Risk summary
# -------------------------------------------------------------------

@app.get("/risk/summary")
def get_risk_summary():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        risk_level,
                        COUNT(*) AS pipeline_count,
                        ROUND(
                            AVG(risk_score),
                            2
                        ) AS average_risk_score

                    FROM pipeline_risk_assessment

                    GROUP BY risk_level

                    ORDER BY
                        CASE risk_level
                            WHEN 'Critical' THEN 1
                            WHEN 'High' THEN 2
                            WHEN 'Medium' THEN 3
                            WHEN 'Low' THEN 4
                        END;
                    """
                )
            )

            summary = [
                {
                    "risk_level":
                        row._mapping["risk_level"],

                    "pipeline_count":
                        row._mapping["pipeline_count"],

                    "average_risk_score":
                        float(
                            row._mapping[
                                "average_risk_score"
                            ]
                        ),
                }
                for row in result
            ]

        return {
            "summary": summary
        }

    finally:
        engine.dispose()


# -------------------------------------------------------------------
# Network statistics
# -------------------------------------------------------------------

@app.get("/stats")
def get_network_statistics():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total_pipelines,

                        ROUND(
                            SUM(
                                ST_Length(geom)
                            )::numeric
                            / 1000,
                            2
                        ) AS total_length_km,

                        ROUND(
                            AVG(
                                EXTRACT(
                                    YEAR
                                    FROM CURRENT_DATE
                                )
                                - installation_year
                            )::numeric,
                            2
                        ) AS average_age_years,

                        ROUND(
                            AVG(
                                diameter_mm
                            )::numeric,
                            2
                        ) AS average_diameter_mm

                    FROM pipelines;
                    """
                )
            )

            row = result.fetchone()

            failure_result = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM pipeline_failures;
                    """
                )
            )

            total_failures = failure_result.scalar()

        return {
            "total_pipelines":
                row._mapping["total_pipelines"],

            "total_length_km":
                float(
                    row._mapping["total_length_km"]
                ),

            "average_age_years":
                float(
                    row._mapping["average_age_years"]
                ),

            "average_diameter_mm":
                float(
                    row._mapping[
                        "average_diameter_mm"
                    ]
                ),

            "total_failures":
                total_failures,
        }

    finally:
        engine.dispose()