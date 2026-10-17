# Statistical method

The two reports use one exact binomial p-chart calculation in `app/qc.py`.
For baseline subgroup counts `(d, n)`, the center line is
`p_bar = sum(d) / sum(n)`. The baseline is selected by the report and remains
fixed when later days are examined. The chart function accepts a four-day
baseline for the worked arithmetic; the reports require ten baseline weekdays
before presenting control limits.

For each observed subgroup with `n > 0`, let `X ~ Binomial(n, p_bar)` and
`alpha = 0.00135`. The upper boundary `u` is the smallest integer with
`P(X > u) <= alpha`; the lower boundary `l` is the largest integer with
`P(X < l) <= alpha`. `UCL = u/n` and `LCL = l/n`. Western Electric rule 1 is
the only signal rule: `d > u` flags high and `d < l` flags low. A point equal
to a boundary is in control. SciPy's exact `binom.sf` and `binom.cdf` evaluate
the tails; the normal three-sigma approximation is not used because a station
window often has only one to four expected unusable snapshots.

In availability, `d` counts snapshots with zero available bikes or zero
available docks; `n` counts snapshots actually observed in one station,
weekday and AM or PM rush window. The two windows have separate baselines.
In maintenance, `d` is disabled docked bikes and `n` is all docked bikes in
the network at exactly 07:00, one point per weekday. The city's 0.10 unusable
share is a service target, not a control limit.

The hand case with baseline `d=(2,4,3,3)` and `n=24` each gives `p_bar=.125`,
`u=9` and `UCL=.375` at `n=24`, or `u=8` and `UCL=.40` at `n=20`; `d=10` at
`n=24` flags high, while `d=8` does not. For maintenance `p_bar=.10` at
`n=100`, `l=2`, `u=20`, `LCL=.02` and `UCL=.20`; `d=25` flags high, `d=20`
does not, and `d=1` flags low. Tests also check missing exposure and
degenerate baselines.

No limits are estimated when baseline exposure is zero or `p_bar` is exactly
zero or one. A subgroup with `n=0` has no observed share or limits and is
marked missing. Invalid counts are rejected with the subgroup row number.

Snapshots within one rush window are serially correlated: an empty station
often remains empty five minutes later. The binomial independence assumption
therefore understates real false-alarm rates. Every chart signal must be
labelled **exploratory**; it is a prompt for investigation, not proof of an
unusual cause. Control limits describe baseline variation and do not imply
that a station meets the service target.
