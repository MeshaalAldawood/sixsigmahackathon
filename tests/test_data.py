"""Tests for the SYNTHETIC datasets in data/ (task H-02).

They check the files themselves (schema, counts, the shared baseline, exact
regeneration from the seed) and the planted signals, first by counting the raw
rows and then through the finished p-chart in app/qc.py. They never import the
availability or maintenance modules.

Run from the repo root:  python -m pytest tests/test_data.py -q
"""

import subprocess
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.data_loader import COLUMNS, filter_rush, load_dataset, rush_window
from app.qc import p_chart

DATA = Path(__file__).resolve().parent.parent / "data"
FILES = ["stable.csv", "planted_events.csv", "edge_case.csv"]
DAYS = [d for d in (date(2026, 9, 14) + timedelta(days=i) for i in range(19)) if d.weekday() < 5]
BASELINE, STADIUM_DAY, SURGE_DAYS = DAYS[:10], DAYS[11], DAYS[12:]
MAIN = [f"S{i:02d}" for i in range(1, 11)]
EDGE = ["E01", "E02"]
EDGE_SHORT = {("E02", DAYS[2], "AM"): 20, ("E02", DAYS[10], "PM"): 20}


@pytest.fixture(scope="module")
def data():
    return {name: filter_rush(load_dataset(DATA / name)) for name in FILES}


def unusable(r):
    return r["num_bikes_available"] == 0 or r["num_docks_available"] == 0


def groups(records):
    """(station, date, window) -> [d, n] for unusable snapshots."""
    out = {}
    for r in records:
        g = out.setdefault((r["station_id"], r["timestamp"].date(), rush_window(r["timestamp"])), [0, 0])
        g[0] += unusable(r)
        g[1] += 1
    return out


def station_chart(records, station, window):
    g = groups(records)
    pairs = [tuple(g[(station, d, window)]) for d in DAYS]
    return p_chart(pairs[:10], pairs)


def network_07(records):
    """One (broken, docked) pair per day from the 07:00 snapshots."""
    pairs = []
    for d in DAYS:
        at7 = [r for r in records if r["timestamp"].date() == d and r["timestamp"].strftime("%H:%M") == "07:00"]
        pairs.append((sum(r["num_bikes_disabled"] for r in at7),
                      sum(r["num_bikes_disabled"] + r["num_bikes_available"] for r in at7)))
    return pairs


def flags(chart):
    return [i + 1 for i, p in enumerate(chart["points"]) if p["flagged_high"] or p["flagged_low"]]


# ---- schema and checkpoint counts --------------------------------------------------

def test_calendar_is_fifteen_weekdays():
    assert len(DAYS) == 15 and DAYS[0] == date(2026, 9, 14) and DAYS[-1] == date(2026, 10, 2)


@pytest.mark.parametrize("name", FILES)
def test_exact_header(name):
    assert (DATA / name).read_text(encoding="utf-8").splitlines()[0] == ",".join(COLUMNS)


@pytest.mark.parametrize("name, rows", [("stable.csv", 7200), ("planted_events.csv", 7200), ("edge_case.csv", 1432)])
def test_row_counts_and_every_row_in_a_rush_window(name, rows):
    records = load_dataset(DATA / name)
    assert len(records) == rows  # 10 x 15 x 48; edge 2 x 15 x 48 - 8 missing
    assert len(filter_rush(records)) == rows


@pytest.mark.parametrize("name", ["stable.csv", "planted_events.csv"])
def test_main_files_have_24_snapshots_per_station_day_window(data, name):
    g = groups(data[name])
    assert set(g) == {(s, d, w) for s in MAIN for d in DAYS for w in ("AM", "PM")}
    assert {n for _, n in g.values()} == {24}


def test_edge_file_has_only_the_documented_missing_snapshots(data):
    g = groups(data["edge_case.csv"])
    assert set(g) == {(s, d, w) for s in EDGE for d in DAYS for w in ("AM", "PM")}
    assert {k: n for k, (_, n) in g.items() if n != 24} == EDGE_SHORT


@pytest.mark.parametrize("name", FILES)
def test_counts_add_up_to_a_fixed_capacity_per_station(data, name):
    capacity = {}
    for r in data[name]:
        total = r["num_bikes_available"] + r["num_bikes_disabled"] + r["num_docks_available"]
        assert capacity.setdefault(r["station_id"], total) == total


# ---- reproducibility and shared baseline ----------------------------------------------

def test_seeded_generator_reproduces_the_files_exactly(tmp_path):
    subprocess.run([sys.executable, str(DATA / "generate.py"), "--out", str(tmp_path)], check=True)
    for name in FILES:
        assert (tmp_path / name).read_bytes() == (DATA / name).read_bytes(), name


