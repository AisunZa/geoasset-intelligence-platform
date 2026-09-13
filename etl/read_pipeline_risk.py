"""
GeoAsset Intelligence Platform
Pipeline Infrastructure Risk Analysis

This script:

1. Connects Python to PostgreSQL/PostGIS
2. Loads pipeline infrastructure data
3. Loads buildings and flood-risk zones
4. Calculates pipeline lengths
5. Counts failures
6. Counts inspections
7. Counts maintenance activities
8. Finds buildings within 100 meters
9. Calculates flood exposure
10. Calculates pipeline age
11. Calculates days since last inspection
12. Calculates pipeline risk scores
13. Classifies risk levels
14. Compares Python results with PostGIS
15. Produces a pipeline risk summary

Project:
GeoAsset Intelligence Platform

Technologies:
Python
GeoPandas
PostgreSQL
PostGIS
SQLAlchemy
Psycopg
QGIS
"""

# ============================================================
# IMPORTS
# ============================================================

import math
from getpass import getpass

import geopandas as gpd
import pandas as pd

from sqlalchemy import create_engine, URL

from risk_calculator import calculate_risk_score


# ============================================================
# CONFIGURATION
# ============================================================

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "geoasset"
DB_USER = "postgres"

PROJECT_CRS = "EPSG:25832"

BUILDING_DISTANCE_METERS = 100


# ============================================================
# DATABASE CONNECTION
# ============================================================

