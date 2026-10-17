# `data/`: test datasets and codebook

> **SYNTHETIC DEMONSTRATION DATA.** Every value in these files was written by
> [`generate.py`](generate.py) from fixed patterns. None of it was observed at a real bikeshare
> station, and it must never be presented as real.

Three files in the format of a logged GBFS `station_status` feed: one row per station per
five-minute snapshot, weekday rush windows only.

| File | Stations | Rows | What it shows |
|---|---|---|---|
| [`stable.csv`](stable.csv) | S01-S10 | 7,200 | a normal network: opposite residential and downtown rush patterns, one chronic hilltop station, a steady broken-bike share |
| [`planted_events.csv`](planted_events.csv) | S01-S10 | 7,200 | the same network with two planted signals after the baseline |
| [`edge_case.csv`](edge_case.csv) | E01, E02 | 1,432 | a station that is never unusable, and missing snapshots |

Rows = stations x 15 weekdays x 48 snapshots (24 per rush window). `edge_case.csv` is
2 x 15 x 48 = 1,440 minus 8 missing snapshots = **1,432**.

## Columns

The names are GBFS's own (`station_status.json`), so a real log drops straight in.

| Column | Type | Units | Meaning |
|---|---|---|---|
| `timestamp` | text, `YYYY-MM-DDTHH:MM` | local time, 24-hour clock | when the snapshot was taken: every 5 minutes, 07:00-08:55 and 16:00-17:55 |
| `station_id` | text | - | `S01`-`S10` in the main files, `E01`-`E02` in the edge file |
| `num_bikes_available` | integer >= 0 | bikes | rentable bikes docked at the station. **0 = empty**: nobody can start a trip |
| `num_bikes_disabled` | integer >= 0 | bikes | broken bikes docked at the station; they take a dock but cannot be rented |
| `num_docks_available` | integer >= 0 | docks | free docks. **0 = full**: nobody can end a trip |

A snapshot is **unusable** when `num_bikes_available == 0` or `num_docks_available == 0`. In every
row, `num_bikes_available + num_bikes_disabled + num_docks_available` equals the station's
capacity; no docks are out of service in this data. The loader ([`app/data_loader.py`](../app/data_loader.py))
rejects a file with a missing value, a negative or fractional count, a malformed timestamp or a
duplicate station + timestamp, naming the CSV row (row 1 is the header).

## Calendar and baseline

- 15 weekdays, Mon **2026-09-14** to Fri **2026-10-02** (days 1-15). No weekends, no holidays.
- **Baseline: days 1-10, 2026-09-14 to 2026-09-25**, byte-identical in `stable.csv` and
  `planted_events.csv`. Control limits come from these days only.
- Day 12 = Tue 2026-09-29; days 13-15 = Wed 2026-09-30 to Fri 2026-10-02. Day 15 is the latest
  day, so it is the day the dispatch table describes.

## Stations (`stable.csv` and `planted_events.csv`)

"Baseline share" is unusable snapshots / 240 baseline snapshots (10 days x 24). "Broken" and
"docked at 07:00" are per normal day.

| Station | Type | Capacity | AM problem, baseline share | PM problem, baseline share | Broken | Docked at 07:00 |
|---|---|---|---|---|---|---|
| S01 | residential | 23 | empty, 13/240 = 0.054 | full, 8/240 = 0.033 | 3 | 20 |
| S02 | residential | 23 | empty, 13/240 = 0.054 | full, 7/240 = 0.029 | 2 | 19 |
| S03 | residential | 27 | empty, 11/240 = 0.046 | full, 9/240 = 0.038 | 3 | 24 |
| S04 | downtown | 31 | full, 22/240 = 0.092 | empty, 9/240 = 0.038 | 0 | 21 |
| S05 | downtown | 31 | full, 18/240 = 0.075 | empty, 9/240 = 0.038 | 2 | 22 |
| S06 | downtown | 27 | full, 24/240 = **0.100** (exactly the target, not above it) | empty, 11/240 = 0.046 | 0 | 18 |
| S07 | **hilltop (chronic)** | 15 | empty, 63/240 = **0.2625** | empty, 3/240 = 0.013 | 1 | 12 |
| S08 | downtown, by the stadium | 39 | full, 10/240 = 0.042 | empty, 10/240 = 0.042 | 0 | 32 |
| S09 | balanced | 19 | empty, 3/240 = 0.013 | full, 3/240 = 0.013 | 4 (varies, see below) | 15 |
| S10 | balanced | 19 | full, 3/240 = 0.013 | empty, 3/240 = 0.013 | 5 | 17 |

Residential stations run out of bikes in the morning (everyone rides to work) and out of docks
in the evening; downtown stations do the opposite. Nobody rides up to the hilltop, so S07 empties
every morning: in control, but far above the 0.10 target, which is a capacity problem vans will
not fix.

