"""Hand-calculated checks from SPEC.md, plus degenerate chart inputs."""

import math

import pytest

from app.qc import p_chart


def test_availability_hand_answer_and_varying_exposure():
    chart = p_chart([(2, 24), (4, 24), (3, 24), (3, 24)], [(10, 24), (8, 24), (8, 20)])
    assert chart["p_bar"] == 0.125
    high, boundary, short = chart["points"]
    assert (high["lower_count"], high["upper_count"], high["lcl"], high["ucl"]) == (0, 9, 0, 0.375)
    assert high["p"] == pytest.approx(10 / 24)
    assert high["flagged_high"] and high["status"] == "high"
    assert boundary["p"] == pytest.approx(8 / 24)
    assert not boundary["flagged_high"]
    assert (short["upper_count"], short["ucl"]) == (8, 0.4)
    assert not short["flagged_high"]  # equality at the count boundary


def test_maintenance_hand_answer_and_lower_boundary():
    points = p_chart([(10, 100)], [(25, 100), (20, 100), (1, 100), (2, 100)])["points"]
    assert all((point["lower_count"], point["upper_count"], point["lcl"], point["ucl"]) == (2, 20, 0.02, 0.2) for point in points)
    assert [point["status"] for point in points] == ["high", "in_control", "low", "in_control"]
    assert [point["flagged_low"] for point in points] == [False, False, True, False]


@pytest.mark.parametrize("baseline,expected", [([(0, 24)], 0.0), ([(24, 24)], 1.0)])
def test_degenerate_baseline_has_no_invented_limits(baseline, expected):
    chart = p_chart(baseline, [(0, 24), (24, 24)])
    assert chart["p_bar"] == expected
    assert "insufficient basis for control limits" in chart["warnings"]
    assert all(point["lcl"] is None and point["ucl"] is None for point in chart["points"])
    assert all(not point["flagged_high"] and not point["flagged_low"] for point in chart["points"])


def test_empty_baseline_and_missing_exposure():
    chart = p_chart([(0, 0)], [(0, 0), (0, 1)])
    assert chart["p_bar"] is None
    assert chart["points"][0]["p"] is None
    assert chart["points"][0]["status"] == "no_data"
    assert chart["points"][1]["status"] == "insufficient_basis"
    assert "baseline subgroups with n=0 were dropped" in chart["warnings"]
    assert all(point["ucl"] is None for point in chart["points"])


@pytest.mark.parametrize(
    "baseline,observed,match",
    [
        ([(1, -1)], [(1, 1)], "baseline row 1: n must be non-negative"),
        ([(2, 1)], [(1, 1)], "baseline row 1: d cannot exceed n"),
        ([(1.5, 2)], [(1, 1)], "baseline row 1: d must be an integer"),
        ([(None, 2)], [(1, 1)], "baseline row 1: d must be an integer"),
        ([(1, 2)], [(None, 2)], "observation row 1: d must be an integer"),
        ([(1, 2)], [(True, 2)], "observation row 1: d must be an integer"),
        ([(1, 2)], [(2, 1)], "observation row 1: d cannot exceed n"),
    ],
)
def test_invalid_counts_are_rejected_with_row(baseline, observed, match):
    with pytest.raises(ValueError, match=match):
        p_chart(baseline, observed)


def test_binomial_tails_and_no_normal_approximation():
    from scipy.stats import binom

    assert binom.sf(9, 24, 0.125) <= 0.00135 < binom.sf(8, 24, 0.125)
    assert binom.sf(20, 100, 0.10) <= 0.00135 < binom.sf(19, 100, 0.10)
    assert binom.cdf(1, 100, 0.10) <= 0.00135 < binom.cdf(2, 100, 0.10)
    normal_ucl = 0.125 + 3 * math.sqrt(0.125 * 0.875 / 24)
    assert normal_ucl < 8 / 24 < p_chart([(2, 24), (4, 24), (3, 24), (3, 24)], [(8, 24)])["points"][0]["ucl"]
