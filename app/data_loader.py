"""Read and check a GBFS-style station status log (task H-02).

Plain functions, standard library only, no statistics. The p-chart counts are
built from these rows elsewhere (app/availability.py, app/maintenance.py).

    rows = load_station_status("data/stable.csv")   # validated, or ValueError
    rush = filter_rush(rows)                         # weekdays, AM/PM windows only

Every error message names the file line it came from (line 1 is the header).
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, time
from pathlib import Path

COLUMNS = (
    "timestamp",
    "station_id",
    "num_bikes_available",
    "num_bikes_disabled",
    "num_docks_available",
)
COUNT_COLUMNS = COLUMNS[2:]
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M"
_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")

# Rush windows: start inclusive, end exclusive (07:00-08:55 and 16:00-17:55 at 5 minutes).
RUSH_WINDOWS = {
    "AM": (time(7, 0), time(9, 0)),
    "PM": (time(16, 0), time(18, 0)),
}


def _count(value: str, column: str, line: int) -> int:
    try:
        number = int(value)
    except ValueError:
        try:
            float(value)
        except ValueError:
            raise ValueError(f"line {line}: {column} is {value!r}, not a number") from None
        raise ValueError(f"line {line}: {column} is {value!r}, not a whole number") from None
    if number < 0:
        raise ValueError(f"line {line}: {column} is {number}, counts cannot be negative")
    return number


def load_station_status(path: str | Path) -> list[dict]:
    """Read a station status CSV and return one dict per snapshot.

    Each dict has ``timestamp`` (datetime), ``station_id`` (str), the three
    counts as ints, and ``line`` (its line number in the file).

    Raises ValueError, naming the line, for: a header that is not exactly
    COLUMNS in order, a row with the wrong number of values, a missing value,
    a timestamp not written as YYYY-MM-DDTHH:MM, a count that is negative, not
    a whole number or not a number, a duplicate station_id + timestamp, or a
    file with no data rows. Missing snapshots are allowed: they just mean
    fewer rows for that window.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None or tuple(h.strip() for h in header) != COLUMNS:
            raise ValueError(f"line 1: header must be {','.join(COLUMNS)}, got {header}")
        rows, seen = [], {}
        for line, values in enumerate(reader, start=2):
            if len(values) != len(COLUMNS):
                raise ValueError(f"line {line}: has {len(values)} values, expected {len(COLUMNS)}")
            record = dict(zip(COLUMNS, (v.strip() for v in values)))
            for column, value in record.items():
                if value == "":
                    raise ValueError(f"line {line}: {column} is missing")
            if not _TIMESTAMP_PATTERN.fullmatch(record["timestamp"]):
                raise ValueError(
                    f"line {line}: timestamp is {record['timestamp']!r}, expected YYYY-MM-DDTHH:MM")
            try:
                stamp = datetime.strptime(record["timestamp"], TIMESTAMP_FORMAT)
            except ValueError:
                raise ValueError(
                    f"line {line}: timestamp {record['timestamp']!r} is not a real date and time") from None
            key = (record["station_id"], stamp)
            if key in seen:
                raise ValueError(
                    f"line {line}: duplicates line {seen[key]} "
                    f"(station {record['station_id']} at {record['timestamp']})")
            seen[key] = line
            row = {"timestamp": stamp, "station_id": record["station_id"], "line": line}
            for column in COUNT_COLUMNS:
                row[column] = _count(record[column], column, line)
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no data rows after the header")
    return rows


def rush_window(stamp: datetime) -> str | None:
    """'AM' or 'PM' if the snapshot is in a weekday rush window, otherwise None."""
    if stamp.weekday() >= 5:
        return None
    for name, (start, end) in RUSH_WINDOWS.items():
        if start <= stamp.time() < end:
            return name
    return None


def filter_rush(rows: list[dict]) -> list[dict]:
    """Keep weekday rush-window snapshots, each copied with ``date`` and ``window`` added."""
    kept = []
    for row in rows:
        window = rush_window(row["timestamp"])
        if window is not None:
            kept.append({**row, "date": row["timestamp"].date(), "window": window})
    return kept
