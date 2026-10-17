"""Tests for app/availability.py on small hand-built records.

Run from the repo root:  python -m pytest tests/test_availability.py -q

A day's window is written as a string, one character per 5-minute snapshot:
  u = usable, e = empty (0 bikes), f = full (0 docks), b = both (all docks hold
  broken bikes), . = snapshot missing. Station capacity is 10 docks.
"""

import copy
from datetime import date, datetime, timedelta

import pytest

from app.availability import build_availability, median_minutes

DAYS = [d for d in (date(2026, 9, 14) + timedelta(days=i) for i in range(16)) if d.weekday() < 5][:11]
BASELINE, LATEST = DAYS[:10], DAYS[10]
START = {"AM": (7, 0), "PM": (16, 0)}


def window(station, day, win, pattern, broken=0):
    rows = []
    h, m = START[win]
    for step, c in enumerate(pattern):
        if c == ".":
            continue
        stamp = datetime(day.year, day.month, day.day, h, m) + timedelta(minutes=5 * step)
        bikes, disabled, docks = {
            "u": (4, broken, 6 - broken), "e": (0, broken, 10 - broken),
            "f": (10 - broken, broken, 0), "b": (0, 10, 0),
        }[c]
        rows.append({"timestamp": stamp, "station_id": station, "num_bikes_available": bikes,
                     "num_bikes_disabled": disabled, "num_docks_available": docks})
    return rows


def pattern(d, kind="e", n=24):
    """n snapshots, the last d of them unusable."""
    return "u" * (n - d) + kind * d


def station_days(station, win, ds, kind="e", broken=0, latest=None):
    """One window per day: baseline d values ds (10 of them), then the latest day."""
    rows = []
    for day, d in zip(BASELINE, ds):
        rows += window(station, day, win, pattern(d, kind), broken)
    if latest is not None:
        rows += window(station, LATEST, win, latest, broken)
    return rows


def row(result, win, station):
    return next(r for r in result[win]["stations"] if r["station_id"] == station)


P125 = [2, 4, 3, 3, 3, 3, 3, 3, 3, 3]  # 30 of 240 = 0.125, the SPEC known answer's p_bar


# ---- exact limits and flags ------------------------------------------------------------

def test_known_answer_limits_and_special_cause_flag():
    recs = station_days("S1", "AM", P125, latest=pattern(10))
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert r["p_bar"] == pytest.approx(0.125)
    assert r["ucl"] == pytest.approx(0.375) and r["lcl"] == 0
    assert (r["d"], r["n"]) == (10, 24) and r["flagged_high"]
    assert r["action"] == "investigate: special cause; van: drop bikes before 08:45"
    assert r["action_rank"] == 0


def test_d8_is_not_flagged_although_the_normal_formula_would():
    recs = station_days("S1", "AM", P125, latest=pattern(8))
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert r["p"] == pytest.approx(8 / 24) and not r["flagged_high"]
    assert r["action"].startswith("capacity review")  # in control, p_bar 0.125 > 0.10 target


def test_missing_snapshots_lower_n_and_widen_the_limit():
    latest = "...." + "u" * 13 + "e" * 7  # 20 logged, 7 empty
    recs = station_days("S1", "AM", P125, latest=latest)
    result = build_availability(recs, BASELINE)
    r = row(result, "AM", "S1")
    assert (r["d"], r["n"]) == (7, 20) and r["ucl"] == pytest.approx(0.40)
    assert result["AM"]["charts"]["S1"]["points"][-1]["upper_count"] == 8


def test_chart_has_one_dated_point_per_day_with_p_bar():
    recs = station_days("S1", "AM", P125, latest=pattern(10))
    chart = build_availability(recs, BASELINE)["AM"]["charts"]["S1"]
    assert chart["baseline_dates"] == [d.isoformat() for d in BASELINE]
    assert [p["date"] for p in chart["points"]] == [d.isoformat() for d in DAYS]
    assert all(p["p_bar"] == pytest.approx(0.125) for p in chart["points"])
    assert [p["flagged_high"] for p in chart["points"]] == [False] * 10 + [True]


# ---- AM and PM are separate --------------------------------------------------------------

