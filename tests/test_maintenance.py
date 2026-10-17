"""Known answer and missing-data checks for the morning maintenance report."""

from datetime import datetime, timedelta

import pytest

from app.maintenance import build_maintenance


MONDAY = datetime(2026, 10, 5, 7)
BASELINE = [(MONDAY + timedelta(days=offset)).date() for offset in
            (0, 1, 2, 3, 4, 7, 8, 9, 10, 11)]


def row(day, station, available, disabled, *, hour=7, minute=0):
    return {
        "timestamp": datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute),
        "station_id": station,
        "num_bikes_available": available,
        "num_bikes_disabled": disabled,
        "num_docks_available": 20,
    }


def baseline_rows():
    return [row(day, "A", 90, 10) for day in BASELINE]


def test_exact_0700_network_sum_and_frozen_known_answer():
    latest = BASELINE[-1] + timedelta(days=3)
    records = baseline_rows() + [
        row(latest, "A", 40, 10),
        row(latest, "B", 35, 15),
        row(latest, "A", 0, 90, minute=5),
        row(latest, "C", 0, 100, hour=16),
    ]
    report = build_maintenance(records, BASELINE)
    assert report["as_of_date"] == latest.isoformat()
    assert report["chart"]["p_bar"] == pytest.approx(0.1)
    assert report["chart"]["baseline_dates"] == [day.isoformat() for day in BASELINE]
    point = report["chart"]["points"][-1]
    assert (point["d"], point["n"], point["p"]) == (25, 100, 0.25)
    assert (point["lower_count"], point["upper_count"]) == (2, 20)
    assert (point["lcl"], point["ucl"], point["status"]) == (0.02, 0.2, "high")
    assert point["flagged_high"]


def test_changing_broken_share_boundary_and_station_ordering():
    latest = BASELINE[-1] + timedelta(days=3)
    records = baseline_rows() + [
        row(latest, "Zulu", 44, 6), row(latest, "Beta", 6, 4),
        row(latest, "Alpha", 6, 4), row(latest, "None", 30, 0),
    ]
    report = build_maintenance(records, BASELINE)
    point = report["chart"]["points"][-1]
    assert (point["d"], point["n"], point["p"]) == (14, 100, 0.14)
    assert point["status"] == "in_control"
    assert [(station["station_id"], station["num_bikes_disabled"])
            for station in report["stations"]] == [
        ("Zulu", 6), ("Alpha", 4), ("Beta", 4)]
    assert {station["action"] for station in report["stations"]} == {
        "inspect and collect broken bikes"}


def test_two_hundred_bike_planted_shift_uses_its_own_exact_limit():
    latest = BASELINE[-1] + timedelta(days=3)
    report = build_maintenance(
        baseline_rows() + [row(latest, "A", 80, 20), row(latest, "B", 80, 20)],
        BASELINE,
    )
    point = report["chart"]["points"][-1]
    assert (point["d"], point["n"], point["upper_count"]) == (40, 200, 34)
    assert point["ucl"] == 34 / 200
    assert point["flagged_high"]


def test_no_exposure_and_missing_baseline_withhold_limits_and_future_dates():
    partial = baseline_rows()[:-1]
    current = BASELINE[-1] + timedelta(days=3)
    report = build_maintenance(partial + [row(current, "A", 0, 0)], BASELINE)
    assert report["chart"]["baseline_observed_days"] == 9
    assert report["chart"]["p_bar"] is None
    assert report["chart"]["points"][-1]["status"] == "no_data"
    assert report["chart"]["points"][-1]["p"] is None
    assert all(point["ucl"] is None for point in report["chart"]["points"])
    assert any("10 baseline weekdays" in warning for warning in report["warnings"])
    assert any("n=0" in warning for warning in report["warnings"])
    assert BASELINE[-1].isoformat() not in [point["date"] for point in report["chart"]["points"]]


@pytest.mark.parametrize("disabled", [0, 100])
def test_degenerate_baseline_has_no_limits(disabled):
    report = build_maintenance(
        [row(day, "A", 100 - disabled, disabled) for day in BASELINE], BASELINE
    )
    assert report["chart"]["p_bar"] == disabled / 100
    assert all(point["lcl"] is None and point["ucl"] is None
               for point in report["chart"]["points"])
    assert any("insufficient basis" in warning for warning in report["warnings"])


def test_duplicate_0700_station_is_rejected():
    with pytest.raises(ValueError, match="duplicate 07:00 snapshot"):
        build_maintenance([row(BASELINE[0], "A", 10, 1)] * 2, BASELINE)
