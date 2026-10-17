"""Bikeshare dispatch API: one FastAPI service for the reports and the built page (task H-04).

    GET /api/datasets                 -> {"datasets": [...three bundled files...]}
    GET /api/report?dataset=<name>    -> {"dataset", "availability", "maintenance", "meta"}
    GET /                             -> the built React page (app/static/), if it has been built
    GET /docs                         -> interactive API docs (free from FastAPI)

The routes only load a whitelisted CSV and call the domain modules; no
statistic is computed here. Start it from the repo root with
`python -m uvicorn app.app:app`, or from inside app/ with `python -m uvicorn app:app`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

if __package__:
    from .availability import build_availability
    from .data_loader import filter_rush, load_dataset
    from .maintenance import build_maintenance
else:  # run from inside app/ (testme.sh, Posit Connect)
    from availability import build_availability
    from data_loader import filter_rush, load_dataset
    from maintenance import build_maintenance

APP_DIR = Path(__file__).resolve().parent
# Prefer data bundled next to the app (the Posit Connect deployment); otherwise the repo's data/.
DATA_DIR = APP_DIR / "data" if (APP_DIR / "data").is_dir() else APP_DIR.parent / "data"
STATIC_DIR = APP_DIR / "static"
DATASETS = ("stable.csv", "planted_events.csv", "edge_case.csv")
BASELINE_DAYS = 10

app = FastAPI(
    title="Bikeshare dispatch API",
    description="Exact binomial p-charts for station availability (AM/PM rush) and broken bikes. "
                "Synthetic demonstration data; control-chart signals are exploratory.",
    version="1.0.0",
)


@app.get("/api/datasets")
def datasets() -> dict:
    """The bundled test datasets a report can be requested for."""
    return {"datasets": list(DATASETS)}


@app.get("/api/report")
def report(dataset: str = Query(..., description="one of the names from /api/datasets")) -> dict:
    """Availability (AM and PM) and maintenance results for one bundled dataset."""
    if dataset not in DATASETS:
        raise HTTPException(status_code=400, detail=f"unknown dataset {dataset!r}; choose one of {list(DATASETS)}")
    try:
        records = load_dataset(DATA_DIR / dataset)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=f"{dataset}: {err}") from None
    rush = filter_rush(records)
    dates = sorted({r["timestamp"].date() for r in rush})
    baseline = dates[:BASELINE_DAYS]
    warnings = []
    if len(baseline) < BASELINE_DAYS:
        warnings.append(f"only {len(baseline)} weekdays with rush-hour data (need {BASELINE_DAYS} for a baseline)")
    return {
        "dataset": dataset,
        "availability": build_availability(rush, baseline),
        "maintenance": build_maintenance(rush, baseline),
        "meta": {
            "synthetic": True,
            "exploratory": True,
            "baseline_dates": [d.isoformat() for d in baseline],
            "latest_date": dates[-1].isoformat() if dates else None,
            "warnings": warnings,
        },
    }


# API routes are registered first; the built page is served last, so it never shadows /api.
if (STATIC_DIR / "index.html").is_file():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    @app.get("/")
    def root() -> dict:
        return {"message": "Bikeshare dispatch API is running; the web page has not been built yet.",
                "docs": "docs", "datasets": "api/datasets"}
