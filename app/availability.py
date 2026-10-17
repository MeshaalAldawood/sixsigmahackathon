"""Decision A: which stations need a van in each rush window (task H-09).

    build_availability(records, baseline_dates, target=0.10)
        -> {"AM": {"stations", "charts", "warnings"}, "PM": {...}}

One subgroup = one station, one weekday, one rush window. n = snapshots logged
in it; d = unusable snapshots (no bikes OR no free docks; a snapshot that is both
counts once in d but in both descriptive counts). Each station has an AM chart
and a PM chart, computed by app/qc.py; this module only counts and decides.
See docs/availability.md.
"""

from __future__ import annotations

from datetime import date

if __package__:
    from .data_loader import rush_window
    from .qc import STATUS_INSUFFICIENT, STATUS_NO_DATA, STATUS_OK, p_chart
else:  # run from inside app/ (testme.sh, Posit Connect)
    from data_loader import rush_window
    from qc import STATUS_INSUFFICIENT, STATUS_NO_DATA, STATUS_OK, p_chart

WINDOWS = ("AM", "PM")
MIN_BASELINE_DAYS = 10
DEFAULT_TARGET = 0.10  # service-level target, NOT a control limit

RANK_ACTION, RANK_NONE = 0, 1


def _is_empty(r: dict) -> bool:
    return r["num_bikes_available"] == 0


def _is_full(r: dict) -> bool:
    return r["num_docks_available"] == 0


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def median_minutes(values: list[int]) -> int:
    """Median of clock minutes; for an even count the mean of the two middle values,
    floored to a whole minute (so the deadline shown is never later than the data)."""
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) // 2


def onset(groups: dict, baseline_dates: list[date], test, label: str) -> dict:
    """Typical first empty (or full) clock time over the baseline days on which it happened."""
    observed = [d for d in baseline_dates if groups.get(d)]
    firsts = []
    for d in observed:
        hits = [r["timestamp"] for r in groups[d] if test(r)]
        if hits:
            first = min(hits)
            firsts.append(first.hour * 60 + first.minute)
    if not firsts:
        return {"time": None, "affected_days": 0, "observed_days": len(observed),
                "text": "baseline timing unavailable"}
    time = _hhmm(median_minutes(firsts))
    return {"time": time, "affected_days": len(firsts), "observed_days": len(observed),
            "text": f"usually {label} by {time}, on {len(firsts)} of {len(observed)} baseline days"}


def _direction(empty_count: int, full_count: int, empty_onset: dict, full_onset: dict) -> str | None:
    if empty_count > full_count:
        verb, when = "drop bikes", empty_onset["time"]
    elif full_count > empty_count:
        verb, when = "pull bikes", full_onset["time"]
    else:
        return None  # a tie, or nothing unusable: no direction
    return f"van: {verb} before {when}" if when else f"van: {verb} (baseline timing unavailable)"


def decide(row: dict, latest_snapshots: list[dict], target: float) -> tuple[str, int]:
    """SPEC section 4 dispatch rules, first match wins."""
    if row["status"] == STATUS_NO_DATA:
        return "no data for the latest day", RANK_NONE
    if any(_is_full(r) and r["num_bikes_disabled"] > 0 for r in latest_snapshots):
        return "collect broken bikes first", RANK_ACTION
    direction = _direction(row["empty_count"], row["full_count"], row["empty_onset"], row["full_onset"])
    limits_valid = row["status"] == STATUS_OK
    if limits_valid and row["flagged_high"]:
        action = "investigate: special cause"
        return (f"{action}; {direction}" if direction else action), RANK_ACTION
    if limits_valid and not row["flagged_low"] and row["p_bar"] is not None and row["p_bar"] > target:
        return "capacity review: unusable every day", RANK_ACTION
    if direction:
        return direction, RANK_ACTION
    if not limits_valid:
        return "no action needed today; no control limits (insufficient basis)", RANK_NONE
    return "OK", RANK_NONE


def _dates_of(records: list[dict]) -> list[date]:
    return sorted({r["timestamp"].date() for r in records if rush_window(r["timestamp"])})


