from pathlib import Path
from datetime import date, timedelta
import random

import geopandas as gpd
import pandas as pd


RANDOM_SEED = 42
REFERENCE_DATE = date(2026, 9, 13)

TARGET_CRS = "EPSG:25832"


def condition_score(condition):
    """
    Convert pipeline condition into a realistic
    inspection score range.
    """

    ranges = {
        "Good": (7, 10),
        "Fair": (4, 7),
        "Poor": (1, 4)
    }

    minimum, maximum = ranges.get(
        condition,
        (5, 8)
    )

    return random.randint(
        minimum,
        maximum
    )


def corrosion_level(condition):
    """
    Assign corrosion severity according to
    pipeline condition.
    """

    if condition == "Poor":
        return random.choices(
            ["High", "Medium", "Low"],
            weights=[55, 35, 10],
            k=1
        )[0]

    if condition == "Fair":
        return random.choices(
            ["High", "Medium", "Low"],
            weights=[15, 55, 30],
            k=1
        )[0]

    return random.choices(
        ["High", "Medium", "Low"],
        weights=[5, 20, 75],
        k=1
    )[0]


def failure_probability(age, condition):
    """
    Estimate annualized historical failure probability.

    This is synthetic portfolio data, not an
    engineering failure model.
    """

    probability = 0.03

    if age >= 50:
        probability += 0.20

    elif age >= 30:
        probability += 0.10

    if condition == "Poor":
        probability += 0.25

    elif condition == "Fair":
        probability += 0.10

    return min(
        probability,
        0.65
    )


