"""Synthetic replay cutoff and observed station state.

All measurements are cut once, before either domain report is built. Navigation
metadata contains clock bounds only; it never contains future measurements.
"""

from datetime import datetime, time
import re


TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z")


def replay_clock(records: list[dict]) -> dict:
    """Return clock navigation data without station IDs or measurements."""
    if not records:
        raise ValueError("dataset has no weekday rush observations")
    timestamps = sorted({row["timestamp"] for row in records})
    baseline = sorted({timestamp.date() for timestamp in timestamps})[:10]
    calibration_end = datetime.combine(baseline[-1], time(18)) if len(baseline) == 10 else None
    last_as_of = datetime.combine(timestamps[-1].date(), time(18))
    return {
        "first_timestamp": timestamps[0].isoformat(timespec="minutes"),
        "last_timestamp": timestamps[-1].isoformat(timespec="minutes"),
        "last_as_of": last_as_of.isoformat(timespec="minutes"),
        "calibration_complete_at": calibration_end.isoformat(timespec="minutes") if calibration_end else None,
        "default_as_of": (calibration_end or timestamps[0]).isoformat(timespec="minutes"),
        "snapshot_timestamps": [timestamp.isoformat(timespec="minutes") for timestamp in timestamps],
    }


def parse_as_of(value: str | None) -> datetime | None:
    if value is None:
        return None
    if not TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError("as_of must be a local timestamp in YYYY-MM-DDTHH:MM format")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError as error:
        raise ValueError("as_of must be a valid local timestamp in YYYY-MM-DDTHH:MM format") from error


def prepare_replay(records: list[dict], as_of: datetime | None) -> dict:
    """Freeze source baseline dates, then return observations no later than cutoff."""
    if not records:
        raise ValueError("dataset has no weekday rush observations")
    ordered = sorted(records, key=lambda row: (row["timestamp"], row["station_id"]))
    baseline = sorted({row["timestamp"].date() for row in ordered})[:10]
    first = ordered[0]["timestamp"]
    last = ordered[-1]["timestamp"]
    cutoff = as_of if as_of is not None else last.replace(hour=18, minute=0)
    if cutoff < first or cutoff > last.replace(hour=18, minute=0):
        raise ValueError("as_of is outside this dataset's replay clock")
    visible = [row for row in ordered if row["timestamp"] <= cutoff]
    # The original tenth PM window closes at 18:00. A missing snapshot does
    # not move this clock boundary and does not create a replacement baseline.
    calibration_end = datetime.combine(baseline[-1], time(18)) if len(baseline) == 10 else None
    calibrated = calibration_end is not None and cutoff >= calibration_end
    current = {}
    for row in visible:
        current[row["station_id"]] = row
    station_status = []
    station_ids = sorted({row["station_id"] for row in ordered})
    for station_id in station_ids:
        row = current.get(station_id)
        if row is None:
            station_status.append({
                "station_id": station_id,
                "observed_at": None,
                "age_minutes": None,
                "stale": True,
                "missing": True,
                "num_bikes_available": None,
                "num_bikes_disabled": None,
                "num_docks_available": None,
                "unusable": None,
            })
            continue
        timestamp = row["timestamp"]
        age_minutes = int((cutoff - timestamp).total_seconds() // 60)
        station_status.append({
            "station_id": station_id,
            "observed_at": timestamp.isoformat(timespec="minutes"),
            "age_minutes": age_minutes,
            "stale": age_minutes > 5,
            "missing": False,
            "num_bikes_available": row["num_bikes_available"],
            "num_bikes_disabled": row["num_bikes_disabled"],
            "num_docks_available": row["num_docks_available"],
            "unusable": row["num_bikes_available"] == 0 or row["num_docks_available"] == 0,
        })
    return {
        "records": visible,
        "baseline_dates": baseline,
        "calibrated": calibrated,
        "as_of": cutoff,
        "station_status": station_status,
        "metadata": {
            "as_of": cutoff.isoformat(timespec="minutes"),
            "first_timestamp": first.isoformat(timespec="minutes"),
            "last_timestamp": last.isoformat(timespec="minutes"),
            "calibration_complete_at": calibration_end.isoformat(timespec="minutes") if calibration_end else None,
            "calibrated": calibrated,
            "observed_station_count": len(current),
            "station_count": len(station_ids),
            "synthetic": True,
        },
    }
