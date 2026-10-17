# Bikeshare Fleet Quality Control

**Team Six — Cornell Six Sigma Hackathon, on-campus track. Prompt: Urban Systems, "Bikeshare Fleets".**

A dispatch tool for a municipal bikeshare operator. It turns the station-status
feed every bikeshare system already publishes (GBFS `station_status`) into exact
binomial **p-charts** that answer two questions:

| Decision | When | What the tool shows |
|---|---|---|
| **A. Availability** | each evening, for the next day's two rushes | per station and rush window (AM 07:00–09:00, PM 16:00–18:00): share of snapshots unusable (empty or full), exact control limits, and a ranked dispatch list: *drop bikes before HH:MM*, *pull bikes before HH:MM*, *collect broken bikes first*, *investigate: special cause*, or *capacity review: unusable every day*. |
| **B. Maintenance** | each morning, before 07:00 | network p-chart of broken bikes among docked bikes at 07:00, and the stations to inspect first, most broken bikes first. |

The tool ranks stations and says what a van should do. It does not assign vans,
plan routes or schedule crews. **All data are synthetic**, and every signal is
labelled *exploratory* (see Assumptions).

- Live app: *Posit Connect URL added at deployment (see [`docs/deployment.md`](docs/deployment.md))*
- Interactive API docs: `<app URL>/docs`

## Run it

Needs Python 3.12. Node 20 is needed only to rebuild the page; a built copy is committed in `app/static/`.

```bash
# macOS / Linux / Git Bash
bash app/testme.sh                  # installs app/requirements.txt, serves http://127.0.0.1:8000/

# Windows PowerShell (uses uv if installed, otherwise pip)
powershell -File app\testme.ps1
```

Tests (63, including the hand-worked answers below):

```bash
python -m pip install -r app/requirements.txt
python -m pytest -q
npm --prefix app/frontend ci && npm --prefix app/frontend run test -- --run
```

## Inputs

| Input | Type | Source |
|---|---|---|
| `station_status` CSV: `timestamp`, `station_id`, `num_bikes_available`, `num_bikes_disabled`, `num_docks_available` | local time `YYYY-MM-DDTHH:MM`; text; non-negative integers | the public GBFS feed logged every 5 minutes |
| Rush windows | fixed: AM `[07:00, 09:00)`, PM `[16:00, 18:00)`, weekdays | the operator's peak definition |
| Baseline | the first 10 weekdays in the file | a period the dispatcher considers normal |
| Target unusable share | 0.10 | the city's service-level agreement (a target, **not** a control limit) |

Rows are validated before use: a missing value, negative or non-integer count,
bad timestamp, or duplicate `station_id` + `timestamp` rejects the file with a
message naming the row. Weekend and off-peak rows are ignored. A missing
snapshot is allowed and lowers `n`; it is never filled in. Codebook: [`data/README.md`](data/README.md).

## The statistic: one exact binomial p-chart

One function in [`app/qc.py`](app/qc.py) is used for both decisions.

- Centre line: `p̄ = Σd / Σn` over the baseline subgroups.
- For a subgroup of size `n`, with `X ~ Binomial(n, p̄)` and `α = 0.00135` (the one-sided 3σ tail):
  - upper count `u` = smallest integer with `P(X > u) ≤ α`; `UCL = u/n`; flag high when `d > u`;
  - lower count `l` = largest integer with `P(X < l) ≤ α`; `LCL = l/n`; flag low when `d < l`.
- Only Western Electric rule 1 (a point beyond a limit) is used.
- Exact limits are used instead of `p̄ ± 3√(p̄(1−p̄)/n)` because one station window has `n = 24`
  and `p̄ ≈ 0.05–0.15`, so `n·p̄` is only 1–4 and the normal approximation fails.

| Chart | Subgroup | `n` | `d` |
|---|---|---|---|
| Availability (AM and PM charted separately) | one station, one weekday, one rush window | snapshots observed (24 if none missing) | snapshots with 0 bikes **or** 0 docks |
| Maintenance | one weekday, whole network at 07:00 | docked bikes (available + disabled) | disabled bikes |

Beside the charts are plain descriptive counts: the empty and full snapshot
counts, and the **typical first-unusable time**. That is the median clock time
of the first empty (or full) snapshot over the baseline days when it happened,
reported with its denominator, for example "07:40 on 3 of 8 observed days".

**Dispatch rule** (latest day, per station and window, first match wins):
(1) full while broken bikes are docked → *collect broken bikes first*;
(2) above UCL → *investigate: special cause*;
(3) in control but `p̄` > 0.10 → *capacity review: unusable every day*;
(4) more empty than full → *van: drop bikes before HH:MM*, more full than empty → *van: pull bikes before HH:MM*;
(5) otherwise *OK*. Full method: [`docs/statistics.md`](docs/statistics.md),
[`docs/availability.md`](docs/availability.md), [`docs/maintenance.md`](docs/maintenance.md).

### Hand-worked checks (reproduced exactly by `tests/test_qc.py`)

