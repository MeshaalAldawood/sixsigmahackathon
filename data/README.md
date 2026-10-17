# Synthetic bikeshare snapshot codebook

All observations in this directory are invented demonstration data. They do not describe a real system, trip demand, failures, or repair time. Regenerate the CSVs with `python data/generate.py`. The standard-library generator uses `random.Random(5300)` to vary the first-unusable clock times while holding daily subgroup counts steady. Its output is byte-for-byte reproducible.

| File | Rows | Scenario |
|---|---:|---|
| `stable.csv` | 7,200 | Ten stations, 15 weekdays, 48 five-minute snapshots per station/day. Four residential stations empty for two AM snapshots and fill for two PM snapshots; four downtown stations do the reverse. `hilltop_01` empties for four AM snapshots (4/24 = 0.167, above the 0.10 service target) every day. `stadium_01` fills for two snapshots in each window. At 07:00, 20 of 400 docked bikes are disabled (5%) every day. Baseline false alerts: **0** availability points and **0** maintenance points. |
| `planted_events.csv` | 7,200 | Identical to `stable.csv` during the first ten weekdays. On weekday 12 (2026-10-20), `stadium_01` is full for 18 of 24 PM snapshots. Starting weekday 13 (2026-10-21), disabled bikes at 07:00 rise from 20/400 to 40/400, doubling the share from 0.05 to 0.10. Both are intended high exact-binomial signals. |
| `edge_case.csv` | 1,436 | Two stations over the same 15 weekdays. `edge_01` is never empty or full, so its baseline share is zero and control limits are unavailable. `edge_02` has three empty AM snapshots daily and lacks four AM snapshots on weekday 14 (2026-10-22): that subgroup has n = 20 while the others have n = 24. Missing rows are never imputed. |

The first ten weekdays, **2026-10-05 through 2026-10-16**, are the fixed calibration period. Weekdays 11–15 are monitored. Each AM window is 07:00–08:55 and each PM window is 16:00–17:55, with five-minute spacing. The windows are half-open at 09:00 and 18:00. Station IDs and 50-dock station capacities are synthetic. Every row has the five fields below, in this exact order:

| Column | Type and units | Meaning |
|---|---|---|
| `timestamp` | local ISO 8601 minute, `YYYY-MM-DDTHH:MM` | State observation time; no time-zone offset is encoded. |
| `station_id` | text | Stable identifier for one station. |
| `num_bikes_available` | non-negative integer, bikes | Docked usable bikes. Zero means riders cannot begin a trip. |
| `num_bikes_disabled` | non-negative integer, bikes | Docked broken bikes; these occupy docks. |
| `num_docks_available` | non-negative integer, docks | Vacant usable docks. Zero means riders cannot end a trip. |

To gather an equivalent real file, poll the operator's public GBFS `station_status` feed every five minutes, retain its feed timestamp in the operator's local time, and write one row per station and timestamp with those four GBFS fields. Keep missing polls missing; do not fill them with zero or interpolate them. Retain weekdays and both rush windows for the analysis, and choose a genuinely normal ten-day baseline before looking at events. The synthetic scenarios here are for exercising the tool and must stay labelled as such.