def test_am_and_pm_are_charted_separately():
    pm_days = [1] + [0] * 9  # one full PM snapshot in the whole baseline
    recs = station_days("S1", "AM", P125, latest=pattern(10))
    recs += station_days("S1", "PM", pm_days, kind="f", latest=pattern(0))
    result = build_availability(recs, BASELINE)
    am, pm = row(result, "AM", "S1"), row(result, "PM", "S1")
    assert am["p_bar"] == pytest.approx(0.125) and am["flagged_high"]
    assert pm["p_bar"] == pytest.approx(1 / 240) and not pm["flagged_high"]
    assert (pm["empty_count"], pm["full_count"]) == (0, 0)
    assert set(result) == {"AM", "PM"}


# ---- the target is not a control limit ---------------------------------------------------

def test_chronic_station_gets_capacity_review_not_investigate():
    chronic = [6, 7, 5, 8, 6, 7, 6, 5, 7, 6]  # p_bar 0.2625, in control
    recs = station_days("HILL", "AM", chronic, latest=pattern(7))
    r = row(build_availability(recs, BASELINE), "AM", "HILL")
    assert not r["flagged_high"] and r["status"] == "ok"
    assert r["action"] == "capacity review: unusable every day"


def test_p_bar_exactly_at_target_is_not_capacity_review():
    at_target = [2, 3, 2, 3, 2, 3, 2, 3, 2, 2]  # 24 of 240 = 0.10, not above it
    recs = station_days("S1", "AM", at_target, latest=pattern(2))
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert r["p_bar"] == pytest.approx(0.10)
    assert r["action"] == "van: drop bikes before 08:50"


def test_target_parameter_is_used():
    recs = station_days("S1", "AM", P125, latest=pattern(3))
    assert row(build_availability(recs, BASELINE, target=0.20), "AM", "S1")["action"].startswith("van: drop")
    assert row(build_availability(recs, BASELINE, target=0.10), "AM", "S1")["action"].startswith("capacity review")


# ---- action precedence -------------------------------------------------------------------

def test_collect_beats_investigate_when_broken_bikes_fill_the_docks():
    recs = station_days("S1", "AM", P125, kind="f", broken=2, latest=pattern(10, "f"))
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert r["flagged_high"] and r["action"] == "collect broken bikes first"


def test_full_without_broken_bikes_means_pull():
    recs = station_days("S1", "AM", [1] * 10, kind="f", latest=pattern(1, "f"))
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert r["action"] == "van: pull bikes before 08:55"


def test_empty_and_full_tie_gives_no_direction():
    latest = "u" * 20 + "eeff"
    recs = station_days("S1", "AM", [1] * 10, latest=latest)
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert (r["empty_count"], r["full_count"]) == (2, 2)
    assert r["action"] == "OK" and r["action_rank"] == 1


def test_snapshot_both_empty_and_full_counts_once_in_d_and_in_both_counts():
    latest = "u" * 22 + "bu"
    recs = station_days("S1", "AM", [1] * 10, latest=latest)
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert (r["d"], r["empty_count"], r["full_count"]) == (1, 1, 1)
    assert r["action"] == "collect broken bikes first"  # full with disabled bikes


def test_nothing_unusable_is_ok():
    recs = station_days("S1", "AM", [1] * 10, latest=pattern(0))
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert r["action"] == "OK" and r["action_rank"] == 1


# ---- baseline timing ----------------------------------------------------------------------

def test_median_first_unusable_time_on_3_of_10_days():
    rows = []
    for i, day in enumerate(BASELINE):
        first = {0: 7, 1: 8, 2: 10}.get(i)  # 07:35, 07:40, 07:50; other days never empty
        pat = "u" * 24 if first is None else "u" * first + "e" + "u" * (23 - first)
        rows += window("S1", day, "AM", pat)
    rows += window("S1", LATEST, "AM", pattern(1))
    r = row(build_availability(rows, BASELINE), "AM", "S1")
    assert r["empty_onset"] == {"time": "07:40", "affected_days": 3, "observed_days": 10,
                                "text": "usually empty by 07:40, on 3 of 10 baseline days"}
    assert r["full_onset"]["time"] is None and r["full_onset"]["text"] == "baseline timing unavailable"
    assert r["action"] == "van: drop bikes before 07:40"