- **Availability:** baseline `d = 2, 4, 3, 3`, `n = 24` each, so `p̄ = 12/96 = 0.125`.
  `P(X ≥ 10) = 0.000342 ≤ α` but `P(X ≥ 9) = 0.001656 > α`, so `u = 9` and `UCL = 0.375`.
  `P(X = 0) = 0.0406 > α`, so `l = 0` and no day can flag low. With `n = 20`, `UCL = 8/20 = 0.40`.
  `d = 10` flags (0.4167 > 0.375). `d = 8` does **not** flag (0.3333), although the normal-formula UCL of 0.3275 would wrongly flag it.
- **Maintenance:** `p̄ = 0.10`, `n = 100`: `u = 20`, `UCL = 0.20`; `l = 2`, `LCL = 0.02`. 25/100 flags high, 20/100 does not, 1/100 flags low.
- **Degenerate:** `p̄ = 0` or `p̄ = 1`, fewer than 10 baseline days, or `n = 0`: no limits, and the page says
  "insufficient basis for control limits". It never shows a limit of 0 or 1 or an invented alert.

Cross-check any limit with `scipy.stats.binom.sf(u, n, p̄)` (Python) or `1 - pbinom(u, n, p̄)` (R).

### Assumptions

- Snapshots within a window are treated as independent trials, which they are not: an empty
  station at 07:35 is likely still empty at 07:40. Real false-alarm rates are therefore higher
  than α, so every signal is labelled **exploratory**.
- Limits come from the baseline days only, never from the days being judged.
- Control limits describe normal variation. The 0.10 target is a service agreement, which a
  station can miss while in control (that is the *capacity review* action).

## Simulated replay

The page can replay a bundled file snapshot by snapshot with Play/Pause, seek, speed and
event jumps. Each step calls `GET /api/report?dataset=…&as_of=YYYY-MM-DDTHH:MM`, and the server uses
only rows at or before that clock time. Until the tenth baseline weekday closes (18:00), no
limits are shown. A rush window in progress is **provisional**: its counts are shown, but no
verdict is given until 09:00 or 18:00. This replays synthetic data and is not a live GBFS feed. See
[`docs/api.md`](docs/api.md) and [`docs/integration.md`](docs/integration.md).

## API

| Route | Returns |
|---|---|
| `GET /api/datasets` | `{"datasets": ["stable", "planted_events", "edge_case"], "synthetic": true}` |
| `GET /api/report?dataset=<name>[&as_of=…]` | baseline dates, AM and PM availability sections (dispatch table and per-station charts), maintenance chart and station list, replay metadata, current station status |
| `GET /api/replay-clock?dataset=<name>` | timestamps only, for replay navigation |

Only the three bundled names are accepted, never paths. Bad input returns HTTP 422 with a message.

## Demonstrations (one per dataset)

Each dataset has 15 weekdays from 2026-10-05 to 2026-10-23 and 10 stations; the first 10 weekdays are the baseline.

1. **`stable`**: no station or maintenance point flags in either window. `downtown_01` AM is
   2/24 = 8.3% with UCL 29.2%. `hilltop_01` is in control at 16.7% but above the 10% target, so its
   action is *capacity review: unusable every day*.
2. **`planted_events`**: PM, `stadium_01`, 2026-10-20: 18/24 = 75.0% is above the 29.2% UCL
   (the planted stadium event). On the maintenance chart, 40/400 = 10.0% broken bikes flags high on
   2026-10-21, 22 and 23 against `p̄ = 0.05`, `UCL = 0.085`. No baseline day flags.
3. **`edge_case`**: `edge_01` is never unusable in the baseline (`p̄ = 0`), so it gets no limits and an
   insufficient-basis message. `edge_02` has missing snapshots, so its `n` and its exact UCL vary by day.

Walkthrough with screenshots: [`demo/README.md`](demo/README.md), [`demo/screenshots/`](demo/screenshots/).

## Repository map

```
app/            FastAPI app (app.py) + qc.py, availability.py, maintenance.py, replay.py, data_loader.py
app/frontend/   React (Vite) source; builds into app/static/, served by FastAPI at /
app/data/       copies of the three CSVs bundled for deployment (tests check they match data/)
data/           the approved synthetic CSVs, generator (generate.py) and codebook
tests/          pytest suite: hand answers, degenerate cases, replay, API, bundle/manifest
docs/           method, API, deployment and verification notes; event docs (criteria, schedule)
```

## Deployment

The app deploys to Posit Connect as one FastAPI content item. The React page and the API share one origin.
Run `bash app/manifestme.sh` (rebuilds the page, copies the CSVs, writes `app/manifest.json`), then
`bash app/deployme.sh` with `CONNECT_SERVER` and `CONNECT_API_KEY` in a gitignored `app/.env`.
Or use GitHub Actions ([`.github/workflows/deploy-fastapi.yml`](.github/workflows/deploy-fastapi.yml)) with those two repo secrets. Details:
[`docs/deployment.md`](docs/deployment.md).

## Credits

Built on the event's `demos/fastapi` and `demos/reactfront` starters. The Connect publishing
workflow is adapted from [timothyfraser/fastapi-connect-demo](https://github.com/timothyfraser/fastapi-connect-demo) (MIT).
Exact binomial tails come from SciPy. The code was written with AI coding agents (Codex, Claude Code), which the team
steered and reviewed. Event information: [`docs/schedule.md`](docs/schedule.md), [`docs/criteria.md`](docs/criteria.md).
