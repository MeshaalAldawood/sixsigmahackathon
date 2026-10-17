"""Generate the three SYNTHETIC test datasets in data/ (task H-02).

Run from the repo root:   python data/generate.py
Write somewhere else:     python data/generate.py --out /tmp/check

Nothing here is real. Every value is drawn from a seeded random model, so the
same seed always writes byte-identical files. Standard library only.

Model, per station, weekday and rush window (24 five-minute snapshots):
  * broken bikes for the day: each of round(0.5 * capacity) bikes is broken
    with probability P_BROKEN (doubled from day 13 in planted_events.csv);
    they stay docked all day;
  * rentable bikes: a bounded random walk. Each 5-minute step adds up to 2
    arrivals (each with probability p_arrive) and removes up to 2 departures
    (each with probability p_depart), kept between 0 and capacity - broken;
  * free docks = capacity - rentable bikes - broken bikes.
Each (station, day, window) gets its own random stream, seeded from SEED and
its key, so changing one day never changes the draws of another.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261016

COLUMNS = [
    "timestamp",
    "station_id",
    "num_bikes_available",
    "num_bikes_disabled",
    "num_docks_available",
]

# 15 weekdays, Mon 2026-09-14 to Fri 2026-10-02. Days are numbered from 1.
FIRST_DAY = date(2026, 9, 14)
N_DAYS = 15
BASELINE_DAYS = 10
WINDOWS = {"AM": (7, 0), "PM": (16, 0)}  # start of each 2-hour rush window
SNAPSHOTS_PER_WINDOW = 24  # every 5 minutes: 07:00-08:55 and 16:00-17:55

P_BROKEN = 0.10  # share of a station's bikes broken on a normal day

# Planted signals (planted_events.csv only).
STADIUM_STATION = "S08"
STADIUM_DAY = 12  # Tue 2026-09-29, PM window: full from 16:10 on
STADIUM_FULL_FROM_STEP = 2
BROKEN_DOUBLES_FROM_DAY = 13  # Wed 2026-09-30 onward: P_BROKEN doubles

# station_id: (type, capacity, {window: (start share of free space, p_arrive, p_depart)})
STATIONS = {
    "S01": ("residential", 23, {"AM": (0.55, 0.08, 0.30), "PM": (0.45, 0.30, 0.08)}),
    "S02": ("residential", 23, {"AM": (0.60, 0.08, 0.30), "PM": (0.45, 0.30, 0.08)}),
    "S03": ("residential", 27, {"AM": (0.55, 0.08, 0.30), "PM": (0.50, 0.30, 0.08)}),
    "S04": ("downtown", 31, {"AM": (0.45, 0.30, 0.08), "PM": (0.55, 0.08, 0.30)}),
    "S05": ("downtown", 31, {"AM": (0.58, 0.30, 0.08), "PM": (0.55, 0.08, 0.30)}),
    "S06": ("downtown", 27, {"AM": (0.50, 0.30, 0.08), "PM": (0.55, 0.08, 0.30)}),
    "S07": ("hilltop", 15, {"AM": (0.92, 0.00, 0.40), "PM": (0.50, 0.15, 0.15)}),
    "S08": ("stadium-downtown", 39, {"AM": (0.70, 0.30, 0.10), "PM": (0.25, 0.10, 0.25)}),
    "S09": ("balanced", 19, {"AM": (0.30, 0.18, 0.20), "PM": (0.70, 0.20, 0.18)}),
    "S10": ("balanced", 19, {"AM": (0.70, 0.20, 0.18), "PM": (0.30, 0.18, 0.20)}),
}

EDGE_STATIONS = {
    # Always usable: a big station that never gets close to empty or full.
    "E01": ("always-usable", 31, {"AM": (0.50, 0.15, 0.15), "PM": (0.50, 0.15, 0.15)}),
    "E02": ("residential", 23, {"AM": (0.40, 0.08, 0.30), "PM": (0.55, 0.30, 0.08)}),
}
EDGE_ALWAYS_USABLE = "E01"
EDGE_MARGIN = 3  # E01 stays at least this many bikes and docks from empty and full
# Missing snapshots in edge_case.csv: (station, day, window) -> steps not logged.
EDGE_MISSING = {
    ("E02", 3, "AM"): (6, 7, 8, 9),
    ("E02", 11, "PM"): (12, 13, 14, 15),
}


def weekdays() -> list[date]:
    """The N_DAYS weekdays starting at FIRST_DAY, in order."""
    days, d = [], FIRST_DAY
    while len(days) < N_DAYS:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _rng(*key) -> random.Random:
    return random.Random("-".join(str(k) for k in (SEED, *key)))


def broken_bikes(station: str, capacity: int, day: int, p_broken: float) -> int:
    rng = _rng("broken", station, day)
    return sum(rng.random() < p_broken for _ in range(round(0.5 * capacity)))


def walk(station: str, day: int, window: str, capacity: int, broken: int,
         params: tuple[float, float, float], low: int = 0, high_margin: int = 0) -> list[int]:
    """Rentable bikes at each of the 24 snapshots of one window."""
    start_share, p_arrive, p_depart = params
    rng = _rng("walk", station, day, window)
    top = capacity - broken - high_margin
    bikes = round(low + start_share * (top - low))
    out = []
    for _ in range(SNAPSHOTS_PER_WINDOW):
        out.append(bikes)
        arrivals = sum(rng.random() < p_arrive for _ in range(2))
        departures = sum(rng.random() < p_depart for _ in range(2))
        bikes = min(max(bikes + arrivals - departures, low), top)
    return out


def _stamp(day: date, window: str, step: int) -> str:
    hour, minute = WINDOWS[window]
    minutes = hour * 60 + minute + 5 * step
    return f"{day.isoformat()}T{minutes // 60:02d}:{minutes % 60:02d}"


def build(stations: dict, *, planted: bool = False, edge: bool = False) -> list[dict]:
    rows = []
    for day_no, day in enumerate(weekdays(), start=1):
        for station, (_, capacity, params) in stations.items():
            p_broken = P_BROKEN
            if planted and day_no >= BROKEN_DOUBLES_FROM_DAY:
                p_broken = 2 * P_BROKEN
            broken = broken_bikes(station, capacity, day_no, p_broken)
            for window in WINDOWS:
                margin = EDGE_MARGIN if edge and station == EDGE_ALWAYS_USABLE else 0
                bikes = walk(station, day_no, window, capacity, broken, params[window],
                             low=margin, high_margin=margin)
                if (planted and station == STADIUM_STATION and day_no == STADIUM_DAY
                        and window == "PM"):
                    bikes = [b if step < STADIUM_FULL_FROM_STEP else capacity - broken
                             for step, b in enumerate(bikes)]
                missing = EDGE_MISSING.get((station, day_no, window), ()) if edge else ()
                for step, b in enumerate(bikes):
                    if step in missing:
                        continue
                    rows.append({
                        "timestamp": _stamp(day, window, step),
                        "station_id": station,
                        "num_bikes_available": b,
                        "num_bikes_disabled": broken,
                        "num_docks_available": capacity - b - broken,
                    })
    rows.sort(key=lambda r: (r["timestamp"], r["station_id"]))
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(build(STATIONS), out_dir / "stable.csv")
    write_csv(build(STATIONS, planted=True), out_dir / "planted_events.csv")
    write_csv(build(EDGE_STATIONS, edge=True), out_dir / "edge_case.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent,
                        help="folder to write the CSVs to (default: data/)")
    main(parser.parse_args().out)
