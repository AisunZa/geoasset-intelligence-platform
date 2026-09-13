from pathlib import Path
from datetime import date, timedelta
import random

import geopandas as gpd


TARGET_CRS = "EPSG:25832"

# Makes the generated dataset reproducible
RANDOM_SEED = 42

# Number of synthetic pipeline segments to create
TARGET_PIPELINE_COUNT = 500

REFERENCE_DATE = date(2026, 9, 13)


def main():

    random.seed(RANDOM_SEED)

    project_root = Path(__file__).resolve().parents[1]

    input_file = (
        project_root
        / "data"
        / "raw"
        / "osm_roads.gpkg"
    )

    output_file = (
        project_root
        / "data"
        / "processed"
        / "synthetic_water_pipelines.gpkg"
    )

    print(f"Reading road network: {input_file}")

    roads = gpd.read_file(
        input_file,
        layer="roads"
    )

    print(f"Road segments loaded: {len(roads)}")

    # -----------------------------------------------------
    # CRS
    # -----------------------------------------------------

    if roads.crs is None:
        raise ValueError("Road dataset has no CRS.")

    if roads.crs.to_epsg() != 25832:
        roads = roads.to_crs(TARGET_CRS)

    # -----------------------------------------------------
    # Convert multipart roads into individual lines
    # -----------------------------------------------------

    roads = roads.explode(
        index_parts=False,
        ignore_index=True
    )

    roads = roads[
        roads.geometry.geom_type == "LineString"
    ].copy()

    # -----------------------------------------------------
    # Calculate road length
    # -----------------------------------------------------

    roads["length_m"] = roads.geometry.length

    # Remove extremely short or unusually long features
    roads = roads[
        (roads["length_m"] >= 30)
        & (roads["length_m"] <= 600)
    ].copy()

    # -----------------------------------------------------
    # Prefer typical urban streets
    # -----------------------------------------------------

    preferred_road_types = [
        "residential",
        "tertiary",
        "secondary",
        "primary",
        "unclassified",
        "living_street",
        "service"
    ]

    if "highway" in roads.columns:

        roads["highway_text"] = (
            roads["highway"]
            .fillna("")
            .astype(str)
            .str.lower()
        )

        mask = roads["highway_text"].apply(
            lambda value: any(
                road_type in value
                for road_type in preferred_road_types
            )
        )

        preferred = roads[mask].copy()

        if len(preferred) >= 100:
            roads = preferred

    print(
        f"Suitable urban road segments: {len(roads)}"
    )

    # -----------------------------------------------------
    # Select a manageable subset
    # -----------------------------------------------------

    sample_count = min(
        TARGET_PIPELINE_COUNT,
        len(roads)
    )

    pipelines = roads.sample(
        n=sample_count,
        random_state=RANDOM_SEED
    ).copy()

    pipelines = pipelines.reset_index(drop=True)

    # -----------------------------------------------------
    # Synthetic asset attributes
    # -----------------------------------------------------

    materials = [
        "Ductile Iron",
        "PVC",
        "Steel",
        "PE",
        "Cast Iron"
    ]

    material_weights = [
        30,
        25,
        15,
        20,
        10
    ]

    diameters = [
        80,
        100,
        150,
        200,
        250,
        300,
        400,
        500
    ]

    diameter_weights = [
        10,
        20,
        25,
        20,
        10,
        8,
        5,
        2
    ]

    pipeline_records = []

    for index, row in pipelines.iterrows():

        installation_year = random.randint(
            1965,
            2022
        )

        age = (
            REFERENCE_DATE.year
            - installation_year
        )

        material = random.choices(
            materials,
            weights=material_weights,
            k=1
        )[0]

        diameter_mm = random.choices(
            diameters,
            weights=diameter_weights,
            k=1
        )[0]

        pressure_bar = round(
            random.uniform(2.5, 8.0),
            2
        )

        # Older pipes are more likely to have
        # poorer condition ratings.
        if age >= 50:
            condition = random.choices(
                ["Poor", "Fair", "Good"],
                weights=[50, 35, 15],
                k=1
            )[0]

        elif age >= 30:
            condition = random.choices(
                ["Poor", "Fair", "Good"],
                weights=[20, 45, 35],
                k=1
            )[0]

        else:
            condition = random.choices(
                ["Poor", "Fair", "Good"],
                weights=[5, 25, 70],
                k=1
            )[0]

        days_since_inspection = random.randint(
            15,
            500
        )

        last_inspection = (
            REFERENCE_DATE
            - timedelta(
                days=days_since_inspection
            )
        )

        asset_code = (
            f"PIPE-{index + 1:05d}"
        )

        pipeline_records.append(
            {
                "asset_code": asset_code,
                "material": material,
                "diameter_mm": diameter_mm,
                "installation_year":
                    installation_year,
                "pressure_bar": pressure_bar,
                "condition": condition,
                "status": "Active",
                "last_inspection":
                    last_inspection,
                "risk_score": None,
                "geom": row.geometry
            }
        )

    # -----------------------------------------------------
    # Create GeoDataFrame
    # -----------------------------------------------------

    water_network = gpd.GeoDataFrame(
        pipeline_records,
        geometry="geom",
        crs=TARGET_CRS
    )

    # -----------------------------------------------------
    # Save result
    # -----------------------------------------------------

    water_network.to_file(
        output_file,
        layer="pipelines",
        driver="GPKG"
    )

    print()
    print(
        f"Synthetic pipelines created: "
        f"{len(water_network)}"
    )

    print(
        f"Saved to: {output_file}"
    )

    print()
    print(
        "NOTE: Pipeline geometries are derived "
        "from real OSM roads, while utility "
        "attributes are synthetic."
    )


if __name__ == "__main__":
    main()