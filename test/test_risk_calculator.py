from etl.risk_calculator import calculate_risk_score


def test_low_risk_pipeline():
    score, level = calculate_risk_score(
        age_years=5,
        days_since_last_inspection=30,
        failure_count=0,
        buildings_within_100m=1,
        flood_exposure_percent=0,
    )

    assert score <= 30
    assert level == "Low"


def test_medium_risk_pipeline():
    score, level = calculate_risk_score(
        age_years=25,
        days_since_last_inspection=180,
        failure_count=1,
        buildings_within_100m=5,
        flood_exposure_percent=20,
    )

    assert 30 < score <= 60
    assert level == "Medium"


def test_high_risk_pipeline():
    score, level = calculate_risk_score(
        age_years=45,
        days_since_last_inspection=365,
        failure_count=2,
        buildings_within_100m=10,
        flood_exposure_percent=20,
    )

    assert 60 < score <= 80
    assert level == "High"


def test_critical_risk_pipeline():
    score, level = calculate_risk_score(
        age_years=50,
        days_since_last_inspection=365,
        failure_count=3,
        buildings_within_100m=10,
        flood_exposure_percent=100,
    )

    assert score == 100.0
    assert level == "Critical"


def test_risk_inputs_are_capped():
    score, level = calculate_risk_score(
        age_years=100,
        days_since_last_inspection=1000,
        failure_count=10,
        buildings_within_100m=100,
        flood_exposure_percent=500,
    )

    assert score == 100.0
    assert level == "Critical"