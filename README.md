# GeoAsset Intelligence Platform

A geospatial pipeline infrastructure risk and maintenance management system built with QGIS, PostGIS, and Python.

## Project Goal

The project analyzes pipeline infrastructure and helps identify higher-risk pipeline segments based on factors such as:

- Pipeline age
- Inspection recency
- Failure history
- Nearby buildings
- Flood exposure

## Technology Stack

* QGIS / PyQGIS
* PostgreSQL / PostGIS
* Python 3.13
* GeoPandas
* Shapely
* Pandas
* SQLAlchemy
* Psycopg
* FastAPI
* Uvicorn
* Docker
* Docker Compose
* Pytest
* GitHub Actions

## Current Features

- Spatial pipeline database using PostGIS
- Pipeline failure management
- Inspection and maintenance records
- Building proximity analysis
- Flood-risk intersection analysis
- Pipeline risk scoring
- Risk classification
- QGIS risk visualization
- Python geospatial analysis with GeoPandas
- Python/PostGIS analytical result validation

## Risk Model

The current risk score uses five factors:

| Factor | Weight |
|---|---:|
| Pipeline age | 25% |
| Failure history | 30% |
| Flood exposure | 20% |
| Nearby buildings | 15% |
| Inspection recency | 10% |

Risk levels are classified as:

- Low: 0–30
- Medium: 30–60
- High: 60–80
- Critical: 80–100

## Project Structure

```text
geoasset-intelligence-platform/
│
├── database/
│   ├── 01_schema.sql
│   ├── 02_views.sql
│   └── 03_sample_data.sql
│
├── etl/
│   ├── read_pipeline_risk.py
│   └── risk_calculator.py
│
├── qgis/
│   └── geoasset_pipeline.qgz
│
├── environment.yml
├── .gitignore
└── README.md