def build_window(records: list[dict], window: str, baseline_dates: list[date],
                 target: float = DEFAULT_TARGET) -> dict:
    dates = _dates_of(records)
    latest = dates[-1] if dates else None
    stations = sorted({r["station_id"] for r in records})
    # station -> date -> snapshots in this window
    by_station = {s: {} for s in stations}
    for r in records:
        if rush_window(r["timestamp"]) == window:
            by_station[r["station_id"]].setdefault(r["timestamp"].date(), []).append(r)

    window_warnings, charts, rows = [], {}, []
    if len(baseline_dates) < MIN_BASELINE_DAYS:
        window_warnings.append(f"only {len(baseline_dates)} baseline days (need {MIN_BASELINE_DAYS}): "
                               "insufficient basis for control limits")
    for station in stations:
        groups = by_station[station]

        def pair(d):
            snaps = groups.get(d, [])
            return sum(1 for r in snaps if _is_empty(r) or _is_full(r)), len(snaps)

        baseline_pairs = [pair(d) for d in baseline_dates if pair(d)[1] > 0]
        plotted = [d for d in dates if pair(d)[1] > 0]
        chart_warnings = [f"{d.isoformat()}: no snapshots in the {window} window"
                          for d in sorted(set(dates) | set(baseline_dates)) if pair(d)[1] == 0]
        result = p_chart(baseline_pairs, [pair(d) for d in plotted])
        chart_warnings += result["warnings"]
        gate_ok = len(baseline_pairs) >= MIN_BASELINE_DAYS
        if not gate_ok:
            chart_warnings.append(f"{len(baseline_pairs)} baseline days with data (need {MIN_BASELINE_DAYS}): "
                                  "insufficient basis for control limits")
        points = []
        for d, point in zip(plotted, result["points"]):
            point = {**point, "date": d.isoformat(), "p_bar": result["p_bar"]}
            if not gate_ok and point["status"] == STATUS_OK:
                point.update(status=STATUS_INSUFFICIENT, lower_count=None, upper_count=None, lcl=None, ucl=None,
                             flagged_high=False, flagged_low=False,
                             warnings=point["warnings"] + ["insufficient basis for control limits"])
            points.append(point)
        charts[station] = {"baseline_dates": [d.isoformat() for d in baseline_dates],
                           "p_bar": result["p_bar"], "points": points, "warnings": chart_warnings}

        latest_snaps = groups.get(latest, []) if latest else []
        latest_point = next((p for p in points if p["date"] == (latest.isoformat() if latest else None)), None)
        row = {
            "station_id": station, "date": latest.isoformat() if latest else None,
            "n": len(latest_snaps), "d": sum(1 for r in latest_snaps if _is_empty(r) or _is_full(r)),
            "p": latest_point["p"] if latest_point else None,
            "empty_count": sum(1 for r in latest_snaps if _is_empty(r)),
            "full_count": sum(1 for r in latest_snaps if _is_full(r)),
            "p_bar": result["p_bar"],
            "lcl": latest_point["lcl"] if latest_point else None,
            "ucl": latest_point["ucl"] if latest_point else None,
            "flagged_high": latest_point["flagged_high"] if latest_point else False,
            "flagged_low": latest_point["flagged_low"] if latest_point else False,
            "status": latest_point["status"] if latest_point else STATUS_NO_DATA,
            "empty_onset": onset(groups, baseline_dates, _is_empty, "empty"),
            "full_onset": onset(groups, baseline_dates, _is_full, "full"),
            "warnings": list(latest_point["warnings"]) if latest_point else [f"no {window} snapshots on the latest day"],
        }
        row["action"], row["action_rank"] = decide(row, latest_snaps, target)
        rows.append(row)
    missing = [r["station_id"] for r in rows if r["status"] == STATUS_NO_DATA]
    if missing:
        window_warnings.append(f"no {window} data on the latest day for: {', '.join(missing)}")
    rows.sort(key=lambda r: (r["action_rank"], r["station_id"]))
    return {"stations": rows, "charts": charts, "warnings": window_warnings}


def build_availability(records: list[dict], baseline_dates: list[date], target: float = DEFAULT_TARGET) -> dict:
    """Availability results for both rush windows. ``records`` are not changed."""
    return {w: build_window(records, w, list(baseline_dates), target) for w in WINDOWS}

