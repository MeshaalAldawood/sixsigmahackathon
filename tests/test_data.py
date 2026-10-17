"""Tests for the SYNTHETIC datasets in data/ (task H-02).

These check the files themselves: schema, counts, the shared baseline, that the
seeded generator reproduces them exactly, and that the planted signals are in
the raw counts where data/README.md says they are. Whether the p-chart flags
them is tested with app/qc.py (task H-03), not here.

Run from the repo root:  python -m pytest tests/test_data.py -q
"""

import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.data_loader import COLUMNS, filter_rush, load_station_status

DATA = Path(__file__).resolve().parent.parent / "data"
FILES = ["stable.csv", "planted_events.csv", "edge_case.csv"]

# 15 weekdays, Mon 2026-09-14 to Fri 2026-10-02; days 1-10 are the baseline.
DAYS = [date(2026, 9, 14) + timedelta(days=d) for d in range(19) if (date(2026, 9, 14) + timedelta(days=d)).weekday() < 5]
BASELINE = DAYS[:10]
STADIUM_DAY = DAYS[11]  # day 12, Tue 2026-09-29
BROKEN_FROM = DAYS[12:]  # days 13-15, from Wed 2026-09-30
MAIN_STATIONS = [f"S{i:02d}" for i in range(1, 11)]
EDGE_MISSING = {("E02", DAYS[2], "AM"): 20, ("E02", DAYS[10], "PM"): 20}


def rows(name):
    return filter_rush(load_station_status(DATA / name))


@pytest.fixture(scope="module")
def stable():
    return rows("stable.csv")


@pytest.fixture(scope="module")
def planted():
    return rows("planted_events.csv")


@pytest.fixture(scope="module")
def edge():
    return rows("edge_case.csv")


def per_window(data, column_test):
    """(station, date, window) -> number of snapshots where column_test(row) is true."""
    out = Counter()
    for r in data:
        out[(r["station_id"], r["date"], r["window"])] += bool(column_test(r))
    return out


def empty(r):
    return r["num_bikes_available"] == 0


def full(r):
    return r["num_docks_available"] == 0


# ---- schema and counts --------------------------------------------------------

def test_calendar_is_fifteen_weekdays():
    assert len(DAYS) == 15 and DAYS[0] == date(2026, 9, 14) and DAYS[-1] == date(2026, 10, 2)


@pytest.mark.parametrize("name", FILES)
def test_exact_header(name):
    first_line = (DATA / name).read_text(encoding="utf-8").splitlines()[0]
    assert first_line == ",".join(COLUMNS)


@pytest.mark.parametrize("name, expected", [("stable.csv", 7200), ("planted_events.csv", 7200), ("edge_case.csv", 1432)])
def test_row_counts_and_every_row_is_in_a_rush_window(name, expected):
    loaded = load_station_status(DATA / name)
    assert len(loaded) == expected  # 10 x 15 x 48; edge 2 x 15 x 48 - 8 missing
    assert len(filter_rush(loaded)) == expected


@pytest.mark.parametrize("name", ["stable.csv", "planted_events.csv"])
def test_main_files_have_24_snapshots_per_station_day_window(name):
    counts = per_window(rows(name), lambda r: True)
    assert set(counts) == {(s, d, w) for s in MAIN_STATIONS for d in DAYS for w in ("AM", "PM")}
    assert set(counts.values()) == {24}


def test_edge_file_has_only_the_documented_missing_snapshots(edge):
    counts = per_window(edge, lambda r: True)
    assert set(counts) == {(s, d, w) for s in ("E01", "E02") for d in DAYS for w in ("AM", "PM")}
    short = {k: v for k, v in counts.items() if v != 24}
    assert short == EDGE_MISSING


@pytest.mark.parametrize("name", FILES)
def test_counts_add_up_to_a_fixed_capacity_per_station(name):
    capacity = defaultdict(set)
    for r in rows(name):
        capacity[r["station_id"]].add(
            r["num_bikes_available"] + r["num_bikes_disabled"] + r["num_docks_available"])
    assert all(len(c) == 1 for c in capacity.values()), capacity


# ---- reproducibility and the shared baseline ----------------------------------

def test_seeded_generator_reproduces_the_files_exactly(tmp_path):
    subprocess.run([sys.executable, str(DATA / "generate.py"), "--out", str(tmp_path)], check=True)
    for name in FILES:
        assert (tmp_path / name).read_bytes() == (DATA / name).read_bytes(), name


def test_planted_file_shares_the_stable_baseline_and_differs_only_where_planted(stable, planted):
    def key(r):
        return (r["station_id"], r["timestamp"])

    a = {key(r): r for r in stable}
    b = {key(r): r for r in planted}
    assert a.keys() == b.keys()
    changed = {k for k in a if a[k] != b[k]}
    for station, stamp in changed:
        stadium = station == "S08" and stamp.date() == STADIUM_DAY and stamp.hour >= 16
        assert stadium or stamp.date() in BROKEN_FROM, (station, stamp)
    assert not any(stamp.date() in BASELINE for _, stamp in changed)


# ---- planted signals ------------------------------------------------------------

def test_stadium_day_fills_s08_for_most_of_the_pm_window(stable, planted):
    planted_full = per_window(planted, full)
    assert planted_full[("S08", STADIUM_DAY, "PM")] >= 20
    assert all(planted_full[("S08", d, "PM")] <= 2 for d in BASELINE)
    assert per_window(stable, full)[("S08", STADIUM_DAY, "PM")] <= 2


def network_broken_share(data, days):
    broken = sum(r["num_bikes_disabled"] for r in data
                 if r["date"] in days and r["timestamp"].strftime("%H:%M") == "07:00")
    docked = sum(r["num_bikes_disabled"] + r["num_bikes_available"] for r in data
                 if r["date"] in days and r["timestamp"].strftime("%H:%M") == "07:00")
    return broken / docked


def test_broken_bike_share_doubles_from_day_13(stable, planted):
    base = network_broken_share(planted, BASELINE)
    assert 0.05 < base < 0.15
    assert 1.7 <= network_broken_share(planted, BROKEN_FROM) / base <= 2.3
    assert 0.7 <= network_broken_share(stable, BROKEN_FROM) / base <= 1.3


# ---- station behavior ------------------------------------------------------------

def total(data, stations, window, test):
    return sum(test(r) for r in data if r["station_id"] in stations and r["window"] == window)


def test_residential_and_downtown_rush_patterns_are_opposite(stable):
    residential, downtown = {"S01", "S02", "S03"}, {"S04", "S05", "S06"}
    assert total(stable, residential, "AM", empty) > total(stable, residential, "PM", empty)
    assert total(stable, residential, "PM", full) > total(stable, residential, "AM", full)
    assert total(stable, downtown, "AM", full) > total(stable, downtown, "PM", full)
    assert total(stable, downtown, "PM", empty) > total(stable, downtown, "AM", empty)


def test_hilltop_is_chronically_unusable_but_empties_every_baseline_morning(stable):
    unusable = per_window(stable, lambda r: empty(r) or full(r))
    share = sum(unusable[("S07", d, "AM")] for d in BASELINE) / (24 * len(BASELINE))
    assert share > 0.10  # above the service-level target every morning, on average
    assert all(unusable[("S07", d, "AM")] > 0 for d in BASELINE)


def test_edge_e01_is_always_usable(edge):
    e01 = [r for r in edge if r["station_id"] == "E01"]
    assert e01 and not any(empty(r) or full(r) for r in e01)
