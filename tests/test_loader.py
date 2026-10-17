"""Tests for app/data_loader.py on tiny hand-written CSVs.

Run from the repo root:  python -m pytest tests/test_loader.py -q
"""

from datetime import date, datetime

import pytest

from app.data_loader import COLUMNS, filter_rush, load_station_status, rush_window

HEADER = ",".join(COLUMNS)
GOOD_ROWS = [
    "2026-09-14T07:00,S01,5,1,9",
    "2026-09-14T07:05,S01,4,1,10",
    "2026-09-14T07:00,S02,0,0,15",
]


def write(tmp_path, lines, name="status.csv"):
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_valid_file_loads_with_integer_counts(tmp_path):
    rows = load_station_status(write(tmp_path, [HEADER, *GOOD_ROWS]))
    assert len(rows) == 3
    first = rows[0]
    assert first["timestamp"] == datetime(2026, 9, 14, 7, 0)
    assert first["station_id"] == "S01"
    assert (first["num_bikes_available"], first["num_bikes_disabled"], first["num_docks_available"]) == (5, 1, 9)
    assert first["line"] == 2


def test_wrong_header_is_rejected(tmp_path):
    bad = "timestamp,station_id,bikes,broken,docks"
    with pytest.raises(ValueError, match="line 1: header must be"):
        load_station_status(write(tmp_path, [bad, *GOOD_ROWS]))


def test_columns_in_wrong_order_are_rejected(tmp_path):
    swapped = "station_id,timestamp,num_bikes_available,num_bikes_disabled,num_docks_available"
    with pytest.raises(ValueError, match="line 1"):
        load_station_status(write(tmp_path, [swapped, *GOOD_ROWS]))


def test_header_only_file_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="no data rows"):
        load_station_status(write(tmp_path, [HEADER]))


def test_missing_value_names_the_line(tmp_path):
    lines = [HEADER, GOOD_ROWS[0], "2026-09-14T07:05,S01,,1,10"]
    with pytest.raises(ValueError, match="line 3: num_bikes_available is missing"):
        load_station_status(write(tmp_path, lines))


def test_wrong_number_of_values_names_the_line(tmp_path):
    lines = [HEADER, GOOD_ROWS[0], "2026-09-14T07:05,S01,4,1"]
    with pytest.raises(ValueError, match="line 3: has 4 values, expected 5"):
        load_station_status(write(tmp_path, lines))


@pytest.mark.parametrize(
    "value, message",
    [
        ("-1", "counts cannot be negative"),
        ("3.5", "not a whole number"),
        ("abc", "not a number"),
    ],
)
def test_invalid_count_names_the_line(tmp_path, value, message):
    lines = [HEADER, GOOD_ROWS[0], f"2026-09-14T07:05,S01,4,{value},10"]
    with pytest.raises(ValueError, match=f"line 3: num_bikes_disabled is .*{message}"):
        load_station_status(write(tmp_path, lines))


@pytest.mark.parametrize("stamp", ["2026-09-14 07:00", "2026-9-14T07:00", "14/09/2026 07:00", "2026-02-30T07:00"])
def test_bad_timestamp_names_the_line(tmp_path, stamp):
    lines = [HEADER, f"{stamp},S01,5,1,9"]
    with pytest.raises(ValueError, match="line 2: timestamp"):
        load_station_status(write(tmp_path, lines))


def test_duplicate_snapshot_names_both_lines(tmp_path):
    lines = [HEADER, *GOOD_ROWS, "2026-09-14T07:05,S01,3,1,11"]
    with pytest.raises(ValueError, match=r"line 5: duplicates line 3 \(station S01 at 2026-09-14T07:05\)"):
        load_station_status(write(tmp_path, lines))


def test_missing_snapshots_are_allowed(tmp_path):
    # 07:10 and 07:15 were never logged: not an error, just fewer rows.
    lines = [HEADER, "2026-09-14T07:05,S01,4,1,10", "2026-09-14T07:20,S01,3,1,11"]
    assert len(load_station_status(write(tmp_path, lines))) == 2


@pytest.mark.parametrize(
    "stamp, window",
    [
        ("2026-09-14T06:55", None),
        ("2026-09-14T07:00", "AM"),
        ("2026-09-14T08:55", "AM"),
        ("2026-09-14T09:00", None),
        ("2026-09-14T12:00", None),
        ("2026-09-14T15:55", None),
        ("2026-09-14T16:00", "PM"),
        ("2026-09-14T17:55", "PM"),
        ("2026-09-14T18:00", None),
        ("2026-09-19T07:30", None),  # Saturday
        ("2026-09-20T16:30", None),  # Sunday
    ],
)
def test_rush_window_boundaries(stamp, window):
    assert rush_window(datetime.fromisoformat(stamp)) == window


def test_filter_rush_keeps_weekday_windows_and_tags_them(tmp_path):
    lines = [
        HEADER,
        "2026-09-14T06:55,S01,5,1,9",
        "2026-09-14T07:00,S01,5,1,9",
        "2026-09-14T09:00,S01,5,1,9",
        "2026-09-14T17:55,S01,5,1,9",
        "2026-09-19T07:00,S01,5,1,9",
    ]
    kept = filter_rush(load_station_status(write(tmp_path, lines)))
    assert [(r["line"], r["date"], r["window"]) for r in kept] == [
        (3, date(2026, 9, 14), "AM"),
        (5, date(2026, 9, 14), "PM"),
    ]
