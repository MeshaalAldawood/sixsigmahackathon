"""Generate the three SYNTHETIC test datasets in data/ (task H-02).

Run from the repo root:   python data/generate.py
Write somewhere else:     python data/generate.py --out <folder>

Nothing here is real. The files are built from FIXED INTEGER PATTERNS written
out below, so every chart result is designed, not luck:

  * UNUSABLE[station][window] lists, for each of the 15 weekdays, how many of
    the window's 24 snapshots are empty (residential AM, downtown PM, ...) or
    full. The station drains (or fills) in a straight line and becomes empty
    (or full) at snapshot 24 - d, then stays that way: d unusable snapshots.
  * BROKEN[station] is the number of broken bikes, constant all day.
  * DOCKED_AT_7[station] is the bikes docked at 07:00 (available + broken).
    These sum to 200 every day, so the maintenance chart has n = 200.

The random seed only adds a +/-1 wiggle to the bike counts strictly between
the start and the empty/full point; it can never create or remove an empty or
full snapshot. The same seed always writes byte-identical files.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261016

COLUMNS = ["timestamp", "station_id", "num_bikes_available", "num_bikes_disabled", "num_docks_available"]

FIRST_DAY = date(2026, 9, 14)  # Monday; 15 weekdays to Fri 2026-10-02
N_DAYS = 15
BASELINE_DAYS = 10
WINDOW_START = {"AM": (7, 0), "PM": (16, 0)}
STEPS = 24  # five-minute snapshots per window: 07:00-08:55, 16:00-17:55

# station: (type, capacity in docks)
STATIONS = {
    "S01": ("residential", 23), "S02": ("residential", 23), "S03": ("residential", 27),
    "S04": ("downtown", 31), "S05": ("downtown", 31), "S06": ("downtown", 27),
    "S07": ("hilltop", 15), "S08": ("stadium-downtown", 39),
    "S09": ("balanced", 19), "S10": ("balanced", 19),
}

# What goes wrong in each window: "empty" (bikes run out) or "full" (docks run out).
KIND = {
    "S01": {"AM": "empty", "PM": "full"}, "S02": {"AM": "empty", "PM": "full"},
    "S03": {"AM": "empty", "PM": "full"},
    "S04": {"AM": "full", "PM": "empty"}, "S05": {"AM": "full", "PM": "empty"},
    "S06": {"AM": "full", "PM": "empty"},
    "S07": {"AM": "empty", "PM": "empty"}, "S08": {"AM": "full", "PM": "empty"},
    "S09": {"AM": "empty", "PM": "full"}, "S10": {"AM": "full", "PM": "empty"},
}

# Unusable snapshots (of 24) on days 1-15. Days 1-10 are the baseline.
UNUSABLE = {
    "S01": {"AM": [1, 2, 0, 3, 1, 2, 0, 1, 2, 1, 2, 0, 1, 3, 1], "PM": [0, 1, 2, 0, 1, 1, 0, 2, 1, 0, 1, 0, 2, 1, 0]},
    "S02": {"AM": [2, 1, 1, 0, 2, 3, 1, 0, 1, 2, 1, 2, 0, 1, 2], "PM": [1, 0, 0, 2, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 2]},
    "S03": {"AM": [0, 1, 2, 1, 0, 1, 3, 1, 0, 2, 1, 1, 0, 2, 1], "PM": [1, 1, 0, 1, 2, 0, 1, 0, 2, 1, 1, 0, 1, 1, 0]},
    "S04": {"AM": [2, 3, 1, 2, 4, 2, 1, 3, 2, 2, 3, 2, 1, 2, 3], "PM": [1, 0, 2, 1, 1, 0, 2, 1, 0, 1, 1, 2, 0, 1, 1]},
    "S05": {"AM": [1, 2, 2, 3, 1, 2, 3, 1, 2, 1, 2, 1, 3, 2, 2], "PM": [0, 1, 1, 2, 0, 1, 1, 0, 2, 1, 0, 1, 1, 2, 0]},
    "S06": {"AM": [3, 2, 2, 1, 3, 4, 2, 2, 3, 2, 2, 3, 2, 1, 3], "PM": [2, 1, 1, 0, 2, 1, 2, 1, 1, 0, 1, 2, 1, 1, 2]},
    "S07": {"AM": [6, 7, 5, 8, 6, 7, 6, 5, 7, 6, 7, 6, 8, 6, 7], "PM": [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0]},
    "S08": {"AM": [1, 0, 2, 1, 1, 0, 1, 2, 1, 1, 0, 1, 2, 1, 1], "PM": [1, 1, 0, 2, 1, 1, 0, 1, 2, 1, 1, 1, 1, 0, 1]},
    "S09": {"AM": [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1], "PM": [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0]},
    "S10": {"AM": [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0], "PM": [0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1]},
}

# Broken bikes per station on a normal day (sum 20), plus a daily change at S09.
BROKEN = {"S01": 3, "S02": 2, "S03": 3, "S04": 0, "S05": 2, "S06": 0, "S07": 1, "S08": 0, "S09": 4, "S10": 5}
S09_BROKEN_CHANGE = [0, -1, 1, 0, 2, -2, 0, 1, -1, 0, 0, 1, 0, -1, 1]  # sums to 0 over the baseline
DOCKED_AT_7 = {"S01": 20, "S02": 19, "S03": 24, "S04": 21, "S05": 22, "S06": 18,
               "S07": 12, "S08": 32, "S09": 15, "S10": 17}  # sums to 200
PM_START_BIKES = {"S01": 12, "S02": 12, "S03": 14, "S04": 16, "S05": 15, "S06": 14,
                  "S07": 6, "S08": 18, "S09": 8, "S10": 7}

# Planted signals (planted_events.csv only).
STADIUM_STATION, STADIUM_DAY, STADIUM_FULL_FROM = "S08", 12, 2  # full from 16:10 on day 12
BROKEN_DOUBLES_FROM = 13  # days 13-15: every station's broken bikes double, n stays 200

# edge_case.csv
EDGE_STATIONS = {"E01": ("always-usable", 31), "E02": ("residential", 23)}
EDGE_KIND = {"E01": {"AM": None, "PM": None}, "E02": {"AM": "empty", "PM": "full"}}
EDGE_UNUSABLE = {
    "E01": {"AM": [0] * 15, "PM": [0] * 15},
    "E02": {"AM": [2, 1, 3, 0, 2, 1, 2, 3, 1, 2, 1, 2, 0, 3, 1], "PM": [1, 2, 0, 1, 2, 1, 0, 2, 1, 1, 2, 1, 1, 0, 2]},
}
EDGE_BROKEN = {"E01": 2, "E02": 1}
EDGE_DOCKED_AT_7 = {"E01": 16, "E02": 15}
EDGE_PM_START_BIKES = {"E01": 15, "E02": 11}
EDGE_MISSING = {("E02", 3, "AM"): range(6, 10), ("E02", 11, "PM"): range(12, 16)}  # 07:30-07:45, 17:00-17:15


def weekdays() -> list[date]:
    days, d = [], FIRST_DAY
    while len(days) < N_DAYS:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def trajectory(start: int, usable_max: int, kind: str | None, d: int, rng: random.Random) -> list[int]:
    """Rentable bikes at the 24 snapshots.

    usable_max = capacity - broken bikes (bikes that fit when no dock is free).
    kind "empty": bikes fall to 0 at snapshot 24 - d and stay at 0 (d empty snapshots).
    kind "full":  bikes rise to usable_max at snapshot 24 - d and stay (d full snapshots).
    d = 0 or kind None: the station drifts but is never empty or full.
    Before that point bikes stay strictly between 0 and usable_max.
    """
    if not 0 < start < usable_max:
        raise ValueError(f"start {start} must be strictly between 0 and {usable_max}")
    if kind is None or d == 0:
        target = {"empty": 1, "full": usable_max - 1, None: start}[kind]
        onset, end = STEPS, target
    else:
        onset, end = STEPS - d, (0 if kind == "empty" else usable_max)
    out = []
    for t in range(STEPS):
        if t >= onset:
            out.append(end)
            continue
        span = onset if onset < STEPS else STEPS - 1
        value = round(start + (end - start) * t / span)
        if 0 < t:
            value += rng.choice((-1, 0, 1))
        out.append(min(max(value, 1), usable_max - 1))
    return out


def stamp(day: date, window: str, step: int) -> str:
    hour, minute = WINDOW_START[window]
    m = hour * 60 + minute + 5 * step
    return f"{day.isoformat()}T{m // 60:02d}:{m % 60:02d}"


def build(stations, kinds, unusable, broken_of, docked_at_7, pm_start, *, planted=False, missing=None):
    rows = []
    for day_no, day in enumerate(weekdays(), start=1):
        for station, (_, capacity) in stations.items():
            broken = broken_of(station, day_no)
            if planted and day_no >= BROKEN_DOUBLES_FROM:
                broken *= 2
            starts = {"AM": docked_at_7[station] - broken, "PM": pm_start[station]}
            for window in WINDOW_START:
                rng = random.Random(f"{SEED}-{station}-{day_no}-{window}")
                bikes = trajectory(starts[window], capacity - broken, kinds[station][window],
                                   unusable[station][window][day_no - 1], rng)
                if planted and (station, day_no, window) == (STADIUM_STATION, STADIUM_DAY, "PM"):
                    full = capacity - broken
                    bikes = [bikes[0], (bikes[0] + full) // 2] + [full] * (STEPS - STADIUM_FULL_FROM)
                skip = (missing or {}).get((station, day_no, window), ())
                for step, b in enumerate(bikes):
                    if step not in skip:
                        rows.append([stamp(day, window, step), station, b, broken, capacity - b - broken])
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def main_broken(station: str, day_no: int) -> int:
    return BROKEN[station] + (S09_BROKEN_CHANGE[day_no - 1] if station == "S09" else 0)


def write_csv(rows, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(rows)


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    common = (STATIONS, KIND, UNUSABLE, main_broken, DOCKED_AT_7, PM_START_BIKES)
    write_csv(build(*common), out_dir / "stable.csv")
    write_csv(build(*common, planted=True), out_dir / "planted_events.csv")
    write_csv(build(EDGE_STATIONS, EDGE_KIND, EDGE_UNUSABLE, lambda s, _: EDGE_BROKEN[s],
                    EDGE_DOCKED_AT_7, EDGE_PM_START_BIKES, missing=EDGE_MISSING),
              out_dir / "edge_case.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write the synthetic test datasets.")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent,
                        help="folder to write the CSVs to (default: data/)")
    main(parser.parse_args().out)
