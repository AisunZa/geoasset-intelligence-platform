from pathlib import Path

import osmnx as ox


# Same project area used for the building download
CENTER_POINT = (50.1040678, 8.6818724)

# Search a wider area because mapped pipelines are much sparser than buildings
SEARCH_DISTANCE = 5000

# Download features tagged as pipelines
TAGS = {
    "man_made": "pipeline"
}


def main():
    print("Downloading OSM pipeline features...")

    pipelines = ox.features_from_point(
        center_point=CENTER_POINT,
        tags=TAGS,
        dist=SEARCH_DISTANCE
    )

    print(f"Downloaded pipeline features: {len(pipelines)}")

    # Keep line geometries only
    pipelines = pipelines[
        pipelines.geometry.geom_type.isin(
            ["LineString", "MultiLineString"]
        )
    ].copy()

    print(
        f"Line pipeline features retained: {len(pipelines)}"
    )

    # Keep water pipelines when substance information exists.
    # Features without a substance tag are retained because
    # many OSM pipelines do not specify the transported material.
    if "substance" in pipelines.columns:
        pipelines = pipelines[
            pipelines["substance"].isna()
            | (pipelines["substance"] == "water")
        ].copy()

    print(
        f"Potential water/unspecified pipelines retained: {len(pipelines)}"
    )

    # Project into our PostGIS/QGIS CRS
    pipelines = pipelines.to_crs("EPSG:25832")

    project_root = Path(__file__).resolve().parents[2]

    output_file = (
        project_root
        / "data"
        / "raw"
        / "osm_pipelines.gpkg"
    )

    pipelines.to_file(
        output_file,
        layer="pipelines",
        driver="GPKG"
    )

    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()