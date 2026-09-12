-- =========================================================
-- GeoAsset Intelligence Platform
-- Sample Data
-- =========================================================


-- =========================================================
-- SAMPLE PIPELINE
-- =========================================================

INSERT INTO pipelines (
    asset_code,
    material,
    diameter_mm,
    installation_year,
    pressure_bar,
    condition,
    status,
    last_inspection,
    risk_score,
    geom
)
VALUES (
    'PIPE-0001',
    'Steel',
    400,
    1995,
    6.5,
    'Good',
    'Active',
    '2026-06-15',
    25.0,
    ST_GeomFromText(
        'LINESTRING(
            477000 5550000,
            477500 5550500
        )',
        25832
    )
);


-- =========================================================
-- SAMPLE PIPELINE FAILURE
-- =========================================================

INSERT INTO pipeline_failures (
    pipeline_id,
    failure_date,
    failure_type,
    severity,
    description,
    repair_cost,
    geom
)
VALUES (
    1,
    '2026-03-10',
    'Leak',
    'Medium',
    'Leak detected during routine inspection',
    2500.00,
    ST_GeomFromText(
        'POINT(
            477250 5550250
        )',
        25832
    )
);


-- =========================================================
-- SAMPLE INSPECTION
-- =========================================================

INSERT INTO inspections (
    pipeline_id,
    inspection_date,
    inspector,
    condition_score,
    corrosion_level,
    leakage_detected,
    notes
)
VALUES (
    1,
    '2026-06-15',
    'Inspector A',
    8,
    'Low',
    FALSE,
    'Routine inspection completed. Pipeline condition is good.'
);


-- =========================================================
-- SAMPLE MAINTENANCE
-- =========================================================

INSERT INTO maintenance (
    pipeline_id,
    maintenance_date,
    maintenance_type,
    cost,
    description
)
VALUES (
    1,
    '2026-03-12',
    'Leak Repair',
    2500.00,
    'Repaired leak found on PIPE-0001 and restored normal operation.'
);


-- =========================================================
-- SAMPLE BUILDING
-- =========================================================

INSERT INTO buildings (
    building_type,
    name,
    geom
)
VALUES (
    'Residential',
    'Building A',
    ST_GeomFromText(
        'POLYGON((
            477300 5550200,
            477340 5550200,
            477340 5550240,
            477300 5550240,
            477300 5550200
        ))',
        25832
    )
);


-- =========================================================
-- SAMPLE FLOOD-RISK ZONE
-- =========================================================

INSERT INTO risk_zones (
    zone_type,
    risk_level,
    geom
)
VALUES (
    'Flood',
    'High',
    ST_Multi(
        ST_GeomFromText(
            'POLYGON((
                477100 5550100,
                477450 5550100,
                477450 5550450,
                477100 5550450,
                477100 5550100
            ))',
            25832
        )
    )
);