def create_database_engine():
    """
    Create a SQLAlchemy connection to PostgreSQL/PostGIS.

    Password is requested securely and is never stored
    directly inside the source code.
    """

    password = getpass("PostgreSQL password: ")

    database_url = URL.create(
        "postgresql+psycopg",
        username=DB_USER,
        password=password,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

    engine = create_engine(database_url)

    return engine


# ============================================================
# LOAD SPATIAL DATA
# ============================================================

def load_spatial_data(engine):
    """
    Read the spatial tables and views from PostGIS.
    """

    pipelines = gpd.read_postgis(
        """
        SELECT *
        FROM pipelines
        ORDER BY pipeline_id
        """,
        engine,
        geom_col="geom"
    )

    failures = gpd.read_postgis(
        """
        SELECT *
        FROM pipeline_failures
        """,
        engine,
        geom_col="geom"
    )

    buildings = gpd.read_postgis(
        """
        SELECT *
        FROM buildings
        """,
        engine,
        geom_col="geom"
    )

    risk_zones = gpd.read_postgis(
        """
        SELECT *
        FROM risk_zones
        WHERE zone_type = 'Flood'
        """,
        engine,
        geom_col="geom"
    )

    postgis_risk_map = gpd.read_postgis(
        """
        SELECT *
        FROM pipeline_risk_map
        ORDER BY pipeline_id
        """,
        engine,
        geom_col="geom"
    )

    return (
        pipelines,
        failures,
        buildings,
        risk_zones,
        postgis_risk_map
    )


# ============================================================
# LOAD NON-SPATIAL DATA
# ============================================================

def load_attribute_data(engine):
    """
    Load inspections and maintenance records.
    """

    inspections = pd.read_sql(
        """
        SELECT *
        FROM inspections
        """,
        engine
    )

    maintenance = pd.read_sql(
        """
        SELECT *
        FROM maintenance
        """,
        engine
    )

    return inspections, maintenance


# ============================================================
# DATABASE DATE
# ============================================================

def get_database_date(engine):
    """
    Read PostgreSQL CURRENT_DATE.

    Using the database date ensures that Python and PostGIS
    calculate pipeline age and inspection age using the
    exact same reference date.
    """

    result = pd.read_sql(
        """
        SELECT CURRENT_DATE AS current_date
        """,
        engine
    )

    return pd.Timestamp(result.loc[0, "current_date"])


# ============================================================
# CRS VALIDATION
# ============================================================

def validate_crs(*geodataframes):
    """
    Verify that spatial layers use EPSG:25832.

    EPSG:25832 is a projected CRS using meters,
    which allows reliable distance and length calculations.
    """

    for gdf in geodataframes:

        if gdf.empty:
            continue

        if gdf.crs is None:
            raise ValueError(
                "A spatial layer does not have a CRS."
            )

        epsg = gdf.crs.to_epsg()

        if epsg != 25832:
            raise ValueError(
                f"Expected EPSG:25832 but found {gdf.crs}"
            )

    print("CRS validation successful.")
    print(f"Project CRS: {PROJECT_CRS}")


# ============================================================
# PIPELINE LENGTH
# ============================================================

def calculate_pipeline_lengths(pipelines):
    """
    Calculate pipeline length in meters.
    """

    pipelines = pipelines.copy()

    pipelines["length_m"] = pipelines.geometry.length

    return pipelines


# ============================================================
# FAILURE COUNT
# ============================================================

def calculate_failure_counts(pipelines, failures):
    """
    Count recorded failures for every pipeline.
    """

    pipelines = pipelines.copy()

    if failures.empty:

        pipelines["python_failure_count"] = 0

        return pipelines

    failure_counts = (
        failures
        .groupby("pipeline_id")["failure_id"]
        .count()
    )

    pipelines["python_failure_count"] = (
        pipelines["pipeline_id"]
        .map(failure_counts)
        .fillna(0)
        .astype(int)
    )

    return pipelines


# ============================================================
# INSPECTION COUNT
# ============================================================

def calculate_inspection_counts(pipelines, inspections):
    """
    Count inspection records for every pipeline.
    """

    pipelines = pipelines.copy()

    if inspections.empty:

        pipelines["inspection_count"] = 0

        return pipelines

    inspection_counts = (
        inspections
        .groupby("pipeline_id")["inspection_id"]
        .count()
    )

    pipelines["inspection_count"] = (
        pipelines["pipeline_id"]
        .map(inspection_counts)
        .fillna(0)
        .astype(int)
    )

    return pipelines


# ============================================================
# MAINTENANCE COUNT
# ============================================================

def calculate_maintenance_counts(pipelines, maintenance):
    """
    Count maintenance records for every pipeline.
    """

    pipelines = pipelines.copy()

    if maintenance.empty:

        pipelines["maintenance_count"] = 0

        return pipelines

    maintenance_counts = (
        maintenance
        .groupby("pipeline_id")["maintenance_id"]
        .count()
    )

    pipelines["maintenance_count"] = (
        pipelines["pipeline_id"]
        .map(maintenance_counts)
        .fillna(0)
        .astype(int)
    )

    return pipelines


# ============================================================
# BUILDINGS WITHIN 100 METERS
# ============================================================

def calculate_nearby_buildings(
    pipelines,
    buildings,
    distance=BUILDING_DISTANCE_METERS
):
    """
    Count buildings within the specified distance
    from every pipeline.

    Uses GeoPandas' dwithin spatial predicate so the
    calculation matches PostGIS ST_DWithin as closely
    as possible.
    """

    pipelines = pipelines.copy()

    if buildings.empty:

        pipelines["python_buildings_within_100m"] = 0

        return pipelines

    # Perform a direct distance-based spatial join.
    # This corresponds to the logic used by
    # PostGIS ST_DWithin.
    nearby_buildings = gpd.sjoin(
        buildings[
            [
                "building_id",
                "geom"
            ]
        ],
        pipelines[
            [
                "pipeline_id",
                "asset_code",
                "geom"
            ]
        ],
        how="inner",
        predicate="dwithin",
        distance=distance
    )

    building_counts = (
        nearby_buildings
        .groupby("pipeline_id")["building_id"]
        .nunique()
    )

    pipelines["python_buildings_within_100m"] = (
        pipelines["pipeline_id"]
        .map(building_counts)
        .fillna(0)
        .astype(int)
    )

    return pipelines


# ============================================================
# FLOOD EXPOSURE
# ============================================================

def calculate_flood_exposure(pipelines, risk_zones):
    """
    Calculate how much of every pipeline lies inside
    flood-risk zones.

    Produces:
        flood_length_m
        python_flood_exposure_percent
    """

    pipelines = pipelines.copy()

    if risk_zones.empty:

        pipelines["flood_length_m"] = 0.0
        pipelines["python_flood_exposure_percent"] = 0.0

        return pipelines

    # Combine all flood polygons into one geometry.
    flood_area = risk_zones.geometry.union_all()

    def calculate_single_pipeline(geometry):

        total_length = geometry.length

        if total_length == 0:
            return 0.0, 0.0

        intersection = geometry.intersection(flood_area)

        flood_length = intersection.length

        flood_percent = (
            flood_length
            / total_length
            * 100
        )

        return flood_length, flood_percent

    flood_results = pipelines.geometry.apply(
        calculate_single_pipeline
    )

    pipelines["flood_length_m"] = flood_results.apply(
        lambda result: result[0]
    )

    pipelines["python_flood_exposure_percent"] = (
        flood_results.apply(
            lambda result: result[1]
        )
    )

    return pipelines


# ============================================================
# PIPELINE AGE
# ============================================================

def calculate_pipeline_age(pipelines, current_date):
    """
    Calculate pipeline age from installation year.
    """

    pipelines = pipelines.copy()

    current_year = current_date.year

    pipelines["python_age_years"] = (
        current_year
        - pipelines["installation_year"]
    )

    return pipelines


# ============================================================
# DAYS SINCE LAST INSPECTION
# ============================================================

def calculate_inspection_age(pipelines, current_date):
    """
    Calculate number of days since each pipeline's
    last inspection.
    """

    pipelines = pipelines.copy()

    pipelines["last_inspection"] = pd.to_datetime(
        pipelines["last_inspection"]
    )

    pipelines["python_days_since_last_inspection"] = (
        current_date
        - pipelines["last_inspection"]
    ).dt.days

    return pipelines


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_required_risk_inputs(pipelines):
    """
    Ensure that all fields needed by the risk model
    contain valid values.
    """

    required_columns = [
        "python_age_years",
        "python_days_since_last_inspection",
        "python_failure_count",
        "python_buildings_within_100m",
        "python_flood_exposure_percent"
    ]

    missing_values = pipelines[
        required_columns
    ].isna().any()

    problematic_columns = (
        missing_values[
            missing_values
        ]
        .index
        .tolist()
    )

    if problematic_columns:

        raise ValueError(
            "Missing risk input values in columns: "
            + ", ".join(problematic_columns)
        )


# ============================================================
# RISK CALCULATION
# ============================================================

def calculate_all_risk_scores(pipelines):
    """
    Calculate risk scores and risk levels for every pipeline.
    """

    pipelines = pipelines.copy()

    risk_results = pipelines.apply(
        lambda row: calculate_risk_score(
            age_years=int(
                row["python_age_years"]
            ),
            days_since_last_inspection=int(
                row[
                    "python_days_since_last_inspection"
                ]
            ),
            failure_count=int(
                row["python_failure_count"]
            ),
            buildings_within_100m=int(
                row[
                    "python_buildings_within_100m"
                ]
            ),
            flood_exposure_percent=float(
                row[
                    "python_flood_exposure_percent"
                ]
            )
        ),
        axis=1
    )

    pipelines["python_risk_score"] = (
        risk_results.apply(
            lambda result: result[0]
        )
    )

    pipelines["python_risk_level"] = (
        risk_results.apply(
            lambda result: result[1]
        )
    )

    return pipelines


# ============================================================
# PYTHON VS POSTGIS VALIDATION
# ============================================================

def validate_against_postgis(
    pipelines,
    postgis_risk_map
):
    """
    Compare Python calculations with the PostGIS
    risk-assessment view.

    This demonstrates that the same analytical logic
    produces consistent results in both environments.
    """

    db_results = postgis_risk_map[
        [
            "pipeline_id",
            "age_years",
            "days_since_last_inspection",
            "failure_count",
            "buildings_within_100m",
            "flood_exposure_percent",
            "risk_score",
            "risk_level"
        ]
    ].copy()

    db_results = db_results.rename(
        columns={
            "age_years":
                "db_age_years",

            "days_since_last_inspection":
                "db_days_since_last_inspection",

            "failure_count":
                "db_failure_count",

            "buildings_within_100m":
                "db_buildings_within_100m",

            "flood_exposure_percent":
                "db_flood_exposure_percent",

            "risk_score":
                "db_risk_score",

            "risk_level":
                "db_risk_level"
        }
    )

    comparison = pipelines.merge(
        db_results,
        on="pipeline_id",
        how="left"
    )

    for _, row in comparison.iterrows():

        asset_code = row["asset_code"]

        # Pipeline age
        assert (
            int(row["python_age_years"])
            ==
            int(row["db_age_years"])
        ), (
            f"Age mismatch for {asset_code}"
        )

        # Inspection age
        assert (
            int(
                row[
                    "python_days_since_last_inspection"
                ]
            )
            ==
            int(
                row[
                    "db_days_since_last_inspection"
                ]
            )
        ), (
            f"Inspection age mismatch for {asset_code}"
        )

        # Failure count
        assert (
            int(row["python_failure_count"])
            ==
            int(row["db_failure_count"])
        ), (
            f"Failure count mismatch for {asset_code}"
        )

        # Nearby buildings
        assert (
            int(
                row[
                    "python_buildings_within_100m"
                ]
            )
            ==
            int(
                row[
                    "db_buildings_within_100m"
                ]
            )
        ), (
            f"Building count mismatch for {asset_code}"
        )

        # Flood exposure
        assert math.isclose(
            float(
                row[
                    "python_flood_exposure_percent"
                ]
            ),
            float(
                row[
                    "db_flood_exposure_percent"
                ]
            ),
            abs_tol=0.01
        ), (
            f"Flood exposure mismatch for {asset_code}"
        )

        # Risk score
        assert math.isclose(
            float(row["python_risk_score"]),
            float(row["db_risk_score"]),
            abs_tol=0.01
        ), (
            f"Risk score mismatch for {asset_code}"
        )

        # Risk category
        assert (
            row["python_risk_level"]
            ==
            row["db_risk_level"]
        ), (
            f"Risk level mismatch for {asset_code}"
        )

    print()
    print(
        "Validation successful:"
    )

    print(
        "Python and PostGIS risk results match."
    )


# ============================================================
# REPORT RESULTS
# ============================================================

def print_pipeline_report(pipelines):
    """
    Display a readable summary of the pipeline
    analysis.
    """

    report_columns = [
        "asset_code",
        "material",
        "diameter_mm",
        "installation_year",
        "length_m",
        "python_age_years",
        "python_days_since_last_inspection",
        "python_failure_count",
        "inspection_count",
        "maintenance_count",
        "python_buildings_within_100m",
        "flood_length_m",
        "python_flood_exposure_percent",
        "python_risk_score",
        "python_risk_level"
    ]

    report = pipelines[
        report_columns
    ].copy()

    report["length_m"] = (
        report["length_m"]
        .round(2)
    )

    report["flood_length_m"] = (
        report["flood_length_m"]
        .round(2)
    )

    report[
        "python_flood_exposure_percent"
    ] = (
        report[
            "python_flood_exposure_percent"
        ]
        .round(2)
    )

    print()
    print("=" * 80)

    print(
        "GEOASSET PIPELINE RISK REPORT"
    )

    print("=" * 80)

    print(report.to_string(index=False))

    print("=" * 80)


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    """
    Main execution workflow.
    """

    print()
    print(
        "GeoAsset Intelligence Platform"
    )

    print(
        "Pipeline Risk Analysis"
    )

    print("-" * 50)

    engine = create_database_engine()

    try:

        # ----------------------------------------------------
        # Load data
        # ----------------------------------------------------

        (
            pipelines,
            failures,
            buildings,
            risk_zones,
            postgis_risk_map
        ) = load_spatial_data(engine)

        (
            inspections,
            maintenance
        ) = load_attribute_data(engine)

        current_date = get_database_date(engine)

        print()
        print(
            f"Database date: "
            f"{current_date.date()}"
        )

        print(
            f"Pipelines loaded: "
            f"{len(pipelines)}"
        )

        print(
            f"Failures loaded: "
            f"{len(failures)}"
        )

        print(
            f"Buildings loaded: "
            f"{len(buildings)}"
        )

        print(
            f"Flood zones loaded: "
            f"{len(risk_zones)}"
        )

        # ----------------------------------------------------
        # CRS validation
        # ----------------------------------------------------

        validate_crs(
            pipelines,
            failures,
            buildings,
            risk_zones,
            postgis_risk_map
        )

        # ----------------------------------------------------
        # Spatial and asset calculations
        # ----------------------------------------------------

        pipelines = calculate_pipeline_lengths(
            pipelines
        )

        pipelines = calculate_failure_counts(
            pipelines,
            failures
        )

        pipelines = calculate_inspection_counts(
            pipelines,
            inspections
        )

        pipelines = calculate_maintenance_counts(
            pipelines,
            maintenance
        )

        pipelines = calculate_nearby_buildings(
            pipelines,
            buildings
        )

        pipelines = calculate_flood_exposure(
            pipelines,
            risk_zones
        )

        # ----------------------------------------------------
        # Time-based calculations
        # ----------------------------------------------------

        pipelines = calculate_pipeline_age(
            pipelines,
            current_date
        )

        pipelines = calculate_inspection_age(
            pipelines,
            current_date
        )

        # ----------------------------------------------------
        # Check risk inputs
        # ----------------------------------------------------

        validate_required_risk_inputs(
            pipelines
        )

        # ----------------------------------------------------
        # Risk assessment
        # ----------------------------------------------------

        pipelines = calculate_all_risk_scores(
            pipelines
        )

        # ----------------------------------------------------
        # Compare Python and PostGIS
        # ----------------------------------------------------

        validate_against_postgis(
            pipelines,
            postgis_risk_map
        )

        # ----------------------------------------------------
        # Final report
        # ----------------------------------------------------

        print_pipeline_report(
            pipelines
        )

        print()
        print(
            "GeoAsset analysis completed successfully."
        )

    finally:

        engine.dispose()

        print(
            "Database connection closed."
        )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()


# ============================================================
# FUTURE PROJECT SECTIONS
# ============================================================

# Future additions will include:
#
# 1. Automatic ETL pipeline for external GIS datasets
# 2. Importing real pipeline networks
# 3. Data-quality and geometry validation
# 4. Updating calculated risk results in PostGIS
# 5. Exporting reports to CSV / Excel / PDF
# 6. Automated testing with pytest
# 7. FastAPI geospatial REST API
# 8. Custom QGIS / PyQGIS plugin
# 9. GeoServer or QGIS Server
# 10. Docker deployment
# 11. GitHub Actions CI/CD