The docked-at-07:00 counts sum to **200 bikes every day**, so the maintenance chart always has
n = 200. Broken bikes sum to 20 on a normal day; S09's count moves by
`0, -1, +1, 0, +2, -2, 0, +1, -1, 0, 0, +1, 0, -1, +1` on days 1-15, giving network totals
`20, 19, 21, 20, 22, 18, 20, 21, 19, 20, 20, 21, 20, 19, 21` (baseline 200 of 2,000 = 0.10).

## How the data were generated

Run from the repo root: `python data/generate.py` (`--out <folder>` writes elsewhere). Standard
library only. `tests/test_data.py` regenerates all three files and checks they are
byte-identical to the committed ones.

The files are built from **fixed integer patterns** written out in `generate.py`, so every chart
result is designed:

1. `UNUSABLE[station][window]` lists how many of the 24 snapshots are unusable on each of the
   15 days. With `d` unusable snapshots, the station drains (or fills) in a straight line from
   its start level and is empty (or full) from snapshot `24 - d` to the end of the window.
   For example, S07 AM on day 1 has `d = 6`: empty from 08:30 to 08:55.
2. Broken bikes are constant through the day. The morning starts with
   `docked at 07:00 - broken` rentable bikes; the evening starts from a fixed level per station.
3. Free docks = capacity - rentable bikes - broken bikes.

**Seed: `SEED = 20261016`.** It only adds a wiggle of -1, 0 or +1 bike to the counts strictly
between the window start and the empty/full point, clamped so the station is never empty or full
there. The seed cannot create or remove an unusable snapshot, so it cannot change any chart.

## Planted signals (`planted_events.csv` only)

| Signal | Where | How it was planted | Raw counts |
|---|---|---|---|
| **Stadium event** | S08, day 12 (Tue 2026-09-29), PM | after a stadium event every free dock fills: 18 bikes at 16:00, 28 at 16:05, full (39 bikes) from 16:10 | 22 of 24 PM snapshots full (normal days: 0-2 empty, 0 full). S08 has no broken bikes, so the action is "investigate", not "collect broken bikes" |
| **Broken-bike surge** | every station, days 13-15 | each station's broken bikes double; the extra broken bikes were rentable ones, so 200 bikes are still docked at 07:00 | network broken bikes at 07:00: 40, 38 and 42 of 200 (normal: 18-22) |

Nothing else changed. The surge lowers rentable bikes at 07:00 on days 13-15 but, by design,
not the number of empty or full snapshots, so the availability charts are untouched by it.

## Expected chart behavior

Verified with the finished p-chart in [`app/qc.py`](../app/qc.py) by `tests/test_data.py`.

| File | Availability charts (10 or 2 stations x AM/PM) | Maintenance chart (n = 200 at 07:00) |
|---|---|---|
| `stable.csv` | **0 flags** on all 300 points; S07 AM in control at 0.2625 (capacity review) | p_bar = 0.10, limits 8 to 34 broken bikes; **0 flags** on all 15 points |
| `planted_events.csv` | **exactly one flag**: S08 PM on day 12, 22/24 against a 24-snapshot upper count of 5 (UCL 0.208) | **days 13, 14, 15 flag high** (40, 38, 42 > 34) |
| `edge_case.csv` | E01: p_bar = 0 in both windows, "insufficient basis", no limits. E02 AM: 4 snapshots missing on day 3 (07:30-07:45) so n = 20 and the UCL steps up from 0.25 to 0.30; E02 PM: 4 missing on day 11 (17:00-17:15), n = 20. No flags | 3 broken of 31 docked every day; no flags |

**Stable false-alert count: 0.** That is a property of these designed files, not of real dock
data. In real logs empty and full spells come in clumps (a station empty at 07:35 is usually
still empty at 07:40), so the day-to-day counts vary more than a binomial allows, and a p-chart
flags more often than its nominal 0.135% per tail. An earlier random-walk version of these files
flagged 14 of 300 stable points for exactly that reason. That is why the tool labels every
signal **exploratory**; see [`docs/statistics.md`](../docs/statistics.md).

## Collecting this data for real

Every GBFS bikeshare system publishes a public `station_status.json` feed (listed in its
`gbfs.json` discovery file); reading it needs no account or key.

1. Every 5 minutes on weekdays, 07:00-09:00 and 16:00-18:00, a scheduled job (cron, or a
   scheduled Posit Connect job) downloads `station_status.json`.
2. For each station, write one row: `last_reported` (a Unix epoch time) converted to local time and
   rounded to the 5-minute mark, then `station_id`, `num_bikes_available`, `num_bikes_disabled` and
   `num_docks_available` as published.
3. Station capacities are in `station_information.json`. A real feed also has
   `num_docks_disabled`, which this tool does not use.
4. A missed download is simply a missing row; the tool handles it (n drops for that window).
   Leave out stations with `is_renting` or `is_returning` false and note them: a closed station is
   a different problem from an empty or full one.

Two weeks of logging (10 weekdays) is enough to set the first control limits.
