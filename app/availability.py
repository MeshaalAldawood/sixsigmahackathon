"""Station rush availability decisions from observed snapshots and exact p-charts.

The caller supplies the original ten baseline weekdays. This module never
reselects them after filtering records (for example, for a replay cutoff).
"""

from collections import defaultdict
from datetime import date, datetime, time
from statistics import median

try:
    from app.qc import INSUFFICIENT, p_chart
except ModuleNotFoundError:  # Posit Connect runs with app/ as its working directory.
    from qc import INSUFFICIENT, p_chart


WINDOWS = {"AM": (time(7), time(9)), "PM": (time(16), time(18))}


def _onset(rows_by_day, baseline_dates, kind):
    """Median first occurrence among observed baseline days only."""
    observed = [day for day in baseline_dates if rows_by_day.get(day)]
    first_minutes = []
    for day in observed:
        matching = [r["timestamp"].hour * 60 + r["timestamp"].minute
                    for r in rows_by_day[day] if _state(r, kind)]
        if matching:
            first_minutes.append(min(matching))
    clock = None
    if first_minutes:
        # Clock labels have minute precision. Floor a half-minute median so
        # the displayed "by HH:MM" deadline never moves later than observed.
        minutes = int(median(first_minutes))
        clock = f"{minutes // 60:02d}:{minutes % 60:02d}"
    affected = len(first_minutes)
    count = len(observed)
    partial_days = sum(len(rows_by_day[day]) < 24 for day in observed)
    observed_snapshots = sum(len(rows_by_day[day]) for day in observed)
    return {
        "time": clock,
        "affected_days": affected,
        "observed_days": count,
        "missing_days": len(baseline_dates) - count,
        "partial_days": partial_days,
        "observed_snapshots": observed_snapshots,
        "expected_snapshots": 24 * len(baseline_dates),
        "label": f"{clock} on {affected} of {count} observed days" if clock else None,
    }


def _state(record, kind):
    return record["num_bikes_available"] == 0 if kind == "empty" else record["num_docks_available"] == 0


def _counts(records):
    empty = sum(_state(record, "empty") for record in records)
    full = sum(_state(record, "full") for record in records)
    unusable = sum(_state(record, "empty") or _state(record, "full") for record in records)
    return unusable, len(records), empty, full


def _direction(empty, full, onset):
    if empty > full:
        deadline = onset["empty"]["time"]
        return "van: drop bikes" + (f" before {deadline}" if deadline else "")
    if full > empty:
        deadline = onset["full"]["time"]
        return "van: pull bikes" + (f" before {deadline}" if deadline else "")
    return None


def _action(point, today_rows, onset, target, p_bar):
    if point["n"] == 0:
        return "no data"
    if any(_state(record, "full") and record["num_bikes_disabled"] > 0 for record in today_rows):
        return "collect broken bikes first"
    direction = _direction(point["empty_count"], point["full_count"], onset)
    if point["flagged_high"]:
        return "investigate: special cause" + (f"; {direction}" if direction else "")
    if point["status"] == "in_control" and p_bar is not None and p_bar > target:
        return "capacity review: unusable every day"
    return direction or "OK"


