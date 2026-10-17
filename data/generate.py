"""Regenerate the three synthetic GBFS-shaped demonstration files."""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path


SEED = 5300
COLUMNS = (
    "timestamp",
    "station_id",
    "num_bikes_available",
    "num_bikes_disabled",
    "num_docks_available",
)
STATIONS = (
    "residential_01", "residential_02", "residential_03", "residential_04",
    "downtown_01", "downtown_02", "downtown_03", "downtown_04",
    "hilltop_01", "stadium_01",
)


def weekdays(start: date, count: int) -> list[date]:
    days = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def snapshot_times(day: date, hour: int) -> list[datetime]:
    return [datetime.combine(day, time(hour)) + timedelta(minutes=5 * i) for i in range(24)]


def main(output: Path | None = None) -> None:
    output = output or Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    days = weekdays(date(2026, 10, 5), 15)
    stable = []
    planted = []
    edge = []

    # Onset changes among days while subgroup counts stay fixed. Both files use
    # the same rows through day 10; planted changes only after calibration.
    starts = {
        (station, day_index, hour): rng.randrange(5, 15)
        for station in STATIONS
        for day_index in range(15)
        for hour in (7, 16)
    }
    for day_index, day in enumerate(days, start=1):
        for hour in (7, 16):
            for index, timestamp in enumerate(snapshot_times(day, hour)):
                for station in STATIONS:
                    disabled = 2
                    available = 38
                    docks = 10
                    onset = starts[(station, day_index - 1, hour)]
                    if station.startswith("residential"):
                        mode = "empty" if hour == 7 else "full"
                        affected = onset <= index < onset + 2
                    elif station.startswith("downtown"):
                        mode = "full" if hour == 7 else "empty"
                        affected = onset <= index < onset + 2
                    elif station == "hilltop_01":
                        mode = "empty"
                        affected = onset <= index < onset + (4 if hour == 7 else 2)
                    else:
                        mode = "full"
                        affected = onset <= index < onset + 2
                    if affected:
                        if mode == "empty":
                            available, docks = 0, 48
                        else:
                            available, docks = 48, 0
                    base = [timestamp.isoformat(timespec="minutes"), station,
                            available, disabled, docks]
                    stable.append(base)

                    event = base.copy()
                    if day_index >= 13:
                        # Keep 40 docked bikes in normal snapshots: 2/40 -> 4/40.
                        event[3] = 4
                        if event[2] == 0:
                            event[4] = 46
                        elif event[4] == 0:
                            event[2] = 46
                        else:
                            event[2], event[4] = 36, 10
                    if day_index == 12 and hour == 16 and station == "stadium_01":
                        if 3 <= index < 21:
                            event[2], event[4] = 48, 0
                        else:
                            event[2], event[4] = 38, 10
                    planted.append(event)

                for station in ("edge_01", "edge_02"):
                    if (station == "edge_02" and day_index == 14 and hour == 7
                            and index in (5, 10, 15, 20)):
                        continue
                    available, docks = 38, 10
                    if station == "edge_02" and hour == 7 and index in (7, 8, 9):
                        available, docks = 0, 48
                    edge.append([timestamp.isoformat(timespec="minutes"), station,
                                 available, 2, docks])

    for filename, rows in (("stable.csv", stable),
                           ("planted_events.csv", planted),
                           ("edge_case.csv", edge)):
        with (output / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(COLUMNS)
            writer.writerows(rows)


if __name__ == "__main__":
    main()