def main():

    random.seed(RANDOM_SEED)

    project_root = (
        Path(__file__)
        .resolve()
        .parents[1]
    )

    pipeline_file = (
        project_root
        / "data"
        / "processed"
        / "synthetic_water_pipelines.gpkg"
    )

    output_directory = (
        project_root
        / "data"
        / "processed"
    )

    print(
        f"Reading pipeline network: "
        f"{pipeline_file}"
    )

    pipelines = gpd.read_file(
        pipeline_file,
        layer="pipelines"
    )

    if pipelines.crs is None:
        raise ValueError(
            "Pipeline dataset has no CRS."
        )

    if pipelines.crs.to_epsg() != 25832:
        pipelines = pipelines.to_crs(
            TARGET_CRS
        )

    print(
        f"Pipelines loaded: "
        f"{len(pipelines)}"
    )

    failure_records = []
    inspection_records = []
    maintenance_records = []

    # =====================================================
    # PROCESS EACH PIPELINE
    # =====================================================

    for _, pipeline in pipelines.iterrows():

        asset_code = pipeline[
            "asset_code"
        ]

        installation_year = int(
            pipeline[
                "installation_year"
            ]
        )

        condition = pipeline[
            "condition"
        ]

        pipeline_age = (
            REFERENCE_DATE.year
            - installation_year
        )

        last_inspection = pd.Timestamp(
            pipeline[
                "last_inspection"
            ]
        ).date()

        geometry = pipeline.geometry

        # =================================================
        # INSPECTION HISTORY
        # =================================================

        inspection_count = random.randint(
            1,
            4
        )

        # Latest inspection matches the date already
        # stored on the pipeline asset.
        inspection_dates = [
            last_inspection
        ]

        current_inspection_date = (
            last_inspection
        )

        for _ in range(
            inspection_count - 1
        ):

            current_inspection_date = (
                current_inspection_date
                - timedelta(
                    days=random.randint(
                        250,
                        500
                    )
                )
            )

            inspection_dates.append(
                current_inspection_date
            )

        inspection_dates.sort()

        for inspection_date in (
            inspection_dates
        ):

            score = condition_score(
                condition
            )

            corrosion = corrosion_level(
                condition
            )

            leakage_detected = (
                random.random()
                <
                (
                    0.30
                    if condition == "Poor"
                    else
                    0.10
                    if condition == "Fair"
                    else
                    0.03
                )
            )

            inspection_records.append(
                {
                    "asset_code":
                        asset_code,

                    "inspection_date":
                        inspection_date,

                    "inspector":
                        random.choice(
                            [
                                "Inspection Team A",
                                "Inspection Team B",
                                "Inspection Team C"
                            ]
                        ),

                    "condition_score":
                        score,

                    "corrosion_level":
                        corrosion,

                    "leakage_detected":
                        leakage_detected,

                    "notes":
                        (
                            "Routine pipeline "
                            "condition inspection."
                        )
                }
            )

        # =================================================
        # FAILURE HISTORY
        # =================================================

        probability = failure_probability(
            pipeline_age,
            condition
        )

        # Simulate up to 3 historical failure events.
        failure_count = 0

        for _ in range(3):

            if (
                random.random()
                < probability
            ):

                failure_count += 1

                days_ago = random.randint(
                    30,
                    1800
                )

                failure_date = (
                    REFERENCE_DATE
                    - timedelta(
                        days=days_ago
                    )
                )

                failure_type = (
                    random.choices(
                        [
                            "Leak",
                            "Burst",
                            "Corrosion",
                            "Joint Failure"
                        ],
                        weights=[
                            45,
                            15,
                            25,
                            15
                        ],
                        k=1
                    )[0]
                )

                severity = (
                    random.choices(
                        [
                            "Low",
                            "Medium",
                            "High"
                        ],
                        weights=[
                            35,
                            45,
                            20
                        ],
                        k=1
                    )[0]
                )

                # Create failure point somewhere
                # along the pipeline geometry.
                position = random.random()

                failure_point = (
                    geometry.interpolate(
                        position,
                        normalized=True
                    )
                )

                repair_cost_ranges = {
                    "Low":
                        (500, 3000),

                    "Medium":
                        (3000, 12000),

                    "High":
                        (12000, 40000)
                }

                minimum_cost, maximum_cost = (
                    repair_cost_ranges[
                        severity
                    ]
                )

                repair_cost = round(
                    random.uniform(
                        minimum_cost,
                        maximum_cost
                    ),
                    2
                )

                failure_records.append(
                    {
                        "asset_code":
                            asset_code,

                        "failure_date":
                            failure_date,

                        "failure_type":
                            failure_type,

                        "severity":
                            severity,

                        "description":
                            (
                                f"Synthetic "
                                f"{failure_type.lower()} "
                                f"event."
                            ),

                        "repair_cost":
                            repair_cost,

                        "geom":
                            failure_point
                    }
                )

                # =========================================
                # MAINTENANCE AFTER FAILURE
                # =========================================

                maintenance_date = (
                    failure_date
                    + timedelta(
                        days=random.randint(
                            1,
                            14
                        )
                    )
                )

                maintenance_records.append(
                    {
                        "asset_code":
                            asset_code,

                        "maintenance_date":
                            maintenance_date,

                        "maintenance_type":
                            (
                                f"{failure_type} Repair"
                            ),

                        "cost":
                            repair_cost,

                        "description":
                            (
                                "Corrective maintenance "
                                "performed following "
                                "pipeline failure."
                            )
                    }
                )

        # =================================================
        # OPTIONAL PREVENTIVE MAINTENANCE
        # =================================================

        if (
            failure_count == 0
            and random.random() < 0.20
        ):

            maintenance_date = (
                REFERENCE_DATE
                - timedelta(
                    days=random.randint(
                        30,
                        900
                    )
                )
            )

            cost = round(
                random.uniform(
                    300,
                    5000
                ),
                2
            )

            maintenance_records.append(
                {
                    "asset_code":
                        asset_code,

                    "maintenance_date":
                        maintenance_date,

                    "maintenance_type":
                        "Preventive Maintenance",

                    "cost":
                        cost,

                    "description":
                        (
                            "Scheduled preventive "
                            "pipeline maintenance."
                        )
                }
            )

    # =====================================================
    # CREATE FAILURE GEODATAFRAME
    # =====================================================

    failures = gpd.GeoDataFrame(
        failure_records,
        geometry="geom",
        crs=TARGET_CRS
    )

    inspections = pd.DataFrame(
        inspection_records
    )

    maintenance = pd.DataFrame(
        maintenance_records
    )

    # =====================================================
    # SAVE OUTPUTS
    # =====================================================

    failure_file = (
        output_directory
        / "synthetic_pipeline_failures.gpkg"
    )

    inspection_file = (
        output_directory
        / "synthetic_inspections.csv"
    )

    maintenance_file = (
        output_directory
        / "synthetic_maintenance.csv"
    )

    failures.to_file(
        failure_file,
        layer="failures",
        driver="GPKG"
    )

    inspections.to_csv(
        inspection_file,
        index=False
    )

    maintenance.to_csv(
        maintenance_file,
        index=False
    )

    # =====================================================
    # SUMMARY
    # =====================================================

    print()
    print(
        f"Failure records generated: "
        f"{len(failures)}"
    )

    print(
        f"Inspection records generated: "
        f"{len(inspections)}"
    )

    print(
        f"Maintenance records generated: "
        f"{len(maintenance)}"
    )

    print()
    print(
        f"Failures saved to: "
        f"{failure_file}"
    )

    print(
        f"Inspections saved to: "
        f"{inspection_file}"
    )

    print(
        f"Maintenance saved to: "
        f"{maintenance_file}"
    )

    print()
    print(
        "NOTE: Operational records are "
        "synthetic and generated for "
        "portfolio/demo purposes."
    )


if __name__ == "__main__":
    main()