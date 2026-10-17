"""Read and check a GBFS-style station status log (task H-02).

Plain functions, standard library only, no statistics:

    records = load_dataset(Path("data/stable.csv"))  # every row validated, or ValueError
    rush = filter_rush(records)                       # weekday AM/PM rush snapshots only
    rush_window(record["timestamp"])                  # "AM", "PM" or None

Error messages name the CSV row: "row 57" is line 57 of the file, counting the
header as row 1, so it is the line a spreadsheet or text editor shows.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, time
from pathlib import Path

COLUMNS = ("timestamp", "station_id", "num_bikes_available", "num_bikes_disabled", "num_docks_available")
COUNT_COLUMNS = COLUMNS[2:]
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M"
_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")

# Half-open rush windows [start, end): 07:00-08:55 and 16:00-17:55 at 5-minute spacing.
RUSH_WINDOWS = {"AM": (time(7, 0), time(9, 0)), "PM": (time(16, 0), time(18, 0))}


def _count(value: str, column: str, row: int) -> int:
    if re.fullmatch(r"\d+", value):
        return int(value)
    if re.fullmatch(r"-\d+", value):
        raise ValueError(f"row {row}: {column} is {value}, counts cannot be negative")
    try:
        float(value)
    except ValueError:
        raise ValueError(f"row {row}: {column} is {value!r}, not a number") from None
    raise ValueError(f"row {row}: {column} is {value!r}, not a whole number")


def load_dataset(path: Path) -> list[dict]:
    """Read a station status CSV; return one dict per snapshot, sorted by (timestamp, station_id).

    Each dict has exactly the keys ``timestamp`` (naive local datetime),
    ``station_id`` (non-empty string), ``num_bikes_available``,
    ``num_bikes_disabled`` and ``num_docks_available`` (ints >= 0).

    Every row is validated before anything is filtered. Raises ValueError,
    naming the CSV row, for: a header that is not exactly COLUMNS in order, a
    row with the wrong number of values, a missing value, a timestamp not
    written as YYYY-MM-DDTHH:MM or not a real date, a count that is negative,
    fractional or not a number, a duplicate station_id + timestamp, or a file
    with no data rows. Missing snapshots are allowed (fewer rows, smaller n).
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None or tuple(h.strip() for h in header) != COLUMNS:
            raise ValueError(f"row 1: header must be {','.join(COLUMNS)}, got {header}")
        records, seen = [], {}
        for row, values in enumerate(reader, start=2):
            if len(values) != len(COLUMNS):
                raise ValueError(f"row {row}: has {len(values)} values, expected {len(COLUMNS)}")
            cells = dict(zip(COLUMNS, (v.strip() for v in values)))
            for column, value in cells.items():
                if value == "":
                    raise ValueError(f"row {row}: {column} is missing")
            text = cells["timestamp"]
            if not _TIMESTAMP_PATTERN.fullmatch(text):
                raise ValueError(f"row {row}: timestamp is {text!r}, expected YYYY-MM-DDTHH:MM")
            try:
                stamp = datetime.strptime(text, TIMESTAMP_FORMAT)
            except ValueError:
                raise ValueError(f"row {row}: timestamp {text!r} is not a real date and time") from None
            key = (cells["station_id"], stamp)
            if key in seen:
                raise ValueError(f"row {row}: duplicates row {seen[key]} (station {key[0]} at {text})")
            seen[key] = row
            record = {"timestamp": stamp, "station_id": cells["station_id"]}
            for column in COUNT_COLUMNS:
                record[column] = _count(cells[column], column, row)
            records.append(record)
    if not records:
        raise ValueError(f"{path}: no data rows after the header")
    records.sort(key=lambda r: (r["timestamp"], r["station_id"]))
    return records


def rush_window(stamp: datetime) -> str | None:
    """'AM' or 'PM' if the snapshot falls in a weekday rush window, otherwise None."""
    if stamp.weekday() >= 5:
        return None
    for name, (start, end) in RUSH_WINDOWS.items():
        if start <= stamp.time() < end:
            return name
    return None


def filter_rush(records: list[dict]) -> list[dict]:
    """Keep only weekday rush-window records (the same dicts, not copies; nothing is changed)."""
    return [r for r in records if rush_window(r["timestamp"]) is not None]
