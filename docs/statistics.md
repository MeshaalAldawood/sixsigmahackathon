# Statistics: the exact binomial p-chart

The tool computes **one statistic**, a p-chart (a control chart for a proportion) with **exact
binomial control limits**. It lives in one plain function, `p_chart` in
[`app/qc.py`](../app/qc.py), tested in [`tests/test_qc.py`](../tests/test_qc.py). The
availability and maintenance modules only build the counts and call it; no statistic is
computed anywhere else, including the browser.

## What goes in

Pairs `(d, n)`: `d` defective units out of `n` inspected.

| Use | One subgroup is | n | d |
|---|---|---|---|
| Availability ([`availability.md`](availability.md)) | one station, one weekday, one rush window | five-minute snapshots logged (24, fewer if some are missing) | snapshots that were empty or full |
| Maintenance ([`maintenance.md`](maintenance.md)) | the whole network at 07:00 on one weekday | docked bikes (available + broken) | broken bikes |

`p_chart(baseline, observations)` takes the baseline subgroups (normal operation, used to set
the limits) and the subgroups to judge (in display order; they may include the baseline days).

## The method

1. **Center line:** `p_bar = sum(baseline d) / sum(baseline n)`. Baseline groups with `n = 0`
   carry no exposure and are left out, with a warning.
2. **Limits for each subgroup**, from `X ~ Binomial(n, p_bar)` and `alpha = 0.00135`, the tail
   area beyond 3 sigma on a normal curve:
   - upper count `u` = the smallest `k` in `0..n` with `P(X > k) <= alpha`;
   - lower count `l` = the largest `k` in `0..n` with `P(X < k) <= alpha`;
   - `UCL = u / n`, `LCL = l / n`. The limits move with `n`, so a day with missing snapshots
     gets slightly wider limits.
3. **Rule:** Western Electric rule 1 only. A subgroup is **flagged high** when `d > u` and
   **flagged low** when `d < l`. A point exactly on a count limit is not flagged.

The tails come from `scipy.stats.binom`: `P(X > k)` is `binom.sf(k, n, p_bar)` and `P(X < k)` is
`binom.cdf(k - 1, n, p_bar)`. Every integer `k` is checked; nothing is interpolated.

### Why exact limits, not the usual formula

The textbook limits `p_bar +/- 3 sqrt(p_bar (1 - p_bar) / n)` lean on a normal approximation
that needs roughly `n * p_bar >= 5`. One station's rush window has `n = 24` snapshots, so
`n * p_bar` is usually below 5 (from 0.3 to 6.3 across the demo data's stations): the normal limits
would sit in the wrong place. Exact binomial limits need no such condition. The known answer below shows a case
where the two disagree.

## What comes out

`{"p_bar", "points", "warnings"}`. Each point has `d, n, p, lower_count, upper_count, lcl, ucl,
flagged_high, flagged_low, status, warnings`.

| `status` | When | What the point carries |
|---|---|---|
| `ok` | limits could be drawn | `p`, both counts, both limits, both flags |
| `no_data` | this subgroup has `n = 0` | `p` and limits are `null`; never flagged |
| `insufficient_basis` | `p_bar` is unavailable (no baseline exposure), 0 or 1 | `p` is shown; limits are `null`; never flagged |

Unavailable numbers are JSON `null`, never `NaN`, infinity or an invented 0. Invalid input
(a bool, a non-integer, a missing or negative count, `d > n`, anything that is not a pair)
raises `ValueError` naming the group.

The rule that a chart needs **ten positive-n baseline days** is applied by the report modules,
not here, so the four-day hand fixture below still exercises the arithmetic.

## Known answers (reproduced by `tests/test_qc.py`)

**Availability:** baseline `d = 2, 4, 3, 3`, each `n = 24`, so `p_bar = 12 / 96 = 0.125`.

| Quantity | Hand value | Why |
|---|---|---|
| upper count, n = 24 | `u = 9`, `UCL = 0.375` | `P(X >= 10) = 0.0003420 <= 0.00135`, `P(X >= 9) = 0.0016565 > 0.00135` |
| lower count, n = 24 | `l = 0`, `LCL = 0` | `P(X = 0) = 0.875^24 = 0.0406 > 0.00135`, so no day can flag low |
| upper count, n = 20 | `u = 8`, `UCL = 0.40` | fewer snapshots, wider limit |
| a day with d = 10 of 24 | `p = 0.4167`, **flagged high** | `10 > 9` |
| a day with d = 8 of 24 | `p = 0.3333`, not flagged | `8 <= 9`; the normal UCL `0.3275` would wrongly flag it |

**Maintenance:** baseline 10 broken of 100 docked bikes, `p_bar = 0.10`, `n = 100`.

| Quantity | Hand value | Why |
|---|---|---|
| upper count | `u = 20`, `UCL = 0.20` | `P(X >= 21) = 0.000808`, `P(X >= 20) = 0.001979` |
| lower count | `l = 2`, `LCL = 0.02` | `P(X <= 1) = 0.000322`, `P(X <= 2) > 0.00135` |
| 25 of 100 | **flagged high** | `25 > 20` |
| 20 of 100 | not flagged | equality at `u` |
| 0 or 1 of 100 | **flagged low** | `d < 2`: fewer bikes broke than normal |

Cross-check any tail in R with `1 - pbinom(k, n, p)` (that is `P(X > k)`), or in Python with
`scipy.stats.binom.sf(k, n, p)`. The tests also re-derive every tail from `math.comb`, without
scipy.

## Assumptions, and why every signal is "exploratory"

- **Independence.** The binomial model treats each snapshot (or bike) as an independent trial.
  Snapshots are not independent: a station empty at 07:35 is likely still empty at 07:40, so
  unusable snapshots arrive in clumps. Real false-alarm rates are therefore higher than
  `alpha`, and the page labels every control-chart signal **exploratory**. The demo
  ([`demo/README.md`](../demo/README.md)) reports how many points flag on the stable dataset.
- **A stable baseline.** Limits come only from the baseline days, never from days that contain
  the event to detect. If the baseline itself was abnormal, the limits are too.
- **Limits are not targets.** The 0.10 unusable-share target comes from the city's
  service-level agreement. A station can be in control (only common-cause variation) and still
  above the target every day; that is a capacity problem, not a special cause.
- **No causal claim.** A flag says this day was unusual compared with the baseline, not why.
