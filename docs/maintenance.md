# Maintenance: Decision B (has the broken-bike share risen, and where to collect)

Module: [`app/maintenance.py`](../app/maintenance.py). Tests:
[`tests/test_maintenance.py`](../tests/test_maintenance.py). The statistic is the exact binomial
p-chart in [`app/qc.py`](../app/qc.py) ([statistics.md](statistics.md)).

```python
build_maintenance(records, baseline_dates)
# -> {"chart": {...}, "stations": [...], "as_of_date": "YYYY-MM-DD" or None, "warnings": [...]}
```

`records` are never changed. It does not import the availability module.

## The network chart

- **One point per weekday, from the 07:00 snapshot only.** Exactly 07:00: a 07:05 snapshot is
  never used as a substitute, so a day without a 07:00 snapshot simply has no point (with a
  dated warning). 07:00 is before the morning rush, when a van can still act on it.
- **d** = broken bikes (`num_bikes_disabled`) summed over every station at 07:00;
  **n** = docked bikes (`num_bikes_available + num_bikes_disabled`) summed over the same stations.
  Each station counts once per day.
- If a station is missing from a day's 07:00 snapshot it is left out of **both** d and n, and the
  chart warns "incomplete coverage" with the station ids.
- p_bar comes from the first ten retained weekdays; the chart needs ten baseline days with 07:00
  data, otherwise every point is `insufficient_basis` (no limits, no flags).
- Chart shape: `{baseline_dates, p_bar, points, warnings}`; each point is a `qc.p_chart` point plus
  `date` and `p_bar`.
- Flag wording on the point's `warnings`: high = "more bikes are broken than normal"; low =
  "fewer bikes are broken than normal (a decrease)". A low point is good news, not a repair alert.

## The station list

From the **most recent date that has a 07:00 snapshot** (`as_of_date`): every station with at
least one broken bike, sorted by broken bikes (most first), then `station_id`. Each row is
`{station_id, num_bikes_disabled, action: "inspect and collect broken bikes"}`. There are no repair
times; the data does not contain them.

If `as_of_date` is older than the latest retained day, `warnings` says the list is stale. With no
07:00 snapshots at all, the list is empty, `as_of_date` is `null` and a warning explains why.

## Assumptions

- Each docked bike at 07:00 is treated as an independent trial. Broken bikes cluster (a bad batch,
  a vandalised station), so real false alarms are more frequent than the nominal rate: the signal
  is **exploratory**.
- Broken bikes that are out on the street or already in the workshop are not seen; the chart
  describes docked bikes only.

## Known answers (from `tests/test_maintenance.py`)

| Case | Result |
|---|---|
| 20 broken of 200 docked every baseline day | p_bar 0.10, counts 8 to 34, LCL 0.04, UCL 0.17 |
| a day with 40 of 200 (the doubled share) | flagged high |
| 34 of 200 | not flagged (equality at the upper count) |
| 7 of 200 | flagged low, worded as a decrease |
| 10 of 100 baseline, 25 of 100 latest (the SPEC answer) | LCL 0.02, UCL 0.20, flagged high |
| 07:05 and 16:00 snapshots present | ignored; only 07:00 counts |
| one station missing at 07:00 | left out of d and n, "incomplete coverage" warning |
