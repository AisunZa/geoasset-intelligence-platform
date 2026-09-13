from pathlib import Path

import osmnx as ox


# Center point near the current sample pipeline
CENTER_POINT = (50.1040678, 8.6818724)

# Search radius in meters
SEARCH_DISTANCE = 1500

# OpenStreetMap tags
TAGS = {
    "building": True
}


def main():
    print("Downloading OSM buildings...")

    buildings = ox.features_from_point(
        center_point=CENTER_POINT,
        tags=TAGS,
        dist=SEARCH_DISTANCE
    )

    print(f"Downloaded features: {len(buildings)}")

    # Keep polygon geometries only
    buildings = buildings[
        buildings.geometry.geom_type.isin(
            ["Polygon", "MultiPolygon"]
        )
    ].copy()

    print(
        f"Building polygons retained: {len(buildings)}"
    )

    # Project to the CRS used by our PostGIS project
    buildings = buildings.to_crs("EPSG:25832")

    # Create output path
    project_root = Path(__file__).resolve().parents[2]

    output_file = (
        project_root
        / "data"
        / "raw"
        / "osm_buildings.gpkg"
    )

    # Save as GeoPackage
    buildings.to_file(
        output_file,
        layer="buildings",
        driver="GPKG"
    )

    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()