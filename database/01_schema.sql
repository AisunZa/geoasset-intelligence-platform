-- =========================================================
-- GeoAsset Intelligence Platform
-- Database Schema
-- =========================================================


-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;


-- =========================================================
-- PIPELINES
-- =========================================================

CREATE TABLE IF NOT EXISTS pipelines (
    pipeline_id SERIAL PRIMARY KEY,
    asset_code VARCHAR(50) UNIQUE NOT NULL,
    material VARCHAR(50),
    diameter_mm INTEGER,
    installation_year INTEGER,
    pressure_bar NUMERIC(6,2),
    condition VARCHAR(20),
    status VARCHAR(20),
    last_inspection DATE,
    risk_score NUMERIC(5,2),
    geom geometry(LineString, 25832)
);

CREATE INDEX IF NOT EXISTS idx_pipelines_geom
ON pipelines
USING GIST (geom);


-- =========================================================
-- PIPELINE FAILURES
-- =========================================================

CREATE TABLE IF NOT EXISTS pipeline_failures (
    failure_id SERIAL PRIMARY KEY,
    pipeline_id INTEGER REFERENCES pipelines(pipeline_id),
    failure_date DATE NOT NULL,
    failure_type VARCHAR(50),
    severity VARCHAR(20),
    description TEXT,
    repair_cost NUMERIC(12,2),
    geom geometry(Point, 25832)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_failures_geom
ON pipeline_failures
USING GIST (geom);


-- =========================================================
-- INSPECTIONS
-- =========================================================

CREATE TABLE IF NOT EXISTS inspections (
    inspection_id SERIAL PRIMARY KEY,
    pipeline_id INTEGER REFERENCES pipelines(pipeline_id),
    inspection_date DATE NOT NULL,
    inspector VARCHAR(100),
    condition_score INTEGER,
    corrosion_level VARCHAR(20),
    leakage_detected BOOLEAN,
    notes TEXT
);


-- =========================================================
-- MAINTENANCE
-- =========================================================

CREATE TABLE IF NOT EXISTS maintenance (
    maintenance_id SERIAL PRIMARY KEY,
    pipeline_id INTEGER REFERENCES pipelines(pipeline_id),
    maintenance_date DATE NOT NULL,
    maintenance_type VARCHAR(100),
    cost NUMERIC(12,2),
    description TEXT
);


-- =========================================================
-- BUILDINGS
-- =========================================================

CREATE TABLE IF NOT EXISTS buildings (
    building_id SERIAL PRIMARY KEY,
    building_type VARCHAR(50),
    name VARCHAR(100),
    geom geometry(Polygon, 25832)
);

CREATE INDEX IF NOT EXISTS idx_buildings_geom
ON buildings
USING GIST (geom);


-- =========================================================
-- RISK ZONES
-- =========================================================

CREATE TABLE IF NOT EXISTS risk_zones (
    risk_zone_id SERIAL PRIMARY KEY,
    zone_type VARCHAR(50),
    risk_level VARCHAR(20),
    geom geometry(MultiPolygon, 25832)
);

CREATE INDEX IF NOT EXISTS idx_risk_zones_geom
ON risk_zones
USING GIST (geom);