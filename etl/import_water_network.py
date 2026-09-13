from pathlib import Path
from getpass import getpass

import geopandas as gpd
from sqlalchemy import create_engine, URL, text


DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "geoasset"
DB_USER = "postgres"

TARGET_CRS = "EPSG:25832"


def main():

    # -----------------------------------------------------
    # Locate generated water network
    # -----------------------------------------------------

    project_root = Path(__file__).resolve().parents[1]

    input_file = (
        project_root
        / "data"
        / "processed"
        / "synthetic_water_pipelines.gpkg"
    )

    print(f"Reading: {input_file}")

    pipelines = gpd.read_file(
        input_file,
        layer="pipelines"
    )

    print(
        f"Synthetic pipelines loaded: "
        f"{len(pipelines)}"
    )

    # -----------------------------------------------------
    # Validate CRS
    # -----------------------------------------------------

    if pipelines.crs is None:
        raise ValueError(
            "Pipeline dataset has no CRS."
        )

    if pipelines.crs.to_epsg() != 25832:
        pipelines = pipelines.to_crs(
            TARGET_CRS
        )

    print(f"CRS: {pipelines.crs}")

    # -----------------------------------------------------
    # Ensure LineString geometry
    # -----------------------------------------------------

    pipelines = pipelines.explode(
        index_parts=False,
        ignore_index=True
    )

    pipelines = pipelines[
        pipelines.geometry.geom_type
        == "LineString"
    ].copy()

    # -----------------------------------------------------
    # Rename geometry column to match PostGIS schema
    # -----------------------------------------------------

    if pipelines.geometry.name != "geom":
        pipelines = pipelines.rename_geometry(
            "geom"
        )

    # -----------------------------------------------------
    # Keep only database fields
    # -----------------------------------------------------

    pipelines = pipelines[
        [
            "asset_code",
            "material",
            "diameter_mm",
            "installation_year",
            "pressure_bar",
            "condition",
            "status",
            "last_inspection",
            "risk_score",
            "geom"
        ]
    ].copy()

    print(
        f"Pipelines ready for import: "
        f"{len(pipelines)}"
    )

    # -----------------------------------------------------
    # PostgreSQL connection
    # -----------------------------------------------------

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

        with engine.begin() as connection:

            # ---------------------------------------------
            # Remove old demo asset-related records
            #
            # Buildings and risk zones are NOT removed.
            # Database tables, indexes, and views remain.
            # ---------------------------------------------

            print()
            print(
                "Removing old demo pipeline records..."
            )

            connection.execute(
                text(
                    """
                    TRUNCATE TABLE
                        pipeline_failures,
                        inspections,
                        maintenance,
                        pipelines
                    RESTART IDENTITY;
                    """
                )
            )

            # ---------------------------------------------
            # Import generated pipeline network
            # ---------------------------------------------

            print(
                "Importing water network "
                "into PostGIS..."
            )

            pipelines.to_postgis(
                name="pipelines",
                con=connection,
                schema="public",
                if_exists="append",
                index=False,
                chunksize=500
            )

        print()
        print(
            f"Imported {len(pipelines)} "
            "pipeline segments into PostGIS."
        )

    finally:

        engine.dispose()

        print(
            "Database connection closed."
        )


if __name__ == "__main__":
    main()