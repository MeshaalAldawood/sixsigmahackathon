# Morning maintenance report

`build_maintenance(records, baseline_dates)` accepts validated station snapshots
and a frozen list of the first ten baseline weekdays. It returns `chart`,
`stations`, `as_of_date`, and `warnings`. The report uses **exactly 07:00 local
time** on weekdays. A 07:05 or evening row never contributes to maintenance.
The caller can pass records cut off at a simulated current time; the function
does not create future observations from baseline dates.

For each weekday, the network subgroup has `d = sum(num_bikes_disabled)` and
`n = sum(num_bikes_available + num_bikes_disabled)` over the stations observed
at 07:00. A missing station is absent from both sums. The chart points include
`date`, `d`, `n`, `p`, exact binomial lower and upper counts, `lcl`, `ucl`,
signal flags, status, and point warnings. `p_bar` uses only the ten baseline
weekday subgroups and remains fixed for later dates. `baseline_dates` and
`baseline_observed_days` expose the baseline coverage. A weekday with other
snapshots but no docked bikes at 07:00 has `n=0`, a null share and null limits.

The exact chart uses `alpha=0.00135` in each tail and Western Electric rule 1
only. With baseline broken share 10/100, an observed 25/100 point has lower
count 2, upper count 20, limits 0.02 and 0.20, and a high signal; 20/100 is
inside the boundary. Limits are withheld unless all ten baseline weekdays
have positive exposure, and when baseline `p_bar` is zero or one. The report
warns `insufficient basis for control limits` in those cases. Signals are
exploratory because counts of docked bikes may be dependent and the baseline
may not describe all operating conditions.

`as_of_date` is the most recent date with a 07:00 snapshot. `stations` uses
only that date, includes stations with at least one disabled bike, and sorts by
disabled bikes descending then `station_id`. Every row says `inspect and
collect broken bikes`. The list is a collection priority, not a route or
repair time estimate.

In replay, the source is cut at the requested time before aggregation. The
calibration share and limits remain hidden until the original tenth baseline
weekday reaches 18:00. `measurement_timestamp` names the exact 07:00 source
measurement behind the list; `observed_stations_at_0700` and
`expected_stations_at_0700` report station coverage among stations seen so far.
`stale` and a warning mark a previous day's measurement when the visible day
has no exact 07:00 row. A 07:05 row never substitutes for 07:00. The point's
`n` is the actual docked-bike count of observed 07:00 stations, not an imputed
network total.
