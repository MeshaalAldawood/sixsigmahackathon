"""Tests for app/maintenance.py on small hand-built records.

Run from the repo root:  python -m pytest tests/test_maintenance.py -q
"""

import copy
from datetime import date, datetime, timedelta

import pytest

from app.maintenance import build_maintenance

DAYS = [d for d in (date(2026, 9, 14) + timedelta(days=i) for i in range(16)) if d.weekday() < 5][:11]
BASELINE, LATEST = DAYS[:10], DAYS[10]


def snap(day, hhmm, station, available, broken):
    h, m = map(int, hhmm.split(":"))
    return {"timestamp": datetime(day.year, day.month, day.day, h, m), "station_id": station,
            "num_bikes_available": available, "num_bikes_disabled": broken, "num_docks_available": 3}


def network(day, broken_by_station, docked=50, hhmm="07:00"):
    """One snapshot per station; each station has `docked` bikes, some of them broken."""
    return [snap(day, hhmm, s, docked - k, k) for s, k in broken_by_station.items()]


def baseline_net(per_day=(5, 5, 5, 5)):
    """Four stations x 50 docked bikes = n 200; the default 5 broken each gives 20 of 200 = 0.10."""
    return {f"S{i + 1}": k for i, k in enumerate(per_day)}


def ten_day_records(per_day=(5, 5, 5, 5), latest=(5, 5, 5, 5)):
    recs = []
    for d in BASELINE:
        recs += network(d, baseline_net(per_day))
    recs += network(LATEST, baseline_net(latest))
    return recs


# ---- the known answer: 20 of 200 -> limits 8 to 34 ----------------------------------------

def test_network_point_sums_stations_at_0700():
    m = build_maintenance(ten_day_records(), BASELINE)
    first = m["chart"]["points"][0]
    assert (first["d"], first["n"]) == (20, 200)
    assert m["chart"]["p_bar"] == pytest.approx(0.10)
    assert (first["lower_count"], first["upper_count"]) == (8, 34)
    assert first["lcl"] == pytest.approx(0.04) and first["ucl"] == pytest.approx(0.17)


def test_doubled_broken_share_flags_high():
    m = build_maintenance(ten_day_records(latest=(10, 10, 10, 10)), BASELINE)
    last = m["chart"]["points"][-1]
    assert (last["d"], last["n"]) == (40, 200) and last["flagged_high"]
    assert any("more bikes are broken" in w for w in last["warnings"])


def test_equality_at_upper_count_is_not_flagged():
    last = build_maintenance(ten_day_records(latest=(9, 9, 8, 8)), BASELINE)["chart"]["points"][-1]
    assert last["d"] == 34 and not last["flagged_high"]


def test_low_flag_is_described_as_a_decrease():
    last = build_maintenance(ten_day_records(latest=(2, 2, 2, 1)), BASELINE)["chart"]["points"][-1]
    assert last["d"] == 7 and last["flagged_low"]
    assert any("fewer bikes are broken than normal (a decrease)" in w for w in last["warnings"])
    assert not any("more bikes" in w for w in last["warnings"])


def test_spec_maintenance_known_answer_through_the_module():
    recs = []
    for d in BASELINE:
        recs += network(d, {"A": 5, "B": 5}, docked=50)  # 10 of 100
    recs += network(LATEST, {"A": 13, "B": 12}, docked=50)  # 25 of 100
    chart = build_maintenance(recs, BASELINE)["chart"]
    assert chart["points"][0]["lcl"] == pytest.approx(0.02) and chart["points"][0]["ucl"] == pytest.approx(0.20)
    assert chart["points"][-1]["flagged_high"]


# ---- only 07:00 counts, once --------------------------------------------------------------

def test_only_the_0700_snapshot_is_used_never_0705():
    recs = ten_day_records()
    for d in DAYS:
        recs += network(d, baseline_net((40, 40, 40, 40)), hhmm="07:05")  # would wreck the chart if counted
        recs += network(d, baseline_net((40, 40, 40, 40)), hhmm="16:00")
    m = build_maintenance(recs, BASELINE)
    assert [(p["d"], p["n"]) for p in m["chart"]["points"]] == [(20, 200)] * 11
    assert m["stations"][0]["num_bikes_disabled"] == 5


