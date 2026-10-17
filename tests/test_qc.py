"""Tests for app/qc.py: every SPEC.md section 4 hand answer, plus degenerate cases.

Run from the repo root:  python -m pytest tests/test_qc.py -q
Expected numbers were worked by hand in SPEC.md; binomial tails are also
re-derived here from math.comb, independently of scipy.
"""

from math import comb

import pytest

from app.qc import ALPHA, count_limits, p_chart

AVAIL_BASELINE = [(2, 24), (4, 24), (3, 24), (3, 24)]  # p_bar = 12 / 96 = 0.125
MAINT_BASELINE = [(10, 100)]  # p_bar = 0.10


def upper_tail(k, n, p):
    """P(X >= k) from the binomial formula, no scipy."""
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


# ---- the hand-worked tail probabilities themselves ------------------------------

def test_hand_tail_probabilities_from_spec():
    assert upper_tail(10, 24, 0.125) == pytest.approx(0.0003419882809, abs=1e-12)
    assert upper_tail(9, 24, 0.125) == pytest.approx(0.001656468148, abs=1e-11)
    assert upper_tail(21, 100, 0.10) == pytest.approx(0.000808, abs=5e-7)
    assert upper_tail(20, 100, 0.10) == pytest.approx(0.001979, abs=5e-7)
    assert 1 - upper_tail(2, 100, 0.10) == pytest.approx(0.000322, abs=5e-7)  # P(X <= 1)
    assert 0.875**24 == pytest.approx(0.0406, abs=5e-5)  # P(X = 0) for n = 24


# ---- availability known answer: p_bar = 0.125 ----------------------------------

def test_availability_p_bar():
    assert p_chart(AVAIL_BASELINE, [])["p_bar"] == pytest.approx(0.125)


def test_availability_limits_n24_and_n20():
    assert count_limits(24, 0.125) == (0, 9)
    assert count_limits(20, 0.125) == (0, 8)
    pts = p_chart(AVAIL_BASELINE, [(0, 24), (0, 20)])["points"]
    assert (pts[0]["lower_count"], pts[0]["upper_count"]) == (0, 9)
    assert pts[0]["ucl"] == pytest.approx(0.375) and pts[0]["lcl"] == 0
    assert (pts[1]["lower_count"], pts[1]["upper_count"]) == (0, 8)
    assert pts[1]["ucl"] == pytest.approx(0.40)


def test_availability_d10_flags_high_and_d8_does_not():
    d10, d8 = p_chart(AVAIL_BASELINE, [(10, 24), (8, 24)])["points"]
    assert d10["p"] == pytest.approx(10 / 24) and d10["flagged_high"] and not d10["flagged_low"]
    assert d8["p"] == pytest.approx(8 / 24) and not d8["flagged_high"]
    # The normal-approximation UCL 0.327523 would wrongly flag d = 8.
    assert d8["p"] > 0.327523


def test_availability_no_day_can_flag_low():
    point = p_chart(AVAIL_BASELINE, [(0, 24)])["points"][0]
    assert point["lower_count"] == 0 and not point["flagged_low"] and point["status"] == "ok"


def test_equality_at_the_upper_count_is_not_flagged():
    at_limit, above = p_chart(AVAIL_BASELINE, [(9, 24), (8, 20)])["points"]
    assert not at_limit["flagged_high"] and not above["flagged_high"]


def test_changed_n_changes_the_limit_not_the_p_bar():
    chart = p_chart(AVAIL_BASELINE, [(9, 24), (9, 20)])
    on_24, on_20 = chart["points"]
    assert not on_24["flagged_high"]  # 9 <= u = 9
    assert on_20["flagged_high"]  # 9 > u = 8
    assert chart["p_bar"] == pytest.approx(0.125)


# ---- maintenance known answer: p_bar = 0.10 -------------------------------------

def test_maintenance_limits():
    assert count_limits(100, 0.10) == (2, 20)
    point = p_chart(MAINT_BASELINE, [(10, 100)])["points"][0]
    assert point["lcl"] == pytest.approx(0.02) and point["ucl"] == pytest.approx(0.20)


