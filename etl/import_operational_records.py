from pathlib import Path
from getpass import getpass

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, URL, text


DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "geoasset"
DB_USER = "postgres"

TARGET_CRS = "EPSG:25832"


def main():

    # =====================================================
    # FILE PATHS
    # =====================================================

    project_root = Path(__file__).resolve().parents[1]

    processed_dir = (
        project_root
        / "data"
        / "processed"
    )

    failure_file = (
        processed_dir
        / "synthetic_pipeline_failures.gpkg"
    )

    inspection_file = (
        processed_dir
        / "synthetic_inspections.csv"
    )

    maintenance_file = (
        processed_dir
        / "synthetic_maintenance.csv"
    )

    # =====================================================
    # LOAD GENERATED RECORDS
    # =====================================================

    print("Loading synthetic operational records...")

    failures = gpd.read_file(
        failure_file,
        layer="failures"
    )

    inspections = pd.read_csv(
        inspection_file
    )

    maintenance = pd.read_csv(
        maintenance_file
    )

    print(
        f"Failures loaded: {len(failures)}"
    )

    print(
        f"Inspections loaded: {len(inspections)}"
    )

    print(
        f"Maintenance records loaded: "
        f"{len(maintenance)}"
    )

    # =====================================================
    # CRS VALIDATION
    # =====================================================

    if failures.crs is None:
        raise ValueError(
            "Failure dataset has no CRS."
        )

    if failures.crs.to_epsg() != 25832:
        failures = failures.to_crs(
            TARGET_CRS
        )

    if failures.geometry.name != "geom":
        failures = failures.rename_geometry(
            "geom"
        )

    # =====================================================
    # DATABASE CONNECTION
    # =====================================================

    password = getpass(
        "PostgreSQL password: "
    )

    url = URL.create(
        "postgresql+psycopg",
        username=DB_USER,
        password=password,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

    engine = create_engine(url)

    try:

        # =================================================
        # GET PIPELINE ID MAPPING
        # =================================================

        pipeline_lookup = pd.read_sql(
            """
            SELECT
                pipeline_id,
                asset_code
            FROM pipelines
            """,
            engine
        )

        print()
        print(
            f"Pipelines found in PostGIS: "
            f"{len(pipeline_lookup)}"
        )

        # =================================================
        # MAP ASSET CODES TO PIPELINE IDS
        # =================================================

        failures = failures.merge(
            pipeline_lookup,
            on="asset_code",
            how="left"
        )

        inspections = inspections.merge(
            pipeline_lookup,
            on="asset_code",
            how="left"
        )

        maintenance = maintenance.merge(
            pipeline_lookup,
            on="asset_code",
            how="left"
        )

        # =================================================
        # VALIDATE MAPPINGS
        # =================================================

        datasets = {
            "failures": failures,
            "inspections": inspections,
            "maintenance": maintenance
        }

        for name, dataset in datasets.items():

            missing = (
                dataset["pipeline_id"]
                .isna()
                .sum()
            )

            if missing > 0:

                raise ValueError(
                    f"{missing} {name} records "
                    "could not be matched to "
                    "a pipeline."
                )

        print(
            "All operational records matched "
            "to pipeline IDs."
        )

        # =================================================
        # PREPARE FAILURE RECORDS
        # =================================================

        failure_import = failures[
            [
                "pipeline_id",
                "failure_date",
                "failure_type",
                "severity",
                "description",
                "repair_cost",
                "geom"
            ]
        ].copy()

        failure_import[
            "pipeline_id"
        ] = (
            failure_import[
                "pipeline_id"
            ]
            .astype(int)
        )

        failure_import[
            "failure_date"
        ] = pd.to_datetime(
            failure_import[
                "failure_date"
            ]
        ).dt.date

        # =================================================
        # PREPARE INSPECTION RECORDS
        # =================================================

        inspection_import = inspections[
            [
                "pipeline_id",
                "inspection_date",
                "inspector",
                "condition_score",
                "corrosion_level",
                "leakage_detected",
                "notes"
            ]
        ].copy()

        inspection_import[
            "pipeline_id"
        ] = (
            inspection_import[
                "pipeline_id"
            ]
            .astype(int)
        )

        inspection_import[
            "inspection_date"
        ] = pd.to_datetime(
            inspection_import[
                "inspection_date"
            ]
        ).dt.date

        # =================================================
        # PREPARE MAINTENANCE RECORDS
        # =================================================

        maintenance_import = maintenance[
            [
                "pipeline_id",
                "maintenance_date",
                "maintenance_type",
                "cost",
                "description"
            ]
        ].copy()

        maintenance_import[
            "pipeline_id"
        ] = (
            maintenance_import[
                "pipeline_id"
            ]
            .astype(int)
        )

        maintenance_import[
            "maintenance_date"
        ] = pd.to_datetime(
            maintenance_import[
                "maintenance_date"
            ]
        ).dt.date

        # =================================================
        # IMPORT INTO POSTGIS
        # =================================================

        with engine.begin() as connection:

            print()
            print(
                "Removing existing operational "
                "records..."
            )

            connection.execute(
                text(
                    """
                    TRUNCATE TABLE
                        pipeline_failures,
                        inspections,
                        maintenance
                    RESTART IDENTITY;
                    """
                )
            )

            print(
                "Importing failure records..."
            )

            failure_import.to_postgis(
                name="pipeline_failures",
                con=connection,
                schema="public",
                if_exists="append",
                index=False,
                chunksize=500
            )

            print(
                "Importing inspection records..."
            )

            inspection_import.to_sql(
                name="inspections",
                con=connection,
                schema="public",
                if_exists="append",
                index=False,
                chunksize=500,
                method="multi"
            )

            print(
                "Importing maintenance records..."
            )

            maintenance_import.to_sql(
                name="maintenance",
                con=connection,
                schema="public",
                if_exists="append",
                index=False,
                chunksize=500,
                method="multi"
            )

        # =================================================
        # SUMMARY
        # =================================================

        print()
        print(
            f"Imported {len(failure_import)} "
            "failure records."
        )

        print(
            f"Imported {len(inspection_import)} "
            "inspection records."
        )

        print(
            f"Imported {len(maintenance_import)} "
            "maintenance records."
        )

        print()
        print(
            "Operational records imported "
            "successfully."
        )

    finally:

        engine.dispose()

        print(
            "Database connection closed."
        )


if __name__ == "__main__":
    main()