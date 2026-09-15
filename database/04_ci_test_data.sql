-- Deterministic dataset used only by GitHub Actions integration tests.

TRUNCATE TABLE
    maintenance,
    inspections,
    pipeline_failures,
    buildings,
    risk_zones,
    pipelines
RESTART IDENTITY CASCADE;


-- ---------------------------------------------------------
-- Four pipelines: Low, Medium, High, Critical
-- ---------------------------------------------------------

INSERT INTO pipelines (
    pipeline_id,
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
VALUES
(
    1,
    'PIPE-CI-LOW',
    'PVC',
    100,
    EXTRACT(YEAR FROM CURRENT_DATE)::int,
    4.00,
    'Good',
    'Active',
    CURRENT_DATE,
    NULL,
    ST_Transform(
        ST_GeomFromText(
            'LINESTRING(8.6810 50.1010, 8.6820 50.1020)',
            4326
        ),
        25832
    )
),
(
    2,
    'PIPE-CI-MEDIUM',
    'Ductile Iron',
    150,
    EXTRACT(YEAR FROM CURRENT_DATE)::int - 60,
    5.00,
    'Fair',
    'Active',
    CURRENT_DATE - 400,
    NULL,
    ST_Transform(
        ST_GeomFromText(
            'LINESTRING(8.6830 50.1030, 8.6840 50.1040)',
            4326
        ),
        25832
    )
),
(
    3,
    'PIPE-CI-HIGH',
    'Cast Iron',
    200,
    EXTRACT(YEAR FROM CURRENT_DATE)::int - 60,
    5.50,
    'Poor',
    'Active',
    CURRENT_DATE - 400,
    NULL,
    ST_Transform(
        ST_GeomFromText(
            'LINESTRING(8.6850 50.1050, 8.6860 50.1060)',
            4326
        ),
        25832
    )
),
(
    469,
    'PIPE-00469',
    'Steel',
    150,
    EXTRACT(YEAR FROM CURRENT_DATE)::int - 60,
    6.38,
    'Fair',
    'Active',
    CURRENT_DATE - 400,
    NULL,
    ST_Transform(
        ST_GeomFromText(
            'LINESTRING(8.6870 50.1070, 8.6880 50.1080)',
            4326
        ),
        25832
    )
);

SELECT setval(
    pg_get_serial_sequence('pipelines', 'pipeline_id'),
    469,
    true
);


-- ---------------------------------------------------------
-- Three failures for Critical pipeline 469
-- ---------------------------------------------------------

INSERT INTO pipeline_failures (
    pipeline_id,
    failure_date,
    failure_type,
    severity,
    description,
    repair_cost,
    geom
)
VALUES
(
    469,
    CURRENT_DATE - 300,
    'Leak',
    'High',
    'CI test failure 1',
    3000,
    ST_Transform(
        ST_SetSRID(ST_MakePoint(8.6872, 50.1072), 4326),
        25832
    )
),
(
    469,
    CURRENT_DATE - 200,
    'Corrosion',
    'High',
    'CI test failure 2',
    4500,
    ST_Transform(
        ST_SetSRID(ST_MakePoint(8.6875, 50.1075), 4326),
        25832
    )
),
(
    469,
    CURRENT_DATE - 100,
    'Burst',
    'Critical',
    'CI test failure 3',
    9000,
    ST_Transform(
        ST_SetSRID(ST_MakePoint(8.6878, 50.1078), 4326),
        25832
    )
);


-- ---------------------------------------------------------
-- Four inspections for pipeline 469
-- ---------------------------------------------------------

INSERT INTO inspections (
    pipeline_id,
    inspection_date,
    inspector,
    condition_score,
    corrosion_level,
    leakage_detected,
    notes
)
VALUES
(469, CURRENT_DATE - 30,  'CI Inspector A', 4, 'High',   TRUE,  'CI inspection 1'),
(469, CURRENT_DATE - 120, 'CI Inspector B', 5, 'Medium', FALSE, 'CI inspection 2'),
(469, CURRENT_DATE - 240, 'CI Inspector C', 5, 'Medium', TRUE,  'CI inspection 3'),
(469, CURRENT_DATE - 400, 'CI Inspector D', 6, 'Low',    FALSE, 'CI inspection 4');


-- ---------------------------------------------------------
-- Three maintenance records for pipeline 469
-- ---------------------------------------------------------

INSERT INTO maintenance (
    pipeline_id,
    maintenance_date,
    maintenance_type,
    cost,
    description
)
VALUES
(469, CURRENT_DATE - 25,  'Leak Repair',     3200, 'CI maintenance 1'),
(469, CURRENT_DATE - 115, 'Corrosion Repair', 4700, 'CI maintenance 2'),
(469, CURRENT_DATE - 195, 'Emergency Repair', 9100, 'CI maintenance 3');


-- ---------------------------------------------------------
-- Buildings near High pipeline
-- ---------------------------------------------------------

INSERT INTO buildings (
    building_type,
    name,
    geom
)
SELECT
    'Residential',
    'High-risk building ' || i,
    ST_Transform(
        ST_MakeEnvelope(
            8.68510 + i * 0.00002,
            50.10520,
            8.68511 + i * 0.00002,
            50.10521,
            4326
        ),
        25832
    )
FROM generate_series(1, 10) AS s(i);


-- ---------------------------------------------------------
-- Buildings near Critical pipeline
-- ---------------------------------------------------------

INSERT INTO buildings (
    building_type,
    name,
    geom
)
SELECT
    'Residential',
    'Critical-risk building ' || i,
    ST_Transform(
        ST_MakeEnvelope(
            8.68710 + i * 0.00002,
            50.10720,
            8.68711 + i * 0.00002,
            50.10721,
            4326
        ),
        25832
    )
FROM generate_series(1, 10) AS s(i);


-- ---------------------------------------------------------
-- Flood zone covering High and Critical pipelines
-- ---------------------------------------------------------

INSERT INTO risk_zones (
    zone_type,
    risk_level,
    geom
)
VALUES (
    'Flood',
    'High',
    ST_Multi(
        ST_Transform(
            ST_MakeEnvelope(
                8.6847,
                50.1047,
                8.6883,
                50.1083,
                4326
            ),
            25832
        )
    )
);