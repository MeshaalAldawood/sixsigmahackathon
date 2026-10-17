# Availability: Decision A (which stations need a van)

Module: [`app/availability.py`](../app/availability.py). Tests:
[`tests/test_availability.py`](../tests/test_availability.py). The statistic itself is the
exact binomial p-chart in [`app/qc.py`](../app/qc.py) ([statistics.md](statistics.md)); this
module only counts snapshots and applies the dispatch rules.

```python
build_availability(records, baseline_dates, target=0.10)
# -> {"AM": {"stations": [...], "charts": {...}, "warnings": [...]}, "PM": {...}}
```

`records` are the validated rush-window rows from `app/data_loader.py`; they are never changed.
`baseline_dates` are the first ten retained weekdays, chosen once by the API for every chart.

## Subgroups

- **One subgroup = one station, one weekday, one rush window.** AM (07:00-08:55) and PM
  (16:00-17:55) are separate charts, because a residential station empties in the morning and
  fills in the evening; mixing them would hide both.
- **n** = snapshots actually logged in that window (24, fewer when snapshots are missing; a
  missing snapshot is never filled in).
- **d** = unusable snapshots: `num_bikes_available == 0` (empty) **or** `num_docks_available == 0`
  (full). A snapshot that is both counts once in `d`, and once in each of the two descriptive
  counts `empty_count` and `full_count`.
- Limits come from the baseline days only, and a chart needs **ten baseline days with data**.
  With fewer, every point is `insufficient_basis`: no limits, no flags, a warning.
- A day with no snapshots in a window is not plotted; the chart carries a dated warning instead.

## Chart (`charts[station_id]`)

`{baseline_dates, p_bar, points, warnings}`. Each point is a `qc.p_chart` point plus its ISO
`date` and the chart's `p_bar`: `d, n, p, lower_count, upper_count, lcl, ucl, flagged_high,
flagged_low, status, warnings`. Every retained day with data is plotted, so the historical stadium
event (day 12) stays visible even though the dispatch table describes day 15.

## Dispatch table (`stations`)

One row per station for the **latest retained day** (the same day for every station):

| Field | Meaning |
|---|---|
| `station_id`, `date` | the station and the latest day |
| `n`, `d`, `p` | snapshots logged, unusable snapshots, share unusable (`null` if n = 0) |
| `empty_count`, `full_count` | empty snapshots and full snapshots that day, kept separate |
| `p_bar`, `lcl`, `ucl` | the station's center line and that day's limits (`null` without a basis) |
| `flagged_high`, `flagged_low`, `status` | from the p-chart; `status` is `ok`, `no_data` or `insufficient_basis` |
| `empty_onset`, `full_onset` | typical first empty / full time (below) |
| `action`, `action_rank` | what the van should do; rank 0 = act, 1 = nothing to do or no data |
| `warnings` | anything that limits what the row can claim |

Rows are sorted by `(action_rank, station_id)`: everything that needs action first, then
alphabetical, so the order never depends on chance.

### Actions: SPEC section 4, first match wins

1. **No snapshots that day** -> "no data for the latest day" (rank 1). Missing data is never "OK".
2. The station was **full at a snapshot while holding broken bikes** -> "collect broken bikes
   first": broken bikes are taking docks, so pulling working bikes would not help.
3. **Flagged high** (valid limits) -> "investigate: special cause", plus the van direction from
   rule 5 when there is one.
4. **In control** (valid limits, neither flag) **and p_bar above the target** (strictly greater
   than 0.10) -> "capacity review: unusable every day". A van will not fix a station that is
   unusable every day; it needs more docks or a standing rebalancing slot.
5. **More empty than full snapshots** -> "van: drop bikes before HH:MM"; **more full than empty**
   -> "van: pull bikes before HH:MM", where HH:MM is the typical first-empty (or first-full)
   time. A tie gives no direction.
6. Otherwise "OK" (rank 1), or, when the chart has no limits, "no action needed today; no control
   limits (insufficient basis)", so a missing basis is never presented as in control.

Missing limits block rules 3 and 4 (no special-cause or capacity claim without a basis) but not
rules 2 and 5, which only use the day's measured counts.

### Typical first-unusable time (`empty_onset`, `full_onset`)

For each baseline day with data, take the clock time of the first empty (or full) snapshot. The
typical time is the **median over the days on which it happened**; with an even number of days it
is the mean of the two middle times, rounded **down** to the minute, so the deadline shown is never
later than the data. Each onset is `{time, affected_days, observed_days, text}`, for example
`{"time": "07:40", "affected_days": 3, "observed_days": 10, "text": "usually empty by 07:40, on 3 of 10 baseline days"}`.
If it never happened in the baseline, `time` is `null` and the text is "baseline timing
unavailable"; the direction is still given, without a deadline.

## The 0.10 target is not a control limit

The target comes from the city's service-level agreement. The control limits come from the data
and describe what the station normally does. A station can sit inside its limits and still miss
the target every day (common cause: S07 in the test data), and a station can flag above its limits
on a day that is still under the target. The table keeps the two ideas apart.

## Known answers (from `tests/test_availability.py`)

| Case | Result |
|---|---|
| baseline d = 2, 4, 3, 3, 3, 3, 3, 3, 3, 3 of 24 (p_bar = 0.125); latest d = 10 of 24 | UCL 0.375, flagged high, "investigate: special cause; van: drop bikes before 08:45" |
| same baseline, latest d = 8 | not flagged (the normal formula would flag it); "capacity review", since 0.125 > 0.10 |
| latest day with 4 missing snapshots, 7 empty of 20 | n = 20, UCL 0.40 |
| baseline p_bar exactly 0.10 | no capacity review: the rule is strictly greater |
| baseline first-empty times 07:35, 07:40, 07:50 on 3 of 10 days | "usually empty by 07:40, on 3 of 10 baseline days" |
| 9 baseline days with data | `insufficient_basis`, no limits, direction still given |
