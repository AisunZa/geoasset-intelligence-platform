-- =========================================================
-- GeoAsset Intelligence Platform
-- Database Views
-- =========================================================


-- =========================================================
-- PIPELINE RISK METRICS
-- =========================================================

CREATE OR REPLACE VIEW pipeline_risk_metrics AS
SELECT
    p.pipeline_id,
    p.asset_code,

    EXTRACT(YEAR FROM CURRENT_DATE)::int
        - p.installation_year
        AS age_years,

    CURRENT_DATE
        - p.last_inspection
        AS days_since_last_inspection,

    (
        SELECT COUNT(*)
        FROM pipeline_failures f
        WHERE f.pipeline_id = p.pipeline_id
    ) AS failure_count,

    (
        SELECT COUNT(*)
        FROM buildings b
        WHERE ST_DWithin(
            p.geom,
            b.geom,
            100
        )
    ) AS buildings_within_100m,

    COALESCE(
        (
            SELECT ROUND(
                (
                    ST_Length(
                        ST_Intersection(
                            p.geom,
                            ST_UnaryUnion(
                                ST_Collect(r.geom)
                            )
                        )
                    )
                    / NULLIF(
                        ST_Length(p.geom),
                        0
                    )
                    * 100
                )::numeric,
                2
            )
            FROM risk_zones r
            WHERE r.zone_type = 'Flood'
              AND ST_Intersects(
                  p.geom,
                  r.geom
              )
        ),
        0
    ) AS flood_exposure_percent

FROM pipelines p;


-- =========================================================
-- PIPELINE RISK ASSESSMENT
-- =========================================================

CREATE OR REPLACE VIEW pipeline_risk_assessment AS
WITH scores AS (
    SELECT
        m.*,

        ROUND(
            (
                LEAST(age_years, 50)
                    / 50.0 * 25

                + LEAST(
                    days_since_last_inspection,
                    365
                )
                    / 365.0 * 10

                + LEAST(
                    failure_count,
                    3
                )
                    / 3.0 * 30

                + LEAST(
                    buildings_within_100m,
                    10
                )
                    / 10.0 * 15

                + flood_exposure_percent
                    / 100.0 * 20
            )::numeric,
            2
        ) AS risk_score

    FROM pipeline_risk_metrics m
)

SELECT
    *,

    CASE
        WHEN risk_score <= 30
            THEN 'Low'

        WHEN risk_score <= 60
            THEN 'Medium'

        WHEN risk_score <= 80
            THEN 'High'

        ELSE 'Critical'
    END AS risk_level

FROM scores;


-- =========================================================
-- SPATIAL RISK MAP FOR QGIS
-- =========================================================

CREATE OR REPLACE VIEW pipeline_risk_map AS
SELECT
    p.pipeline_id,
    p.asset_code,
    p.material,
    p.diameter_mm,
    p.installation_year,
    p.condition,
    p.status,

    r.age_years,
    r.days_since_last_inspection,
    r.failure_count,
    r.buildings_within_100m,
    r.flood_exposure_percent,
    r.risk_score,
    r.risk_level,

    p.geom

FROM pipelines p

JOIN pipeline_risk_assessment r
    ON p.pipeline_id = r.pipeline_id;