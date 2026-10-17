"""Decision B: has the network's broken-bike share risen, and where to collect (task H-10).

    build_maintenance(records, baseline_dates) -> {"chart", "stations", "as_of_date", "warnings"}

One NETWORK subgroup per weekday, from the 07:00 snapshot only (never 07:05):
d = broken bikes summed over stations, n = docked bikes (available + broken)
summed over the same stations. The p-chart comes from app/qc.py. The station
list ranks the latest 07:00 snapshot by broken bikes. See docs/maintenance.md.
"""

from __future__ import annotations

from datetime import date, time

if __package__:
    from .data_loader import rush_window
    from .qc import STATUS_INSUFFICIENT, STATUS_OK, p_chart
else:  # run from inside app/ (testme.sh, Posit Connect)
    from data_loader import rush_window
    from qc import STATUS_INSUFFICIENT, STATUS_OK, p_chart

CHECK_TIME = time(7, 0)
MIN_BASELINE_DAYS = 10
ACTION = "inspect and collect broken bikes"


def build_maintenance(records: list[dict], baseline_dates: list[date]) -> dict:
    """Network 07:00 broken-bike p-chart plus the ranked station list. ``records`` are not changed."""
    stations = sorted({r["station_id"] for r in records})
    dates = sorted({r["timestamp"].date() for r in records if rush_window(r["timestamp"])})
    at_seven: dict[date, list[dict]] = {}
    for r in records:
        if r["timestamp"].time() == CHECK_TIME and rush_window(r["timestamp"]):
            at_seven.setdefault(r["timestamp"].date(), []).append(r)

    warnings, chart_warnings = [], []
    if len(baseline_dates) < MIN_BASELINE_DAYS:
        warnings.append(f"only {len(baseline_dates)} baseline days (need {MIN_BASELINE_DAYS}): "
                        "insufficient basis for control limits")

    def pair(d):
        snaps = at_seven.get(d, [])
        return (sum(r["num_bikes_disabled"] for r in snaps),
                sum(r["num_bikes_disabled"] + r["num_bikes_available"] for r in snaps))

    for d in sorted(set(dates) | set(baseline_dates)):
        present = {r["station_id"] for r in at_seven.get(d, [])}
        if not present:
            chart_warnings.append(f"{d.isoformat()}: no 07:00 snapshot, so no maintenance point")
        elif present != set(stations):
            absent = sorted(set(stations) - present)
            chart_warnings.append(f"{d.isoformat()}: incomplete coverage, {len(absent)} of {len(stations)} stations "
                                  f"missing at 07:00 ({', '.join(absent)}); they are left out of d and n")

    baseline_pairs = [pair(d) for d in baseline_dates if pair(d)[1] > 0]
    plotted = [d for d in dates if pair(d)[1] > 0]
    for d in dates:
        if at_seven.get(d) and pair(d)[1] == 0:
            chart_warnings.append(f"{d.isoformat()}: no bikes docked at 07:00 (n = 0), so no maintenance point")
    result = p_chart(baseline_pairs, [pair(d) for d in plotted])
    chart_warnings += result["warnings"]
    gate_ok = len(baseline_pairs) >= MIN_BASELINE_DAYS
    if not gate_ok:
        chart_warnings.append(f"{len(baseline_pairs)} baseline days with 07:00 data (need {MIN_BASELINE_DAYS}): "
                              "insufficient basis for control limits")
    points = []
    for d, point in zip(plotted, result["points"]):
        point = {**point, "date": d.isoformat(), "p_bar": result["p_bar"], "warnings": list(point["warnings"])}
        if not gate_ok and point["status"] == STATUS_OK:
            point.update(status=STATUS_INSUFFICIENT, lower_count=None, upper_count=None, lcl=None, ucl=None,
                         flagged_high=False, flagged_low=False)
            point["warnings"].append("insufficient basis for control limits")
        if point["flagged_high"]:
            point["warnings"].append("flagged high: more bikes are broken than normal")
        if point["flagged_low"]:
            point["warnings"].append("flagged low: fewer bikes are broken than normal (a decrease)")
        points.append(point)
    chart = {"baseline_dates": [d.isoformat() for d in baseline_dates], "p_bar": result["p_bar"],
             "points": points, "warnings": chart_warnings}

    as_of = max(at_seven) if at_seven else None
    station_rows = []
    if as_of is not None:
        broken = [r for r in at_seven[as_of] if r["num_bikes_disabled"] > 0]
        broken.sort(key=lambda r: (-r["num_bikes_disabled"], r["station_id"]))
        station_rows = [{"station_id": r["station_id"], "num_bikes_disabled": r["num_bikes_disabled"],
                         "action": ACTION} for r in broken]
        if dates and as_of < dates[-1]:
            warnings.append(f"station list is from {as_of.isoformat()} 07:00, older than the latest day "
                            f"{dates[-1].isoformat()}: stale data")
    else:
        warnings.append("no 07:00 snapshots at all: no maintenance chart or station list")
    return {"chart": chart, "stations": station_rows,
            "as_of_date": as_of.isoformat() if as_of else None, "warnings": warnings}
