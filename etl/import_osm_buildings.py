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
    # Locate downloaded GeoPackage
    # -----------------------------------------------------

    project_root = Path(__file__).resolve().parents[1]

    input_file = (
        project_root
        / "data"
        / "raw"
        / "osm_buildings.gpkg"
    )

    print(f"Reading: {input_file}")

    buildings = gpd.read_file(
        input_file,
        layer="buildings"
    )

    print(f"Buildings loaded: {len(buildings)}")

    # -----------------------------------------------------
    # Ensure correct CRS
    # -----------------------------------------------------

    if buildings.crs is None:
        raise ValueError("Building dataset has no CRS.")

    if buildings.crs.to_epsg() != 25832:
        buildings = buildings.to_crs(TARGET_CRS)

    print(f"CRS: {buildings.crs}")

    # -----------------------------------------------------
    # Keep only fields needed by our project
    # -----------------------------------------------------

    cleaned = gpd.GeoDataFrame(
        {
            "building_type": buildings.get(
                "building"
            ),
            "name": buildings.get(
                "name"
            ),
            "geom": buildings.geometry
        },
        geometry="geom",
        crs=TARGET_CRS
    )
    
    # Convert MultiPolygon buildings into individual Polygon features
    cleaned = cleaned.explode(
        index_parts=False,
        ignore_index=True
    )
    
    # Keep Polygon geometries only
    cleaned = cleaned[
        cleaned.geometry.geom_type == "Polygon"
    ].copy()

    cleaned["building_type"] = (
        cleaned["building_type"]
        .fillna("Unknown")
        .astype(str)
    )

    cleaned["name"] = (
        cleaned["name"]
        .fillna("Unnamed Building")
        .astype(str)
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
        # -------------------------------------------------
        # Replace sample building table with real OSM data
        # -------------------------------------------------
        
        with engine.begin() as connection:
        
            connection.execute(
                text(
                    "TRUNCATE TABLE buildings RESTART IDENTITY;"
                )
            )
        
            cleaned.to_postgis(
                name="buildings",
                con=connection,
                schema="public",
                if_exists="append",
                index=False,
                chunksize=1000
            )

        print()
        print(
            f"Imported {len(cleaned)} buildings "
            "into PostGIS."
        )

    finally:
        engine.dispose()

        print(
            "Database connection closed."
        )


if __name__ == "__main__":
    main()