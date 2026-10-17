![](docs/images/banner_thin.png)

# 🚲 Bikeshare dispatch: which stations need a van, and when

**Team Six, Cornell Six Sigma Hackathon (on-campus track), prompt "Urban Systems: Bikeshare Fleets".**

A municipal bikeshare system has a "docks full / docks empty" crisis at rush hour, and maintenance
vans are dispatched blindly. This tool reads the dock-availability log every bikeshare system
already publishes and tells the **operations dispatcher**:

- **A. Availability (each evening, for tomorrow's two rushes):** which stations need a van in the
  morning (07:00-09:00) and evening (16:00-18:00) rush, whether to **drop** or **pull** bikes and
  **by what time**, and which stations vans cannot fix because they are unusable every day.
- **B. Maintenance (each morning, before 07:00):** whether the network's share of broken bikes has
  risen beyond normal, and which stations to collect broken bikes from first.

It does this with **one statistic, a p-chart with exact binomial control limits**, checked against
hand-worked answers. The app (FastAPI plus a React page) only delivers that analysis.

> **Synthetic demonstration data; control-chart signals are exploratory.** All three test datasets
> were generated ([data/README.md](data/README.md)); none of it is real station data.

**Live app:** not deployed yet. The Posit Connect bundle is ready and tested locally, but the course
publisher key was not available to the build; see [docs/deployment.md](docs/deployment.md).

---

## Run it (one command)

```bash
git clone https://github.com/MeshaalAldawood/sixsigmahackathon.git
cd sixsigmahackathon
bash app/testme.sh
```

Open <http://localhost:8000> (API docs at <http://localhost:8000/docs>). Prerequisites: **Python 3.12**
(`python3.12`, or [uv](https://docs.astral.sh/uv/), on your PATH) and **Node.js 20+** to rebuild the
page. `testme.sh` creates or reuses `.venv`, installs the pinned
[`app/requirements.txt`](app/requirements.txt), builds the page and starts one server. The page
itself is committed already built, so the tool also runs without Node.

Run the tests:

```bash
source .venv/bin/activate
python -m pytest -q                     # 152 tests: data, loader, statistic, both modules, API, page serving
npm --prefix app/frontend run build     # rebuild the page into app/static/
```

## Inputs and parameters

Only what a dispatcher already has or decides:

| Input | Type and units | Where it comes from |
|---|---|---|
| `station_status.csv`: `timestamp`, `station_id`, `num_bikes_available`, `num_bikes_disabled`, `num_docks_available`, one row per station per 5-minute snapshot | local time `YYYY-MM-DDTHH:MM`; text; integer counts of bikes, broken bikes, free docks | the system's public GBFS `station_status` feed, logged every 5 minutes (GBFS's own column names) |
| Rush windows | fixed: 07:00-09:00 (AM) and 16:00-18:00 (PM), weekdays | the operator's definition of the peaks |
| Baseline | the first 10 weekdays in the file | a period of normal operation |
| Target unusable share | 0.10 (10% of a rush window) | the city's service-level agreement; a target, **not** a control limit |

Bad input is rejected with the CSV row named: a missing value, a negative or fractional count, a
malformed timestamp, a duplicate station + timestamp. Missing snapshots are allowed (they lower n).
The tool reads the three bundled datasets (no upload) through `GET /api/report?dataset=<name>`.

## The statistics

Full method, known answers and assumptions: **[docs/statistics.md](docs/statistics.md)**. In short:

- A snapshot is **unusable** when a station has **no bikes** (nobody can start a trip) or **no free
  docks** (nobody can end one).
- **Availability:** one subgroup = one station, one weekday, one rush window. n = snapshots logged
  (24), d = unusable snapshots. AM and PM are charted separately, because residential stations
  empty in the morning and fill in the evening.
- **Maintenance:** one network subgroup per weekday from the 07:00 snapshot: n = docked bikes,
  d = broken bikes, summed over stations.
- **p-chart:** p̄ = Σd / Σn over the baseline. For each day, with X ~ Binomial(n, p̄) and
  α = 0.00135 per tail, the upper count u is the smallest k with P(X > k) ≤ α and the lower count l
  is the largest k with P(X < k) ≤ α; UCL = u/n, LCL = l/n. A day is flagged when d > u or d < l
  (Western Electric rule 1). Exact limits are used because n·p̄ for one station's window is usually
  below 5 (0.3 to 6.3 in the demo data), too small for the usual ±3σ normal formula.
- **Known answers reproduced by the tests:** baseline 12/96 (p̄ = 0.125) gives UCL 9/24 = 0.375 and
  8/20 = 0.40; 10/24 flags, 8/24 does not (the normal formula would wrongly flag it). Baseline 10/100
  gives limits 0.02 to 0.20; 25/100 flags. An independent reviewer reproduced every one
  ([docs/verification.md](docs/verification.md)).
- **Assumption to keep in mind:** snapshots five minutes apart are not independent, so real false
  alarms are more frequent than the nominal rate. Every signal is labelled **exploratory**.

### What the dispatcher is told (first rule that applies)

1. Full while broken bikes take docks: **collect broken bikes first**.
2. Above the upper control limit: **investigate: special cause**, plus the van direction.
3. In control but p̄ above the 10% target: **capacity review: unusable every day** (vans will not fix it).
4. More empty than full: **van: drop bikes before HH:MM**; more full than empty: **van: pull bikes
   before HH:MM**, where HH:MM is the station's median first-unusable time in the baseline.
5. Otherwise **OK**. Missing data or missing limits are said as such, never shown as "OK".

Details: [docs/availability.md](docs/availability.md) and [docs/maintenance.md](docs/maintenance.md).

## Demonstration on the three datasets

Walk-through with the observed numbers and how to read each: **[demo/README.md](demo/README.md)**.

| Dataset | What the tool finds |
|---|---|
| [`stable.csv`](data/stable.csv) | Nothing flagged (0 of 300 availability points, 0 of 15 maintenance points). Hilltop station S07 is in control but empty 26% of the morning rush: **capacity review**. Van directions for the rest. |
| [`planted_events.csv`](data/planted_events.csv) | The **stadium event**: S08 full in 22 of 24 PM snapshots on 2026-09-29, flagged above its 20.8% UCL. The **broken-bike surge**: 40, 38, 42 of 200 bikes broken on 09-30 to 10-02, flagged above the 17% UCL (34 bikes). |
| [`edge_case.csv`](data/edge_case.csv) | E01 is never unusable, so p̄ = 0: **no control limits (insufficient basis)**, no invented alert. E02's days with 4 missing snapshots get wider limits (AM UCL 30% instead of 25%; PM 25% instead of 20.8%). |

## How it is built

```text
data/*.csv ──► app/data_loader.py ──► app/availability.py ─┐
 (GBFS log)     load_dataset()          AM/PM station charts ├─► app/app.py (FastAPI) ──► React page (app/static)
                                    ──► app/maintenance.py ─┘     GET /api/datasets
                                         07:00 network chart       GET /api/report?dataset=
                         both call ──► app/qc.py  p_chart(): the one statistic
```

| Document | What it covers |
|---|---|
| [data/README.md](data/README.md) | codebook: every file and column with units, how the data were generated (seed), planted signals, how to log GBFS for real |
| [docs/statistics.md](docs/statistics.md) | the exact binomial p-chart, known answers, assumptions |
| [docs/availability.md](docs/availability.md) | availability subgroups, dispatch table fields, action rules, onset times |
| [docs/maintenance.md](docs/maintenance.md) | the 07:00 network chart and station list |
| [docs/api.md](docs/api.md) | endpoints, status codes, the report's JSON |
| [docs/integration.md](docs/integration.md) | building and serving the page from the same origin |
| [docs/deployment.md](docs/deployment.md) | the Posit Connect bundle, CI workflow, current status |
| [docs/verification.md](docs/verification.md) | the independent audit: what was re-run and what it showed |
| [app/README.md](app/README.md) | the app folder, its four scripts and modules |
| [demo/README.md](demo/README.md) | the demonstration on each dataset |

Project ledger and spec: [SPEC.md](SPEC.md), [CONTRACT.md](CONTRACT.md), [docs/plan.md](docs/plan.md).
Event information (schedule, rubric, prompts) stays in [docs/](docs/README.md).

## Out of scope

No live feed polling, uploads, maps, van routing or crew scheduling, demand forecasting, repair-time
estimates or machine learning. Built with AI coding agents under the repo's spec-first workflow;
statistics reviewed independently.

![](docs/images/banner_icons.png)