def test_missing_0700_day_is_not_replaced_by_a_later_snapshot():
    recs = [r for r in ten_day_records() if r["timestamp"].date() != BASELINE[3]]
    recs += network(BASELINE[3], baseline_net(), hhmm="07:05")
    m = build_maintenance(recs, BASELINE)
    assert BASELINE[3].isoformat() not in [p["date"] for p in m["chart"]["points"]]
    assert any(BASELINE[3].isoformat() in w and "no 07:00" in w for w in m["chart"]["warnings"])
    assert m["chart"]["points"][0]["status"] == "insufficient_basis"  # only 9 baseline days left
    assert m["chart"]["points"][0]["ucl"] is None


def test_absent_station_is_left_out_of_d_and_n_with_a_warning():
    recs = [r for r in ten_day_records() if not (r["timestamp"].date() == LATEST and r["station_id"] == "S4")]
    m = build_maintenance(recs, BASELINE)
    last = m["chart"]["points"][-1]
    assert (last["d"], last["n"]) == (15, 150)
    assert any("incomplete coverage" in w and "S4" in w for w in m["chart"]["warnings"])


# ---- degenerate cases ------------------------------------------------------------------------

def test_zero_docked_bikes_gives_no_point():
    recs = ten_day_records()
    recs = [r for r in recs if r["timestamp"].date() != LATEST] + network(LATEST, {"S1": 0}, docked=0)
    m = build_maintenance(recs, BASELINE)
    assert LATEST.isoformat() not in [p["date"] for p in m["chart"]["points"]]
    assert any("n = 0" in w for w in m["chart"]["warnings"])


def test_no_broken_bikes_in_the_baseline_is_insufficient_basis():
    m = build_maintenance(ten_day_records(per_day=(0, 0, 0, 0), latest=(1, 0, 0, 0)), BASELINE)
    assert m["chart"]["p_bar"] == 0
    assert {p["status"] for p in m["chart"]["points"]} == {"insufficient_basis"}
    assert not any(p["flagged_high"] for p in m["chart"]["points"])


def test_no_0700_records_at_all():
    recs = [snap(d, "07:05", "S1", 10, 1) for d in DAYS]
    m = build_maintenance(recs, BASELINE)
    assert m["stations"] == [] and m["as_of_date"] is None and m["chart"]["points"] == []
    assert m["warnings"]


def test_fewer_than_ten_baseline_dates_warns():
    m = build_maintenance(ten_day_records(), BASELINE[:9])
    assert any("only 9 baseline days" in w for w in m["warnings"])
    assert m["chart"]["points"][0]["status"] == "insufficient_basis"


# ---- station list ------------------------------------------------------------------------------

def test_station_list_ranks_latest_0700_by_broken_bikes_then_id():
    recs = ten_day_records(latest=(2, 7, 0, 7))
    m = build_maintenance(recs, BASELINE)
    assert m["as_of_date"] == LATEST.isoformat()
    assert m["stations"] == [
        {"station_id": "S2", "num_bikes_disabled": 7, "action": "inspect and collect broken bikes"},
        {"station_id": "S4", "num_bikes_disabled": 7, "action": "inspect and collect broken bikes"},
        {"station_id": "S1", "num_bikes_disabled": 2, "action": "inspect and collect broken bikes"},
    ]  # S3 has no broken bikes, so it is not listed


def test_stale_station_list_is_flagged():
    recs = ten_day_records()
    recs = [r for r in recs if r["timestamp"].date() != LATEST]
    recs += [snap(LATEST, "07:30", "S1", 40, 2)]  # the latest day has data, but no 07:00 snapshot
    m = build_maintenance(recs, BASELINE)
    assert m["as_of_date"] == BASELINE[-1].isoformat()
    assert any("stale" in w for w in m["warnings"])


def test_output_shape_and_records_unchanged():
    recs = ten_day_records()
    before = copy.deepcopy(recs)
    m = build_maintenance(recs, BASELINE)
    assert recs == before
    assert set(m) == {"chart", "stations", "as_of_date", "warnings"}
    assert set(m["chart"]) == {"baseline_dates", "p_bar", "points", "warnings"}
    assert {"date", "p_bar", "d", "n", "ucl", "lcl", "status"} <= set(m["chart"]["points"][0])
