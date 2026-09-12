"""
Risk calculation module for the GeoAsset Intelligence Platform.

This module contains the reusable pipeline risk-scoring logic.
"""


def calculate_risk_score(
    age_years,
    days_since_last_inspection,
    failure_count,
    buildings_within_100m,
    flood_exposure_percent
):
    """
    Calculate a pipeline risk score from 0 to 100.

    Risk weights:
        Pipeline age:                25%
        Inspection recency:          10%
        Failure history:             30%
        Nearby buildings:            15%
        Flood exposure:              20%

    Returns
    -------
    tuple
        (risk_score, risk_level)
    """

    score = (
        min(age_years, 50) / 50.0 * 25
        + min(days_since_last_inspection, 365) / 365.0 * 10
        + min(failure_count, 3) / 3.0 * 30
        + min(buildings_within_100m, 10) / 10.0 * 15
        + min(flood_exposure_percent, 100) / 100.0 * 20
    )

    risk_score = round(score, 2)

    if risk_score <= 30:
        risk_level = "Low"

    elif risk_score <= 60:
        risk_level = "Medium"

    elif risk_score <= 80:
        risk_level = "High"

    else:
        risk_level = "Critical"

    return risk_score, risk_level