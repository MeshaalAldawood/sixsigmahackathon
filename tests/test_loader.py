"""Tests for app/data_loader.py on tiny hand-written CSVs.

Run from the repo root:  python -m pytest tests/test_loader.py -q
"""

from datetime import datetime

import pytest

from app.data_loader import COLUMNS, filter_rush, load_dataset, rush_window

HEADER = ",".join(COLUMNS)
GOOD_ROWS = [
    "2026-09-14T07:05,S01,4,1,10",
    "2026-09-14T07:00,S02,0,0,15",
    "2026-09-14T07:00,S01,5,1,9",
]


def write(tmp_path, lines, name="status.csv"):
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_valid_file_loads_with_exact_keys_and_integer_counts(tmp_path):
    records = load_dataset(write(tmp_path, [HEADER, *GOOD_ROWS]))
    assert len(records) == 3
    assert all(set(r) == set(COLUMNS) for r in records)
    first = records[0]
    assert first == {"timestamp": datetime(2026, 9, 14, 7, 0), "station_id": "S01",
                     "num_bikes_available": 5, "num_bikes_disabled": 1, "num_docks_available": 9}


def test_records_are_sorted_by_timestamp_then_station(tmp_path):
    records = load_dataset(write(tmp_path, [HEADER, *GOOD_ROWS]))
    assert [(r["timestamp"].strftime("%H:%M"), r["station_id"]) for r in records] == [
        ("07:00", "S01"), ("07:00", "S02"), ("07:05", "S01")]


@pytest.mark.parametrize("header", [
    "timestamp,station_id,bikes,broken,docks",
    "station_id,timestamp,num_bikes_available,num_bikes_disabled,num_docks_available",
    "timestamp,station_id,num_bikes_available,num_bikes_disabled",
])
def test_wrong_header_is_rejected(tmp_path, header):
    with pytest.raises(ValueError, match="row 1: header must be"):
        load_dataset(write(tmp_path, [header, *GOOD_ROWS]))


def test_empty_file_and_header_only_file_are_rejected(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="row 1"):
        load_dataset(empty)
    with pytest.raises(ValueError, match="no data rows"):
        load_dataset(write(tmp_path, [HEADER]))


@pytest.mark.parametrize("cell_row", [
    "2026-09-14T07:10,S01,,1,10",
    "2026-09-14T07:10,,4,1,10",
    ",S01,4,1,10",
])
def test_missing_value_names_the_row(tmp_path, cell_row):
    with pytest.raises(ValueError, match="row 3: .* is missing"):
        load_dataset(write(tmp_path, [HEADER, GOOD_ROWS[0], cell_row]))


def test_wrong_number_of_values_names_the_row(tmp_path):
    with pytest.raises(ValueError, match="row 3: has 4 values, expected 5"):
        load_dataset(write(tmp_path, [HEADER, GOOD_ROWS[0], "2026-09-14T07:10,S01,4,1"]))


@pytest.mark.parametrize("value, message", [
    ("-1", "counts cannot be negative"),
    ("3.5", "not a whole number"),
    ("2.0", "not a whole number"),
    ("abc", "not a number"),
])
def test_invalid_count_names_the_row(tmp_path, value, message):
    lines = [HEADER, GOOD_ROWS[0], f"2026-09-14T07:10,S01,4,{value},10"]
    with pytest.raises(ValueError, match=f"row 3: num_bikes_disabled is .*{message}"):
        load_dataset(write(tmp_path, lines))


@pytest.mark.parametrize("stamp", ["2026-09-14 07:00", "2026-9-14T07:00", "14/09/2026 07:00",
                                   "2026-02-30T07:00", "2026-09-14T25:00"])
def test_bad_timestamp_names_the_row(tmp_path, stamp):
    with pytest.raises(ValueError, match="row 2: timestamp"):
        load_dataset(write(tmp_path, [HEADER, f"{stamp},S01,5,1,9"]))


def test_duplicate_snapshot_names_both_rows(tmp_path):
    lines = [HEADER, *GOOD_ROWS, "2026-09-14T07:05,S01,3,1,11"]
    with pytest.raises(ValueError, match=r"row 5: duplicates row 2 \(station S01 at 2026-09-14T07:05\)"):
        load_dataset(write(tmp_path, lines))


def test_rows_are_validated_before_filtering(tmp_path):
    # A bad row outside every rush window (a Saturday at noon) still rejects the file.
    lines = [HEADER, GOOD_ROWS[0], "2026-09-19T12:00,S01,-2,1,10"]
    with pytest.raises(ValueError, match="row 3"):
        load_dataset(write(tmp_path, lines))


def test_missing_snapshots_are_allowed(tmp_path):
    lines = [HEADER, "2026-09-14T07:05,S01,4,1,10", "2026-09-14T07:20,S01,3,1,11"]
    assert len(load_dataset(write(tmp_path, lines))) == 2


@pytest.mark.parametrize("stamp, window", [
    ("2026-09-14T06:55", None), ("2026-09-14T07:00", "AM"), ("2026-09-14T08:55", "AM"),
    ("2026-09-14T09:00", None), ("2026-09-14T12:00", None), ("2026-09-14T15:55", None),
    ("2026-09-14T16:00", "PM"), ("2026-09-14T17:55", "PM"), ("2026-09-14T18:00", None),
    ("2026-09-19T07:30", None),  # Saturday
    ("2026-09-20T16:30", None),  # Sunday
])
def test_rush_window_boundaries(stamp, window):
    assert rush_window(datetime.fromisoformat(stamp)) == window


def test_filter_rush_keeps_weekday_windows_without_changing_records(tmp_path):
    lines = [HEADER] + [f"{s},S01,5,1,9" for s in (
        "2026-09-14T06:55", "2026-09-14T07:00", "2026-09-14T09:00", "2026-09-14T17:55", "2026-09-19T07:00")]
    records = load_dataset(write(tmp_path, lines))
    kept = filter_rush(records)
    assert [r["timestamp"].strftime("%Y-%m-%d %H:%M") for r in kept] == ["2026-09-14 07:00", "2026-09-14 17:55"]
    assert all(set(r) == set(COLUMNS) for r in kept)
    assert kept[0] is records[1]
