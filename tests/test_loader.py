"""Input contract checks for the GBFS-shaped snapshot reader."""

import csv
from datetime import datetime

import pytest

from app.data_loader import COLUMNS, load_dataset


def write_rows(tmp_path, rows):
    path = tmp_path / "input.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    return path


def row(timestamp="2026-10-05T07:00", station="A", bikes="38",
        broken="2", docks="10"):
    return [timestamp, station, bikes, broken, docks]


def test_loader_parses_counts_and_keeps_missing_snapshots_missing(tmp_path):
    path = write_rows(tmp_path, [row(), row("2026-10-05T07:10")])
    result = load_dataset(path)
    assert len(result) == 2
    assert result[0]["timestamp"] == datetime(2026, 10, 5, 7)
    assert result[0]["num_bikes_disabled"] == 2


def test_loader_sorts_unsorted_source_rows(tmp_path):
    path = write_rows(tmp_path, [row("2026-10-05T07:10", "B"),
                                 row("2026-10-05T07:00", "B"),
                                 row("2026-10-05T07:00", "A")])
    assert [(item["timestamp"].strftime("%H:%M"), item["station_id"])
            for item in load_dataset(path)] == [("07:00", "A"), ("07:00", "B"), ("07:10", "B")]


def test_loader_filters_weekends_and_off_peak_after_validation(tmp_path):
    path = write_rows(tmp_path, [row(), row("2026-10-05T09:00"),
                                 row("2026-10-10T07:00"),
                                 row("2026-10-05T16:00")])
    assert [item["timestamp"].hour for item in load_dataset(path)] == [7, 16]


@pytest.mark.parametrize("bad,fragment", [
    (row(bikes="-1"), "num_bikes_available"),
    (row(broken="2.5"), "num_bikes_disabled"),
    (row(docks=""), "missing value"),
    (row(station=""), "missing value"),
    (row(timestamp="not-a-date"), "invalid timestamp"),
])
def test_invalid_values_name_source_row(tmp_path, bad, fragment):
    path = write_rows(tmp_path, [row(station="B"), bad])
    with pytest.raises(ValueError, match="row 3") as error:
        load_dataset(path)
    assert fragment in str(error.value)


def test_duplicate_station_and_time_names_source_row(tmp_path):
    path = write_rows(tmp_path, [row(), row()])
    with pytest.raises(ValueError, match="row 3: duplicate"):
        load_dataset(path)


def test_invalid_off_peak_row_is_still_rejected(tmp_path):
    path = write_rows(tmp_path, [row(), row("2026-10-05T12:00", bikes="-1")])
    with pytest.raises(ValueError, match="row 3"):
        load_dataset(path)


def test_header_must_match_exact_schema(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("timestamp,station_id,num_bikes_available\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row 1: expected columns"):
        load_dataset(path)
