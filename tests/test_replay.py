"""Replay has a single source cutoff and cannot borrow future calibration."""

from datetime import date, datetime, timedelta

import pytest

from app.availability import build_availability
from app.maintenance import build_maintenance
from app.replay import parse_as_of, prepare_replay


BASE = date(2026, 1, 5)
DAYS = [BASE + timedelta(days=i) for i in range(22)
        if (BASE + timedelta(days=i)).weekday() < 5][:15]


def row(day, hour, minute, station="A", *, empty=False, disabled=1):
    return {
        "timestamp": datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute),
        "station_id": station,
        "num_bikes_available": 0 if empty else 9,
        "num_bikes_disabled": disabled,
        "num_docks_available": 10,
    }


def fixture():
    records = []
    for day in DAYS:
        for hour in (7, 8, 16, 17):
            for minute in range(0, 60, 5):
                records.append(row(day, hour, minute, empty=(hour == 7 and minute < 10)))
    return records


def reports(source, cutoff):
    replay = prepare_replay(source, cutoff)
    availability = build_availability(replay["records"], replay["baseline_dates"],
                                      as_of=cutoff, calibrated=replay["calibrated"])
    maintenance = build_maintenance(replay["records"], replay["baseline_dates"],
                                    as_of=cutoff, calibrated=replay["calibrated"])
    return replay, availability, maintenance


def test_cutoff_future_suffix_and_rewind():
    source = fixture()
    cutoff = datetime.combine(DAYS[10], datetime.min.time()).replace(hour=8, minute=55)
    replay, availability, maintenance = reports(source, cutoff)
    changed = [dict(record, num_bikes_available=0, num_bikes_disabled=9)
               if record["timestamp"] > cutoff else record for record in source]
    again, a2, m2 = reports(changed, cutoff)
    assert replay["records"] == again["records"]
    assert replay["station_status"] == again["station_status"]
    assert availability == a2 and maintenance == m2
    assert replay["baseline_dates"] == DAYS[:10]
    assert availability["AM"]["stations"][0]["provisional"]
    assert availability["AM"]["stations"][0]["status"] == "provisional"
    assert availability["AM"]["stations"][0]["ucl"] is None
    assert availability["AM"]["stations"][0]["action"] == "provisional: rush window incomplete"
    assert availability["AM"]["stations"][0]["n"] == 24
    assert maintenance["measurement_timestamp"] == f"{DAYS[10]}T07:00"
    assert reports(source, datetime.combine(DAYS[5], datetime.min.time()).replace(hour=8))[0]["calibrated"] is False


@pytest.mark.parametrize("hour,minute,window,complete", [
    (8, 55, "AM", False), (9, 0, "AM", True),
    (17, 55, "PM", False), (18, 0, "PM", True),
])
def test_half_open_window_boundaries(hour, minute, window, complete):
    source = fixture()
    cutoff = datetime.combine(DAYS[10], datetime.min.time()).replace(hour=hour, minute=minute)
    _, availability, _ = reports(source, cutoff)
    assert availability[window]["window_complete"] is complete
    point = availability[window]["charts"]["A"]["points"][-1]
    assert point["window_complete"] is complete
    assert point["n"] == 24
    if complete and window == "AM":
        assert point["status"] == "in_control"
    elif not complete:
        assert point["status"] == "provisional"
        assert point["ucl"] is None


def test_tenth_baseline_day_waits_for_pm_close_and_no_onset_leak():
    source = fixture()
    just_before = datetime.combine(DAYS[9], datetime.min.time()).replace(hour=17, minute=55)
    replay, availability, maintenance = reports(source, just_before)
    assert replay["calibrated"] is False
    assert availability["AM"]["charts"]["A"]["p_bar"] is None
    assert availability["AM"]["charts"]["A"]["onset"]["empty"]["time"] is None
    assert maintenance["chart"]["p_bar"] is None
    at_close = reports(source, just_before.replace(hour=18, minute=0))
    assert at_close[0]["calibrated"] is True
    assert at_close[1]["AM"]["charts"]["A"]["p_bar"] == pytest.approx(2 / 24)
    assert at_close[2]["chart"]["p_bar"] == 1.0
    assert all(point["ucl"] is None for point in at_close[2]["chart"]["points"])


def test_missing_0700_and_stale_station_state():
    source = fixture()
    day = DAYS[10]
    source = [record for record in source if not (
        record["timestamp"].date() == day and record["timestamp"].hour == 7
        and record["timestamp"].minute == 0)]
    cutoff = datetime.combine(day, datetime.min.time()).replace(hour=7, minute=15)
    replay, _, maintenance = reports(source, cutoff)
    assert replay["station_status"][0]["observed_at"] == f"{day}T07:15"
    assert maintenance["measurement_timestamp"] == f"{DAYS[9]}T07:00"
    assert maintenance["stale"] is True
    assert any("no 07:00" in warning for warning in maintenance["warnings"])


def test_future_station_id_is_visible_only_as_missing_catalog_entry():
    source = fixture()
    source.append(row(DAYS[11], 7, 0, "future_station", empty=True, disabled=7))
    cutoff = datetime.combine(DAYS[10], datetime.min.time()).replace(hour=8, minute=0)
    replay, availability, maintenance = reports(source, cutoff)
    future = next(status for status in replay["station_status"]
                  if status["station_id"] == "future_station")
    assert future == {
        "station_id": "future_station", "observed_at": None,
        "age_minutes": None, "stale": True, "missing": True,
        "num_bikes_available": None, "num_bikes_disabled": None,
        "num_docks_available": None, "unusable": None,
    }
    assert replay["metadata"]["observed_station_count"] == 1
    assert replay["metadata"]["station_count"] == 2
    assert "future_station" not in availability["AM"]["charts"]
    assert all(station["station_id"] != "future_station" for station in maintenance["stations"])


def test_final_cutoff_parity_and_invalid_clock():
    source = fixture()
    historical = build_availability(source, DAYS[:10])
    replayed = reports(source, datetime.combine(DAYS[-1], datetime.min.time()).replace(hour=18))[1]
    assert historical["AM"]["charts"]["A"]["p_bar"] == replayed["AM"]["charts"]["A"]["p_bar"]
    assert [(p["d"], p["n"], p["ucl"], p["status"]) for p in historical["AM"]["charts"]["A"]["points"]] == [
        (p["d"], p["n"], p["ucl"], p["status"]) for p in replayed["AM"]["charts"]["A"]["points"]]
    with pytest.raises(ValueError, match="YYYY-MM-DDTHH:MM"):
        parse_as_of("2026-01-05")
