"""The one statistic: a p-chart with exact binomial control limits (task H-03).

    p_chart(baseline=[(d, n), ...], observations=[(d, n), ...]) -> dict

Every pair is (d, n): d defective units out of n inspected. For this tool a
"unit" is a five-minute snapshot (availability) or a docked bike (maintenance),
but this function knows nothing about bikes, dates, HTTP or the ten-day
baseline rule; the report modules apply those.

Method (SPEC.md section 4):
    p_bar = sum(baseline d) / sum(baseline n)
    For a subgroup of size n and X ~ Binomial(n, p_bar), alpha = 0.00135:
        upper count u = min{k in 0..n : P(X > k) <= alpha}  -> flagged high when d > u
        lower count l = max{k in 0..n : P(X < k) <= alpha}  -> flagged low  when d < l
        UCL = u / n,  LCL = l / n
    Western Electric rule 1 only: a point beyond a limit. A point exactly on a
    count limit is not flagged.

Exact tails come from scipy.stats.binom (sf and cdf), never from the normal
approximation p_bar +/- 3 sqrt(p_bar (1 - p_bar) / n), which needs n * p_bar >= 5.
"""

from __future__ import annotations

from scipy.stats import binom

ALPHA = 0.00135  # one-sided tail area beyond 3 sigma on a normal curve

STATUS_OK = "ok"
STATUS_NO_DATA = "no_data"
STATUS_INSUFFICIENT = "insufficient_basis"


def _check_pair(pair, where: str) -> tuple[int, int]:
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        raise ValueError(f"{where}: expected a (d, n) pair, got {pair!r}")
    d, n = pair
    for name, value in (("d", d), ("n", n)):
        if value is None:
            raise ValueError(f"{where}: {name} is missing")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{where}: {name} must be a whole number, got {value!r}")
        if value < 0:
            raise ValueError(f"{where}: {name} must not be negative, got {value}")
    if d > n:
        raise ValueError(f"{where}: d = {d} is larger than n = {n}")
    return d, n


def count_limits(n: int, p_bar: float, alpha: float = ALPHA) -> tuple[int, int]:
    """Exact binomial (lower count l, upper count u) for a subgroup of size n.

    u is the smallest k in 0..n with P(X > k) <= alpha; l is the largest k in
    0..n with P(X < k) <= alpha, where X ~ Binomial(n, p_bar). Needs n >= 1 and
    0 < p_bar < 1.
    """
    if n < 1 or not 0 < p_bar < 1:
        raise ValueError(f"limits need n >= 1 and 0 < p_bar < 1, got n={n}, p_bar={p_bar}")
    upper = next(k for k in range(n + 1) if binom.sf(k, n, p_bar) <= alpha)  # sf(k) = P(X > k)
    lower = max(k for k in range(n + 1) if binom.cdf(k - 1, n, p_bar) <= alpha)  # cdf(k-1) = P(X < k)
    return lower, upper


def p_chart(baseline: list[tuple[int, int]], observations: list[tuple[int, int]]) -> dict:
    """Exact binomial p-chart.

    Parameters
    ----------
    baseline : list of (d, n)
        Subgroups from a period of normal operation. Groups with n = 0 are left
        out of p_bar (they carry no exposure).
    observations : list of (d, n)
        Subgroups to judge against the baseline limits, in display order. They
        may include the baseline groups themselves.

    Returns
    -------
    dict
        ``{"p_bar", "points", "warnings"}``. ``p_bar`` is a float, or None when
        the baseline has no exposure. ``points`` has one dict per observation, in
        input order, with ``d, n, p, lower_count, upper_count, lcl, ucl,
        flagged_high, flagged_low, status, warnings``. ``status`` is ``"ok"``
        (limits drawn), ``"no_data"`` (n = 0: p and limits are None) or
        ``"insufficient_basis"`` (p_bar is None, 0 or 1: no limits can be drawn,
        so nothing is flagged). Unavailable numbers are None, never NaN, inf or
        an invented 0.

    Raises
    ------
    ValueError
        A pair that is not two whole numbers, a missing (None) or negative
        count, a bool, or d > n.
    """
    base = [_check_pair(p, f"baseline group {i + 1}") for i, p in enumerate(baseline)]
    obs = [_check_pair(p, f"observation {i + 1}") for i, p in enumerate(observations)]

    warnings = []
    dropped = sum(1 for _, n in base if n == 0)
    if dropped:
        warnings.append(f"{dropped} baseline group(s) with n = 0 left out of p_bar")
    total_d = sum(d for d, n in base if n > 0)
    total_n = sum(n for _, n in base if n > 0)

    if total_n == 0:
        p_bar = None
        basis_problem = "no baseline exposure (total baseline n = 0): insufficient basis for control limits"
    else:
        p_bar = total_d / total_n
        if p_bar == 0:
            basis_problem = "p_bar = 0 (never defective in the baseline): insufficient basis for control limits"
        elif p_bar == 1:
            basis_problem = "p_bar = 1 (always defective in the baseline): insufficient basis for control limits"
        else:
            basis_problem = None
    if basis_problem:
        warnings.append(basis_problem)

    points = []
    for d, n in obs:
        point = {
            "d": d, "n": n, "p": None,
            "lower_count": None, "upper_count": None, "lcl": None, "ucl": None,
            "flagged_high": False, "flagged_low": False,
            "status": STATUS_OK, "warnings": [],
        }
        if n == 0:
            point["status"] = STATUS_NO_DATA
            point["warnings"].append("n = 0: no data for this subgroup")
        else:
            point["p"] = d / n
            if basis_problem:
                point["status"] = STATUS_INSUFFICIENT
                point["warnings"].append(basis_problem)
            else:
                lower, upper = count_limits(n, p_bar)
                point.update(
                    lower_count=lower, upper_count=upper, lcl=lower / n, ucl=upper / n,
                    flagged_high=d > upper, flagged_low=d < lower,
                )
        points.append(point)
    return {"p_bar": p_bar, "points": points, "warnings": warnings}
