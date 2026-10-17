"""Network broken-bike p-chart and morning collection list."""

from __future__ import annotations

from datetime import date, datetime, time

try:
    from app.qc import INSUFFICIENT, p_chart
except ModuleNotFoundError:  # Posit Connect also runs with app/ as its root.
    from qc import INSUFFICIENT, p_chart


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def build_maintenance(records: list[dict], baseline_dates, *, as_of=None, calibrated=True) -> dict:
    """Aggregate exact 07:00 weekday snapshots and apply the shared p-chart.

    ``records`` contains validated rows from the CSV loader, optionally cut off
    by the replay backend. ``baseline_dates`` is the frozen set of the first ten
    baseline weekdays; later observations never enter the center line.
    """
    baseline = sorted({_date(day) for day in baseline_dates})[:10]
    dates = set()
    morning: dict[date, dict[str, dict]] = {}
    for record in records:
        timestamp = record["timestamp"]
        if timestamp.weekday() >= 5:
            continue
        day = timestamp.date()
        dates.add(day)
        if timestamp.time() != time(7):
            continue
        station = record["station_id"]
        day_rows = morning.setdefault(day, {})
        if station in day_rows:
            raise ValueError(f"duplicate 07:00 snapshot for {station} on {day.isoformat()}")
        day_rows[station] = record

    ordered_dates = sorted(dates)
    counts = {}
    for day in ordered_dates:
        rows = morning.get(day, {}).values()
        disabled = sum(row["num_bikes_disabled"] for row in rows)
        docked = sum(row["num_bikes_available"] + row["num_bikes_disabled"] for row in rows)
        counts[day] = (disabled, docked)

    observed_baseline = [day for day in baseline if counts.get(day, (0, 0))[1] > 0]
    enough_baseline = calibrated and len(baseline) == 10 and len(observed_baseline) == 10
    chart = p_chart(
        [counts[day] for day in baseline] if enough_baseline else [],
        [counts[day] for day in ordered_dates],
    )
    for day, point in zip(ordered_dates, chart["points"]):
        point["date"] = day.isoformat()
    chart["baseline_dates"] = [day.isoformat() for day in baseline]
    chart["baseline_observed_days"] = len(observed_baseline)
    warnings = list(chart["warnings"])
    if not enough_baseline:
        warnings.append(
            f"{INSUFFICIENT}: 10 baseline weekdays with docked bikes required; "
            f"observed {len(observed_baseline)}"
        )
    if not calibrated:
        warnings.append("original ten-day calibration has not completed")
    for day in ordered_dates:
        if counts[day][1] == 0:
            warnings.append(f"{day.isoformat()}: no docked bikes at 07:00; point has n=0")

    measurement_day = max(morning, default=None)
    stations = []
    if measurement_day is not None:
        for station_id, record in morning[measurement_day].items():
            disabled = record["num_bikes_disabled"]
            if disabled > 0:
                stations.append({
                    "station_id": station_id,
                    "num_bikes_disabled": disabled,
                    "action": "inspect and collect broken bikes",
                })
        stations.sort(key=lambda row: (-row["num_bikes_disabled"], row["station_id"]))

    measurement_at = datetime.combine(measurement_day, time(7)) if measurement_day else None
    stale = bool(measurement_at and as_of is not None and measurement_at.date() < as_of.date())
    if stale:
        warnings.append("latest weekday has no 07:00 network measurement; showing previous 07:00")
    expected_stations = len({record["station_id"] for record in records})
    measured_stations = len(morning[measurement_day]) if measurement_day else 0
    if measurement_day and measured_stations < expected_stations:
        warnings.append(f"07:00 station coverage {measured_stations} of {expected_stations} observed stations")

    return {
        "chart": chart,
        "stations": stations,
        "as_of_date": measurement_day.isoformat() if measurement_day else None,
        "measurement_timestamp": measurement_at.isoformat(timespec="minutes") if measurement_at else None,
        "observed_stations_at_0700": measured_stations,
        "expected_stations_at_0700": expected_stations,
        "stale": stale,
        "warnings": warnings,
    }