def test_maintenance_flags():
    d25, d20, d2, d1, d0 = p_chart(MAINT_BASELINE, [(25, 100), (20, 100), (2, 100), (1, 100), (0, 100)])["points"]
    assert d25["flagged_high"]
    assert not d20["flagged_high"] and not d20["flagged_low"]  # equality at u = 20
    assert not d2["flagged_low"]  # equality at l = 2
    assert d1["flagged_low"] and d0["flagged_low"]
    assert not d1["flagged_high"]


def test_limits_satisfy_their_definition_against_independent_tails():
    for n, p in [(24, 0.125), (20, 0.125), (100, 0.10), (200, 0.10), (24, 0.30), (7, 0.5)]:
        lower, upper = count_limits(n, p)
        assert upper_tail(upper + 1, n, p) <= ALPHA  # P(X > u) <= alpha
        assert upper == 0 or upper_tail(upper, n, p) > ALPHA  # and u is the smallest such
        assert 1 - upper_tail(lower, n, p) <= ALPHA  # P(X < l) <= alpha
        assert lower == n or 1 - upper_tail(lower + 1, n, p) > ALPHA  # and l is the largest


# ---- output shape ------------------------------------------------------------------

def test_points_keep_input_order_and_have_every_field():
    chart = p_chart(AVAIL_BASELINE, [(1, 24), (0, 0), (10, 24)])
    assert set(chart) == {"p_bar", "points", "warnings"}
    assert [p["d"] for p in chart["points"]] == [1, 0, 10]
    for point in chart["points"]:
        assert set(point) == {"d", "n", "p", "lower_count", "upper_count", "lcl", "ucl",
                              "flagged_high", "flagged_low", "status", "warnings"}


# ---- degenerate cases ---------------------------------------------------------------

@pytest.mark.parametrize("baseline, word", [([(0, 24), (0, 24)], "p_bar = 0"), ([(24, 24), (20, 20)], "p_bar = 1")])
def test_p_bar_zero_or_one_gives_no_limits(baseline, word):
    chart = p_chart(baseline, [(3, 24)])
    point = chart["points"][0]
    assert any(word in w for w in chart["warnings"])
    assert point["status"] == "insufficient_basis"
    assert point["p"] == pytest.approx(3 / 24)  # the measurement itself is still shown
    assert point["lcl"] is None and point["ucl"] is None
    assert point["lower_count"] is None and point["upper_count"] is None
    assert not point["flagged_high"] and not point["flagged_low"]
    assert point["warnings"]


def test_zero_n_observation_is_no_data():
    point = p_chart(AVAIL_BASELINE, [(0, 0)])["points"][0]
    assert point["status"] == "no_data"
    assert point["p"] is None and point["ucl"] is None and point["lcl"] is None
    assert not point["flagged_high"] and not point["flagged_low"]
    assert "n = 0" in point["warnings"][0]


def test_zero_n_baseline_groups_are_left_out_of_p_bar():
    chart = p_chart([*AVAIL_BASELINE, (0, 0)], [(10, 24)])
    assert chart["p_bar"] == pytest.approx(0.125)
    assert any("n = 0" in w for w in chart["warnings"])
    assert chart["points"][0]["flagged_high"]


@pytest.mark.parametrize("baseline", [[], [(0, 0), (0, 0)]])
def test_no_baseline_exposure_is_insufficient_basis(baseline):
    chart = p_chart(baseline, [(2, 24)])
    assert chart["p_bar"] is None
    assert chart["points"][0]["status"] == "insufficient_basis"
    assert not chart["points"][0]["flagged_high"]


@pytest.mark.parametrize(
    "pair",
    [(True, 24), (2, False), (2.0, 24), (2, 24.5), (None, 24), (2, None), (-1, 24), (2, -24), (25, 24), (2,), "2,24"],
)
def test_invalid_counts_raise(pair):
    with pytest.raises(ValueError):
        p_chart([pair], [])
    with pytest.raises(ValueError):
        p_chart(AVAIL_BASELINE, [pair])


def test_count_limits_refuse_undefined_cases():
    for n, p in [(0, 0.1), (24, 0.0), (24, 1.0)]:
        with pytest.raises(ValueError):
            count_limits(n, p)


def test_no_nan_or_infinity_anywhere():
    import json

    chart = p_chart([(0, 24)], [(0, 0), (3, 24)])
    json.dumps(chart, allow_nan=False)  # raises if a NaN or inf slipped in