def test_planted_file_shares_the_baseline_and_differs_only_where_planted(data):
    stable = {(r["station_id"], r["timestamp"]): r for r in data["stable.csv"]}
    planted = {(r["station_id"], r["timestamp"]): r for r in data["planted_events.csv"]}
    assert stable.keys() == planted.keys()
    changed = [k for k in stable if stable[k] != planted[k]]
    assert changed
    for station, stamp in changed:
        in_stadium = station == "S08" and stamp.date() == STADIUM_DAY and rush_window(stamp) == "PM"
        assert in_stadium or stamp.date() in SURGE_DAYS, (station, stamp)


# ---- planted signals: raw counts, then the p-chart --------------------------------------

def test_stadium_day_fills_s08_for_most_of_the_pm_window(data):
    g = groups(data["planted_events.csv"])
    assert g[("S08", STADIUM_DAY, "PM")] == [22, 24]
    full = [r for r in data["planted_events.csv"] if r["station_id"] == "S08"
            and r["timestamp"].date() == STADIUM_DAY and rush_window(r["timestamp"]) == "PM"
            and r["num_docks_available"] == 0]
    assert len(full) == 22 and all(r["num_bikes_disabled"] == 0 for r in full)  # investigate, not collect


def test_stadium_day_flags_and_is_the_only_availability_flag(data):
    assert flags(station_chart(data["planted_events.csv"], "S08", "PM")) == [12]
    others = [(s, w, flags(station_chart(data["planted_events.csv"], s, w)))
              for s in MAIN for w in ("AM", "PM") if (s, w) != ("S08", "PM")]
    assert all(f == [] for _, _, f in others), others


def test_maintenance_network_is_200_bikes_and_the_surge_flags(data):
    stable, planted = network_07(data["stable.csv"]), network_07(data["planted_events.csv"])
    assert {n for _, n in stable + planted} == {200}
    assert [d for d, _ in planted[:12]] == [d for d, _ in stable[:12]]
    assert sum(d for d, _ in stable[:10]) == 200  # p_bar = 200 / 2000 = 0.10
    assert [d for d, _ in planted[12:]] == [2 * d for d, _ in stable[12:]] == [40, 38, 42]
    chart = p_chart(planted[:10], planted)
    assert chart["p_bar"] == pytest.approx(0.10)
    assert chart["points"][0]["upper_count"] == 34
    assert flags(chart) == [13, 14, 15]
    assert all(p["flagged_high"] for p in chart["points"][12:])


def test_stable_file_has_no_flags_at_all(data):
    for s in MAIN:
        for w in ("AM", "PM"):
            assert flags(station_chart(data["stable.csv"], s, w)) == [], (s, w)
    stable = network_07(data["stable.csv"])
    assert flags(p_chart(stable[:10], stable)) == []


# ---- station behavior -------------------------------------------------------------------

def count(records, stations, window, test):
    return sum(test(r) for r in records if r["station_id"] in stations and rush_window(r["timestamp"]) == window)


def empty(r):
    return r["num_bikes_available"] == 0


def full(r):
    return r["num_docks_available"] == 0


def test_residential_and_downtown_rush_patterns_are_opposite(data):
    recs, res, down = data["stable.csv"], {"S01", "S02", "S03"}, {"S04", "S05", "S06"}
    assert count(recs, res, "AM", empty) > 0 and count(recs, res, "AM", full) == 0
    assert count(recs, res, "PM", full) > 0 and count(recs, res, "PM", empty) == 0
    assert count(recs, down, "AM", full) > 0 and count(recs, down, "AM", empty) == 0
    assert count(recs, down, "PM", empty) > 0 and count(recs, down, "PM", full) == 0


def test_hilltop_is_above_target_but_in_control(data):
    chart = station_chart(data["stable.csv"], "S07", "AM")
    assert chart["p_bar"] == pytest.approx(63 / 240)  # 0.2625 > the 0.10 target
    assert flags(chart) == [] and all(p["status"] == "ok" for p in chart["points"])


def test_edge_e01_is_always_usable_so_it_has_no_limits(data):
    recs = data["edge_case.csv"]
    assert not any(unusable(r) for r in recs if r["station_id"] == "E01")
    for w in ("AM", "PM"):
        chart = station_chart(recs, "E01", w)
        assert chart["p_bar"] == 0 and {p["status"] for p in chart["points"]} == {"insufficient_basis"}


def test_edge_e02_short_days_get_wider_limits(data):
    chart = station_chart(data["edge_case.csv"], "E02", "AM")
    short, full_day = chart["points"][2], chart["points"][0]
    assert short["n"] == 20 and full_day["n"] == 24
    assert short["ucl"] > full_day["ucl"]
