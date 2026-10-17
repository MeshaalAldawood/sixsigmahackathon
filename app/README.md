# `app/`: the bikeshare dispatch tool

One FastAPI service that serves the JSON reports and the built React page from the same address.
Adapted from [`demos/fastapi/`](../demos/fastapi/); it keeps that starter's four-script contract.

## Run it

```bash
bash app/testme.sh        # then open http://localhost:8000  (API docs: /docs)
```

Prerequisites: Python 3.12 (`python3.12` or [uv](https://docs.astral.sh/uv/) on your PATH) and,
for the web page, Node.js 20 or newer. `testme.sh` reuses or creates the repo's `.venv`, installs
the pinned [`requirements.txt`](requirements.txt), builds the page from `frontend/` into `static/`
when npm is available, and starts the server on `PORT` (default 8000). Without Node it still
serves an already-built page, or just the API.

## The four-script contract

| File | Job |
|---|---|
| [`testme.sh`](testme.sh) | run the whole tool locally, one command, no arguments |
| [`manifestme.sh`](manifestme.sh) | write `manifest.json` for Posit Connect, on your own machine (never in CI) |
| [`deployme.sh`](deployme.sh) | publish `app/` to Posit Connect with `CONNECT_SERVER` and `CONNECT_API_KEY` from your environment or a gitignored `.env` |
| `README.md` | this file |

## What is in here

| File | What it does | Docs |
|---|---|---|
| [`app.py`](app.py) | the FastAPI app: `GET /api/datasets`, `GET /api/report?dataset=<name>`, the built page at `/` | [docs/api.md](../docs/api.md) |
| [`data_loader.py`](data_loader.py) | `load_dataset(path)`: reads and validates a station status CSV; `filter_rush`, `rush_window` | [data/README.md](../data/README.md) |
| [`qc.py`](qc.py) | `p_chart(baseline, observations)`: the one statistic, an exact binomial p-chart | [docs/statistics.md](../docs/statistics.md) |
| [`availability.py`](availability.py) | `build_availability(records, baseline_dates, target=0.10)`: AM/PM station charts and the dispatch table | [docs/availability.md](../docs/availability.md) |
| [`maintenance.py`](maintenance.py) | `build_maintenance(records, baseline_dates)`: the 07:00 broken-bike chart and station list | [docs/maintenance.md](../docs/maintenance.md) |
| `frontend/` | the React (Vite) page source; built into `static/` | [docs/integration.md](../docs/integration.md) |
| `data/` | copies of the three CSVs, bundled for Posit Connect only | [docs/deployment.md](../docs/deployment.md) |

## Endpoints

- `GET /api/datasets` returns `{"datasets": ["stable.csv", "planted_events.csv", "edge_case.csv"]}`.
- `GET /api/report?dataset=stable.csv` returns availability for AM and PM (every station's chart and
  the latest-day dispatch table), the maintenance chart and station list, and
  `meta: {synthetic, exploratory, baseline_dates, latest_date, warnings}`.
  An unknown name gives 400, a missing parameter 422, an invalid source row 422 naming the row.

## Imports

The modules work two ways: as the package `app` from the repo root (`python -m uvicorn app.app:app`,
and `pytest`), and as plain modules from inside `app/` (`python -m uvicorn app:app`, which is how
`testme.sh` and Posit Connect run it). Each module picks its import style from `__package__`.
