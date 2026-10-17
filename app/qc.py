"""Exact binomial p-chart arithmetic shared by the two bikeshare reports.

The caller chooses the frozen baseline and supplies subgroup (defects, trials)
counts. This module deliberately does not decide which days form that baseline.
"""

from collections.abc import Iterable, Mapping
from numbers import Integral

from scipy.stats import binom


ALPHA = 0.00135
INSUFFICIENT = "insufficient basis for control limits"


def _counts(value, label):
    """Validate one subgroup while retaining its position in error messages."""
    if isinstance(value, Mapping):
        try:
            defects, trials = value["d"], value["n"]
        except KeyError as exc:
            raise ValueError(f"{label}: missing {exc.args[0]} count") from exc
    else:
        try:
            defects, trials = value
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: expected a (d, n) pair") from exc
    for name, count in (("d", defects), ("n", trials)):
        if isinstance(count, bool) or not isinstance(count, Integral):
            raise ValueError(f"{label}: {name} must be an integer")
        if count < 0:
            raise ValueError(f"{label}: {name} must be non-negative")
    if defects > trials:
        raise ValueError(f"{label}: d cannot exceed n")
    return int(defects), int(trials)


def _limits(n, p_bar, alpha):
    """Find inclusive boundary counts with exact binomial tail probabilities.

    High flags require d > u; low flags require d < l. Binary searches avoid
    depending on discrete quantile rounding conventions at an exact boundary.
    """
    lo, hi = 0, n
    while lo < hi:
        middle = (lo + hi) // 2
        if binom.sf(middle, n, p_bar) <= alpha:
            hi = middle
        else:
            lo = middle + 1
    upper = lo

    lo, hi = 0, n
    while lo < hi:
        middle = (lo + hi + 1) // 2
        if binom.cdf(middle - 1, n, p_bar) <= alpha:
            lo = middle
        else:
            hi = middle - 1
    lower = lo
    return lower, upper


def p_chart(
    baseline: Iterable[tuple[int, int]],
    observations: Iterable[tuple[int, int]],
    *,
    alpha: float = ALPHA,
) -> dict:
    """Return an exact p-chart for subgroup (d, n) pairs.

    Baseline rows with no exposure are ignored. Observed rows with n=0 remain
    in place with null values and a warning, so a caller can retain dates.
    Fewer-than-ten-baseline-day policy belongs to the report, allowing direct
    verification of the four-day hand example in SPEC.md.
    """
    if not 0 < alpha < 1 or isinstance(alpha, bool):
        raise ValueError("alpha must be between 0 and 1")
    baseline_counts = [_counts(value, f"baseline row {i}") for i, value in enumerate(baseline, 1)]
    observed_counts = [
        _counts(value, f"observation row {i}") for i, value in enumerate(observations, 1)
    ]

    warnings = []
    baseline_nonzero = [(d, n) for d, n in baseline_counts if n > 0]
    if len(baseline_nonzero) != len(baseline_counts):
        warnings.append("baseline subgroups with n=0 were dropped")
    total_n = sum(n for _, n in baseline_nonzero)
    p_bar = sum(d for d, _ in baseline_nonzero) / total_n if total_n else None
    has_limits = p_bar is not None and 0 < p_bar < 1
    if not has_limits:
        warnings.append(INSUFFICIENT)

    points = []
    for d, n in observed_counts:
        point_warnings = []
        if n == 0:
            point_warnings.append("subgroup has n=0; no observed share or control limits")
        elif not has_limits:
            point_warnings.append(INSUFFICIENT)
        lower, upper = _limits(n, p_bar, alpha) if n and has_limits else (None, None)
        high = upper is not None and d > upper
        low = lower is not None and d < lower
        points.append(
            {
                "d": d,
                "n": n,
                "p": d / n if n else None,
                "lower_count": lower,
                "upper_count": upper,
                "lcl": lower / n if lower is not None else None,
                "ucl": upper / n if upper is not None else None,
                "flagged_high": high,
                "flagged_low": low,
                "status": "no_data" if n == 0 else "insufficient_basis" if not has_limits else "high" if high else "low" if low else "in_control",
                "warnings": point_warnings,
            }
        )
    return {"p_bar": p_bar, "points": points, "warnings": warnings}
