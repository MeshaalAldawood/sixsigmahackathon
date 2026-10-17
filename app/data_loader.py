"""Validate and load rush-hour station snapshots from a GBFS-shaped CSV."""

from __future__ import annotations

import csv
import re
from datetime import datetime, time
from pathlib import Path


COLUMNS = (
    "timestamp", "station_id", "num_bikes_available",
    "num_bikes_disabled", "num_docks_available",
)
COUNTS = COLUMNS[2:]


def load_station_status(path: str | Path) -> list[dict]:
    """Return weekday AM/PM rows, rejecting invalid source rows with line numbers.

    Validation occurs before filtering: malformed weekend or off-peak rows are
    still rejected. A missing five-minute snapshot is allowed and never filled.
    """
    observations = []
    seen = set()
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or tuple(reader.fieldnames) != COLUMNS:
            raise ValueError(f"row 1: expected columns {','.join(COLUMNS)}")
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(column) is None or
                                  not row[column].strip() for column in COLUMNS):
                raise ValueError(f"row {row_number}: missing value")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", row["timestamp"]):
                raise ValueError(f"row {row_number}: invalid timestamp")
            try:
                timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%dT%H:%M")
            except ValueError as error:
                raise ValueError(f"row {row_number}: invalid timestamp") from error
            station_id = row["station_id"].strip()
            key = (station_id, timestamp)
            if key in seen:
                raise ValueError(f"row {row_number}: duplicate station_id + timestamp")
            seen.add(key)
            observation = {"timestamp": timestamp, "station_id": station_id}
            for column in COUNTS:
                raw = row[column].strip()
                if not raw.isdecimal():
                    raise ValueError(f"row {row_number}: {column} must be a non-negative integer")
                observation[column] = int(raw)
            clock = timestamp.time()
            if timestamp.weekday() < 5 and (
                time(7) <= clock < time(9) or time(16) <= clock < time(18)
            ):
                observations.append(observation)
    return sorted(observations, key=lambda item: (item["timestamp"], item["station_id"]))


load_dataset = load_station_status
load_csv = load_station_status