def test_even_median_averages_the_middle_two_and_floors():
    assert median_minutes([455, 470]) == 462  # 07:35 and 07:50 -> 07:42.5 -> 07:42
    assert median_minutes([455, 460, 470]) == 460


def test_no_baseline_timing_keeps_the_direction_without_a_deadline():
    # The baseline was empty once but never full, so a full latest day has no typical time.
    recs = station_days("S1", "AM", [0] * 9 + [1], latest=pattern(1, "f"))
    r = row(build_availability(recs, BASELINE), "AM", "S1")
    assert r["full_onset"]["time"] is None
    assert r["action"] == "van: pull bikes (baseline timing unavailable)"


# ---- the ten-day gate and missing data -----------------------------------------------------

def test_nine_baseline_days_with_data_is_insufficient_but_direction_survives():
    recs = station_days("S1", "AM", P125, latest=pattern(10))
    recs = [r for r in recs if r["timestamp"].date() != BASELINE[4]]  # one baseline day has no AM data
    result = build_availability(recs, BASELINE)
    r = row(result, "AM", "S1")
    assert r["status"] == "insufficient_basis" and r["ucl"] is None and not r["flagged_high"]
    assert r["action"] == "van: drop bikes before 08:45"  # measured direction, no special-cause claim
    chart = result["AM"]["charts"]["S1"]
    assert any("9 baseline days" in w for w in chart["warnings"])
    assert any(BASELINE[4].isoformat() in w for w in chart["warnings"])  # dated no-data warning
    assert BASELINE[4].isoformat() not in [p["date"] for p in chart["points"]]


def test_ten_baseline_days_pass_the_gate():
    recs = station_days("S1", "AM", P125, latest=pattern(10))
    assert row(build_availability(recs, BASELINE), "AM", "S1")["status"] == "ok"


def test_fewer_than_ten_baseline_dates_warns_at_window_level():
    recs = station_days("S1", "AM", P125, latest=pattern(10))
    result = build_availability(recs, BASELINE[:9])
    assert row(result, "AM", "S1")["status"] == "insufficient_basis"
    assert any("only 9 baseline days" in w for w in result["AM"]["warnings"])


def test_missing_latest_window_is_no_data_never_ok():
    recs = station_days("S1", "AM", P125, latest=pattern(1)) + station_days("S2", "AM", P125)
    result = build_availability(recs, BASELINE)
    r = row(result, "AM", "S2")
    assert r["status"] == "no_data" and r["n"] == 0 and r["p"] is None
    assert r["action"] == "no data for the latest day" and r["action_rank"] == 1
    assert any("S2" in w for w in result["AM"]["warnings"])


def test_p_bar_zero_station_has_no_limits():
    recs = station_days("CALM", "AM", [0] * 10, latest=pattern(0))
    r = row(build_availability(recs, BASELINE), "AM", "CALM")
    assert r["status"] == "insufficient_basis" and r["ucl"] is None
    assert r["action"] == "no action needed today; no control limits (insufficient basis)"


# ---- ordering and purity -------------------------------------------------------------------

def test_actionable_rows_first_then_station_id():
    recs = []
    for s, d in [("S3", 0), ("S1", 0), ("S4", 2), ("S2", 2)]:
        recs += station_days(s, "AM", [1] * 10, latest=pattern(d))
    order = [(r["station_id"], r["action_rank"]) for r in build_availability(recs, BASELINE)["AM"]["stations"]]
    assert order == [("S2", 0), ("S4", 0), ("S1", 1), ("S3", 1)]


def test_rows_have_every_frozen_field_and_records_are_not_changed():
    recs = station_days("S1", "AM", P125, latest=pattern(10))
    before = copy.deepcopy(recs)
    result = build_availability(recs, BASELINE)
    assert recs == before
    assert set(row(result, "AM", "S1")) == {
        "station_id", "date", "n", "d", "p", "empty_count", "full_count", "p_bar", "lcl", "ucl",
        "flagged_high", "flagged_low", "status", "empty_onset", "full_onset", "action", "action_rank", "warnings"}
    assert set(result["AM"]) == {"stations", "charts", "warnings"}
    assert set(result["AM"]["charts"]["S1"]) == {"baseline_dates", "p_bar", "points", "warnings"}
