"""Availability decisions use observed rush snapshots and frozen calibration dates."""

from datetime import date, datetime, timedelta

import pytest

from app.availability import build_availability


START = date(2026, 1, 5)
DATES = [START + timedelta(days=i) for i in range(20) if (START + timedelta(days=i)).weekday() < 5]


def row(day, minute, station="A", *, window="AM", empty=False, full=False, disabled=0):
    hour = 7 if window == "AM" else 16
    return {
        "timestamp": datetime.combine(day, datetime.min.time()).replace(hour=hour + minute // 60, minute=minute % 60),
        "station_id": station,
        "num_bikes_available": 0 if empty else 5,
        "num_bikes_disabled": disabled,
        "num_docks_available": 0 if full else 5,
    }


def fixture_counts(counts, *, station="A", window="AM", n=24):
    return [row(day, minute * 5, station, window=window, empty=minute < d)
            for day, d in zip(DATES, counts) for minute in range(n)]


def test_separate_am_pm_and_exact_limits_with_missing_snapshots():
    baseline = DATES[:10]
    records = fixture_counts([2, 4, 3, 3, 2, 4, 3, 3, 2, 4, 10])
    records += fixture_counts([0] * 11, window="PM")
    report = build_availability(records, baseline)
    am = report["AM"]
    pm = report["PM"]
    assert am["charts"]["A"]["p_bar"] == pytest.approx(30 / 240)
    point = am["charts"]["A"]["points"][-1]
    assert (point["d"], point["n"], point["upper_count"], point["ucl"]) == (10, 24, 9, .375)
    assert point["flagged_high"] is True
    assert am["stations"][0]["action"] == "investigate: special cause; van: drop bikes before 07:00"
    assert pm["charts"]["A"]["p_bar"] == 0
    assert pm["charts"]["A"]["points"][-1]["ucl"] is None
    assert "insufficient basis for control limits" in pm["charts"]["A"]["warnings"]

    # Explicitly remove the final four snapshots; the subgroup then has n=20.
    short = [r for r in records if not (r["timestamp"].date() == DATES[10] and
                                       r["timestamp"].hour == 8 and r["timestamp"].minute >= 40)]
    short_point = build_availability(short, baseline)["AM"]["charts"]["A"]["points"][-1]
    assert (short_point["d"], short_point["n"], short_point["upper_count"], short_point["ucl"]) == (10, 20, 8, .4)


def test_onset_median_uses_observed_baseline_denominator():
    baseline = DATES[:10]
    records = [row(day, 5) for day in baseline[:8]]
    records += [row(baseline[i], minute, empty=True) for i, minute in ((0, 35), (1, 40), (2, 50))]
    records += [row(DATES[10], 40, empty=True)]
    result = build_availability(records, baseline)["AM"]["stations"][0]
    onset = result["onset"]["empty"]
    assert onset["time"] == "07:40"
    assert onset["affected_days"] == 3
    assert onset["observed_days"] == 8
    assert onset["missing_days"] == 2
    assert onset["label"] == "07:40 on 3 of 8 observed days"


def test_half_minute_onset_floors_and_partial_baseline_warns():
    baseline = DATES[:10]
    records = fixture_counts([0] * 11)
    records = [record for record in records if not (
        record["timestamp"].date() in baseline[:2] and
        record["timestamp"].hour == 7 and record["timestamp"].minute == 40
    ) and not (
        record["timestamp"].date() == baseline[2] and
        record["timestamp"].hour == 8 and record["timestamp"].minute == 55
    )]
    records += [row(baseline[0], 40, empty=True), row(baseline[1], 41, empty=True)]
    chart = build_availability(records, baseline)["AM"]["charts"]["A"]
    onset = chart["onset"]["empty"]
    assert onset["time"] == "07:40"  # median is 07:40:30, floored to 07:40.
    assert (onset["affected_days"], onset["observed_days"], onset["missing_days"]) == (2, 10, 0)
    assert (onset["partial_days"], onset["observed_snapshots"], onset["expected_snapshots"]) == (1, 239, 240)
    assert "missing baseline snapshots may hide or delay first-unusable time" in chart["warnings"]


def test_action_precedence_chronic_and_tie_order():
    baseline = DATES[:10]
    records = fixture_counts([3] * 10 + [3], station="B")
    records += fixture_counts([3] * 10 + [3], station="A")
    report = build_availability(records, baseline)
    stations = report["AM"]["stations"]
    assert [s["station_id"] for s in stations] == ["A", "B"]
    assert all(s["action"] == "capacity review: unusable every day" for s in stations)
    assert all(not s["flagged_high"] for s in stations)
    records = [r for r in records if not (r["station_id"] == "B" and r["timestamp"].date() == DATES[10]
                                         and r["timestamp"].hour == 7 and r["timestamp"].minute == 55)]
    records.append(row(DATES[10], 55, "B", full=True, disabled=1))
    updated = build_availability(records, baseline)["AM"]["stations"]
    assert [s["station_id"] for s in updated] == ["A", "B"]  # actionable ties use station ID
    assert updated[1]["action"] == "collect broken bikes first"


def test_empty_full_direction_and_missing_current_group():
    baseline = DATES[:10]
    records = [row(day, 35, "A", empty=True) for day in baseline]
    records += [row(day, 40, "B", full=True) for day in baseline]
    records += [row(DATES[10], 35, "A", empty=True), row(DATES[10], 40, "B", full=True)]
    records += [row(DATES[11], 35, "A", empty=True)]
    report = build_availability(records, baseline)
    am = report["AM"]
    station_a, station_b = am["stations"]
    assert station_a["action"] == "van: drop bikes before 07:35"
    assert station_b["station_id"] == "B" and station_b["action"] == "no data"
    assert station_b["n"] == 0 and station_b["p"] is None and station_b["ucl"] is None
    assert station_b["date"] == DATES[11].isoformat()


def test_baseline_gate_and_degenerate_share():
    baseline = DATES[:10]
    records = fixture_counts([0] * 11)
    chart = build_availability(records, baseline)["AM"]["charts"]["A"]
    assert chart["p_bar"] == 0
    assert chart["points"][-1]["ucl"] is None
    assert "insufficient basis for control limits" in chart["warnings"]
    missing = [r for r in records if r["timestamp"].date() != baseline[0]]
    chart = build_availability(missing, baseline)["AM"]["charts"]["A"]
    assert chart["p_bar"] is not None
    assert chart["points"][-1]["ucl"] is None
    assert "insufficient basis for control limits" in chart["warnings"]