def build_availability(records, baseline_dates, target=0.10, *, as_of=None, calibrated=True):
    """Return AM/PM station charts and latest-global-day dispatch tables.

    ``records`` are the validated weekday rush rows from ``load_station_status``.
    Missing snapshots lower n. A station/day/window with n=0 stays in the
    dispatch table but is omitted from the chart's plotted points.
    """
    if isinstance(target, bool) or not isinstance(target, (int, float)) or not 0 <= target <= 1:
        raise ValueError("target must be a proportion between 0 and 1")
    baseline = sorted({day.date() if isinstance(day, datetime) else day for day in baseline_dates})
    if len(baseline) > 10:
        baseline = baseline[:10]
    if any(not isinstance(day, date) for day in baseline):
        raise ValueError("baseline_dates must contain dates")
    rows = sorted(records, key=lambda record: (record["timestamp"], record["station_id"]))
    valid = []
    for record in rows:
        timestamp = record["timestamp"]
        if timestamp.weekday() < 5 and any(start <= timestamp.time() < end for start, end in WINDOWS.values()):
            valid.append(record)
    dates = sorted({record["timestamp"].date() for record in valid} |
                   ({as_of.date()} if as_of is not None else set()))
    latest = dates[-1] if dates else None
    stations = sorted({record["station_id"] for record in valid})
    report = {
        "latest_date": latest.isoformat() if latest else None,
        "baseline_dates": [day.isoformat() for day in baseline],
        "target": target,
        "warnings": ["Control-chart signals are exploratory; consecutive snapshots are dependent."],
    }
    for window, (start, end) in WINDOWS.items():
        by_station = defaultdict(lambda: defaultdict(list))
        for record in valid:
            if start <= record["timestamp"].time() < end:
                by_station[record["station_id"]][record["timestamp"].date()].append(record)
        charts = {}
        dispatch = []
        section_warnings = []
        for station_id in stations:
            groups = by_station[station_id]
            baseline_counts = [_counts(groups[day])[:2] for day in baseline] if calibrated else []
            complete_basis = calibrated and len(baseline) == 10 and all(n > 0 for _, n in baseline_counts)
            raw_chart = p_chart(baseline_counts, [_counts(groups[day])[:2] for day in dates])
            warnings = list(raw_chart["warnings"])
            if not complete_basis and INSUFFICIENT not in warnings:
                warnings.append(INSUFFICIENT)
            if not complete_basis:
                warnings.append("fewer than 10 observed baseline days for this station/window")
            if not calibrated:
                warnings.append("original ten-day calibration has not completed")
            onset = {kind: _onset(groups, baseline if calibrated else [], kind)
                     for kind in ("empty", "full")}
            if any(value["missing_days"] or value["partial_days"] for value in onset.values()):
                warnings.append("missing baseline snapshots may hide or delay first-unusable time")
            points = []
            current = None
            for day, qc_point in zip(dates, raw_chart["points"]):
                _, _, empty, full = _counts(groups[day])
                point = {
                    **qc_point,
                    "date": day.isoformat(),
                    "empty_count": empty,
                    "full_count": full,
                }
                provisional = as_of is not None and day == as_of.date() and as_of.time() < end
                point["provisional"] = provisional
                point["window_complete"] = not provisional
                point["expected_snapshots"] = 24
                point["observed_snapshots"] = point["n"]
                if not complete_basis:
                    point.update(lcl=None, ucl=None, lower_count=None, upper_count=None,
                                 flagged_high=False, flagged_low=False,
                                 status="no_data" if point["n"] == 0 else "insufficient_basis")
                    if point["n"] and INSUFFICIENT not in point["warnings"]:
                        point["warnings"].append(INSUFFICIENT)
                if provisional:
                    point.update(lcl=None, ucl=None, lower_count=None, upper_count=None,
                                 flagged_high=False, flagged_low=False,
                                 status="provisional" if point["n"] else "no_data")
                    point["warnings"].append("rush window is incomplete; final control signal withheld")
                if point["n"] > 0:
                    points.append(point)
                if day == latest:
                    current = point
            charts[station_id] = {
                "station_id": station_id,
                "p_bar": raw_chart["p_bar"],
                "points": points,
                "onset": onset,
                "warnings": warnings,
            }
            if latest is not None:
                if current is None:
                    current = {
                        "date": latest.isoformat(), "d": 0, "n": 0, "p": None,
                        "empty_count": 0, "full_count": 0, "lcl": None, "ucl": None,
                        "lower_count": None, "upper_count": None,
                        "flagged_high": False, "flagged_low": False,
                        "status": "no_data", "warnings": ["subgroup has n=0; no observed share or control limits"],
                        "provisional": as_of is not None and latest == as_of.date() and as_of.time() < end,
                        "window_complete": as_of is None or latest != as_of.date() or as_of.time() >= end,
                        "expected_snapshots": 24, "observed_snapshots": 0,
                    }
                action = ("provisional: rush window incomplete" if current["provisional"] and current["n"]
                          else _action(current, groups[latest], onset, target, raw_chart["p_bar"]))
                dispatch.append({
                    "station_id": station_id,
                    **current,
                    "p_bar": raw_chart["p_bar"],
                    "target": target,
                    "onset": onset,
                    "typical_first_unusable": (
                        onset["empty"]["label"] if current["empty_count"] > current["full_count"]
                        else onset["full"]["label"] if current["full_count"] > current["empty_count"]
                        else None
                    ),
                    "action": action,
                })
            if warnings:
                section_warnings.append(f"{station_id}: {'; '.join(warnings)}")
        dispatch.sort(key=lambda item: (item["action"] in ("OK", "no data"), item["station_id"]))
        window_provisional = as_of is not None and latest == as_of.date() and as_of.time() < end
        report[window] = {
            "stations": dispatch, "charts": charts, "warnings": section_warnings,
            "provisional": window_provisional,
            "window_complete": not window_provisional,
            "expected_snapshots_per_station": 24,
        }
    return report
