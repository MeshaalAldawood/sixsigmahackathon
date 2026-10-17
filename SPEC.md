# SPEC: Bike-sharing station decisions

This is the product contract. Follow the [hackathon rubric](docs/criteria.md). Implement **only** what is written here. Synthetic data is explicitly labeled; unconfirmed event information remains TBD.

## 1. Team and prompt
- **Team name:** TBD — confirm with team.
- **Track:** TBD — confirm on-campus or virtual.
- **Prompt we chose:** TBD — insert exact Devpost prompt number and title before submission.
- **Our public repo:** https://github.com/MeshaalAldawood/sixsigmahackathon (confirm this is the submission repo).

## 2. User and use case (rubric: scope 5, user and use case 5)
- **User:** Bike-sharing operations supervisor reviewing station status.
- **Decision A — Availability:** Which stations cannot serve rentals or returns, and should we add or remove a working bike?
- **Decision B — Maintenance:** Which stations have broken bikes, and which should be inspected/collected first?
- **Prompt fit:** Bike availability and broken-bike maintenance; confirm exact wording against the official prompt.
- **Boundary:** Prioritize stations, **not** vans, trips, routes, or work schedules. The two analyses are independent.

## 3. Inputs (rubric: minimal inputs 5)
One CSV with one row per station per daily checkpoint:

| Column | Type / units | Meaning |
|---|---|---|
| `timestamp` | ISO date `YYYY-MM-DD` | Scheduled checkpoint |
| `station_id` | text | Station |
| `total_docks` | integer / docks | Usable dock positions |
| `working_bikes` | integer / bikes | Rentable bikes occupying docks |
| `broken_bikes` | integer / bikes | Broken bikes occupying docks |

Derived: `empty_docks = total_docks - working_bikes - broken_bikes`. Reject missing values, negative counts, duplicate station/date pairs, or occupancy exceeding capacity. Each checkpoint must cover the same stations. Snapshots do **not** measure downtime, repair events, or rider demand.

## 4. The statistics, and why (rubric: valid QC analysis 25)
- **One method:** A **p control chart**, computed by a single tested Python function and reused in both modules. The first **20 checkpoints** form the fixed baseline. For each date, `p = failures / opportunities`.
- **Availability chart:** Failure = a station with `working_bikes == 0` **OR** `empty_docks == 0`; opportunity = a station observed. Show one network-level chart. Latest-snapshot rules: no working bikes and an empty dock -> **add 1 working bike**; no empty docks and a working bike -> **remove 1 working bike**; all docks occupied by broken bikes -> **collect a broken bike first**. Otherwise no action. List actionable stations first, sorted by `station_id` for deterministic ties.
- **Maintenance chart:** Failure = a docked bike that is broken; opportunity = any docked bike (`working_bikes + broken_bikes`). Latest-snapshot rule: list stations with `broken_bikes > 0`, sorted by broken-bike count descending, then `station_id`; action = **inspect/collect broken bikes**. No repair ETA.
- **Formula:** `p_bar = sum(baseline failures)/sum(baseline opportunities)`; `LCL = max(0, p_bar - 3*sqrt(p_bar*(1-p_bar)/n))`; `UCL = min(1, p_bar + 3*sqrt(p_bar*(1-p_bar)/n))`, where `n` is the daily opportunity count. Flag `p < LCL` or `p > UCL`. Control limits are **not** operating targets.
- **Assumptions:** Comparable checkpoints; binomial-style proportion data. If fewer than 20 checkpoints, zero opportunities, `p_bar` of 0 or 1, or `n*p_bar < 5` / `n*(1-p_bar) < 5`, show **insufficient basis for standard p-chart limits**, not an invented alert. Because repeated station/bike snapshots may be correlated, label control-chart signals *exploratory* rather than validated false-alarm probabilities.
- **Known answer:** For baseline 10/100, `p_bar=0.10`, `LCL=0.01`, `UCL=0.19`; monitored 25/100 (`p=0.25`) flags above UCL. Test this plus invalid counts and missing/insufficient data. Keep statistics separate from UI.

## 5. Delivery (rubric: working tool 25)
- **Stack:** The existing `demos/fastapi/` starter, Python calculations, **one minimal React/Vite page**. One deployed FastAPI service should serve the built React page and JSON results; no second deployed service.
- **API:** `GET /api/datasets` and `GET /api/report?dataset=<approved_filename>`; accept only the two bundled datasets (no arbitrary paths). Both reports are available independently and read the same validated CSV schema.
- **Implementation split:** `app/qc.py` shared and frozen first; `app/availability.py` and `app/maintenance.py` have separate tests and must not import one another. Minimal integration in the API and UI. Preserve the starter's `testme`, `manifestme`, `deployme`, and README scripts. Deploy on course Posit Connect; credentials provided separately.

## 6. Outputs
One page: **dataset selector, Availability tab, Maintenance tab**. Each tab shows **one** p-chart (points, center line, control limits or warning), **one** table of prioritized stations with counts, and a plain-English recommended action. Show "Synthetic demonstration data." No map, login, upload, or additional pages.

## 7. Test datasets and codebook (rubric: demo 10, datasets 5, codebook 5)
Exactly **two synthetic CSV files** in `data/` using §3: `stable.csv` (20 baseline checkpoints plus subsequent stable observations) and `deterioration.csv` (same baseline plus a clearly planted increase). Use enough stations/bikes that p-chart approximation checks pass in the intended demos. `data/README.md` defines every field, units, baseline, generation rules, expected chart behavior, and real-world collection equivalent. Edge cases belong in unit tests rather than a third CSV.

## 8. Documentation and reproducibility (rubric: docs 10, public repo 5)
A fresh clone must run the app with `app/testme.sh` and pass `pytest`. Tests cover the hand calculation, bad data, both priority rules, and a planted chart signal. README describes input, two decisions, charts, run command, two dataset demonstrations, and public URL. Submit repo and demo on Devpost.

## 9. Out of scope
No real-world integrations, uploads, forecasting, demand estimation, travel-time estimates, maps, vehicle routing, van assignment, repair scheduling, user accounts, database, ML, extra charts, or visual polish before passing tests. Do **not** add features to fill time.
