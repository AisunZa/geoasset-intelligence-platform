from pathlib import Path

import osmnx as ox


CENTER_POINT = (50.1040678, 8.6818724)

SEARCH_DISTANCE = 2500


def main():
    print("Downloading OSM road network...")

    graph = ox.graph_from_point(
        center_point=CENTER_POINT,
        dist=SEARCH_DISTANCE,
        network_type="drive",
        simplify=True
    )

    nodes, edges = ox.graph_to_gdfs(graph)

    print(f"Road segments downloaded: {len(edges)}")

    # Project into our project CRS
    edges = edges.to_crs("EPSG:25832")

    # Keep only useful road attributes
    keep_columns = [
        column
        for column in [
            "name",
            "highway",
            "maxspeed",
            "geometry"
        ]
        if column in edges.columns
    ]

    roads = edges[keep_columns].copy()

    project_root = Path(__file__).resolve().parents[2]

    output_file = (
        project_root
        / "data"
        / "raw"
        / "osm_roads.gpkg"
    )

    roads.to_file(
        output_file,
        layer="roads",
        driver="GPKG"
    )

    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()