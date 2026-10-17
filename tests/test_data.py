"""Reproducibility and scenario checks for synthetic demonstration data."""

import csv
import importlib.util
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def day(row):
    return row["timestamp"][:10]


def window(row):
    return "AM" if int(row["timestamp"][11:13]) < 12 else "PM"


def test_exact_schema_size_and_shared_calibration():
    stable = rows("stable.csv")
    planted = rows("planted_events.csv")
    edge = rows("edge_case.csv")
    columns = ["timestamp", "station_id", "num_bikes_available",
               "num_bikes_disabled", "num_docks_available"]
    assert list(stable[0]) == columns
    assert list(planted[0]) == columns
    assert list(edge[0]) == columns
    assert len(stable) == len(planted) == 10 * 15 * 48 == 7200
    assert len(edge) == 2 * 15 * 48 - 4 == 1436
    dates = sorted({day(item) for item in stable})
    assert len(dates) == 15
    assert all(datetime.fromisoformat(value).weekday() < 5 for value in dates)
    assert [item for item in stable if day(item) in dates[:10]] == [
        item for item in planted if day(item) in dates[:10]]
    assert all(value.isdecimal() for item in stable + planted + edge
               for field, value in item.items() if field.startswith("num_"))


def test_scenarios_and_stable_counts():
    stable = rows("stable.csv")
    planted = rows("planted_events.csv")
    dates = sorted({day(item) for item in stable})
    assert dates[11] == "2026-10-20"  # day 12
    assert dates[12] == "2026-10-21"  # day 13
    station_window = defaultdict(lambda: [0, 0])
    for item in stable:
        key = (item["station_id"], day(item), window(item))
        if item["num_bikes_available"] == "0":
            station_window[key][0] += 1
        if item["num_docks_available"] == "0":
            station_window[key][1] += 1
    assert all(counts == [4, 0] for (station, _, hour), counts in
               station_window.items() if station == "hilltop_01" and hour == "AM")
    assert all(counts == [2, 0] for (station, _, hour), counts in
               station_window.items() if station.startswith("residential") and hour == "AM")
    assert all(counts == [0, 2] for (station, _, hour), counts in
               station_window.items() if station.startswith("downtown") and hour == "AM")
    assert all(counts == [0, 2] for (station, _, hour), counts in
               station_window.items() if station.startswith("residential") and hour == "PM")
    assert all(counts == [2, 0] for (station, _, hour), counts in
               station_window.items() if station.startswith("downtown") and hour == "PM")
    # Constant 2/24 (or hilltop 4/24) baseline subgroups yield zero
    # beyond-limit points, for any valid exact-binomial limits.
    assert all(len({sum(counts) for (station2, date, hour2), counts in
                    station_window.items() if station2 == station and
                    date in dates[:10] and hour2 == hour}) == 1
               for station in {item["station_id"] for item in stable}
               for hour in ("AM", "PM"))
    stadium = [item for item in planted if day(item) == dates[11] and
               item["station_id"] == "stadium_01" and
               window(item) == "PM"]
    assert sum(item["num_docks_available"] == "0" for item in stadium) == 18
    for index, expected_disabled in ((9, 20), (11, 20), (12, 40), (14, 40)):
        at_seven = [item for item in planted if day(item) == dates[index] and
                    item["timestamp"].endswith("T07:00")]
        assert len(at_seven) == 10
        assert sum(int(item["num_bikes_disabled"]) for item in at_seven) == expected_disabled
        assert sum(int(item["num_bikes_available"]) +
                   int(item["num_bikes_disabled"]) for item in at_seven) == 400
    assert planted[:10 * 10 * 48] == stable[:10 * 10 * 48]
    # Exact upper binomial tails establish that the two planted counts flag
    # against the frozen baseline, independent of the chart implementation.
    maintenance_tail = sum(math.comb(400, k) * .05**k * .95**(400-k)
                           for k in range(40, 401))
    stadium_tail = sum(math.comb(24, k) * (2/24)**k * (22/24)**(24-k)
                       for k in range(18, 25))
    assert maintenance_tail < .00135
    assert stadium_tail < .00135


def test_missing_snapshot_and_always_usable_edge_station():
    edge = rows("edge_case.csv")
    assert all(item["num_bikes_available"] != "0" and
               item["num_docks_available"] != "0" for item in edge
               if item["station_id"] == "edge_01")
    counts = Counter((day(item), item["station_id"], window(item))
                     for item in edge)
    assert counts[("2026-10-22", "edge_02", "AM")] == 20
    assert set(counts.values()) == {20, 24}


def test_regeneration_is_byte_identical(tmp_path):
    spec = importlib.util.spec_from_file_location("generate", DATA / "generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(tmp_path)
    for name in ("stable.csv", "planted_events.csv", "edge_case.csv"):
        assert (tmp_path / name).read_bytes() == (DATA / name).read_bytes()
