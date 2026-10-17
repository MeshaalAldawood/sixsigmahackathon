"""FastAPI entrypoint for the bundled synthetic bikeshare reports."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:
    from app.availability import build_availability
    from app.data_loader import load_station_status
    from app.maintenance import build_maintenance
    from app.replay import parse_as_of, prepare_replay, replay_clock
except ModuleNotFoundError:  # Connect starts with app/ as its working directory.
    from availability import build_availability
    from data_loader import load_station_status
    from maintenance import build_maintenance
    from replay import parse_as_of, prepare_replay, replay_clock


APP_DIR = Path(__file__).resolve().parent
DATASETS = ("stable", "planted_events", "edge_case")
app = FastAPI(title="Bikeshare Fleet Quality Control", version="1.0.0")


def _dataset_path(name: str) -> Path:
    if name not in DATASETS:
        raise HTTPException(status_code=422, detail="Unknown dataset. Choose stable, planted_events, or edge_case.")
    for directory in (APP_DIR / "data", APP_DIR.parent / "data"):
        candidate = directory / f"{name}.csv"
        if candidate.is_file():
            return candidate
    raise HTTPException(status_code=503, detail=f"Bundled dataset {name} is unavailable")


@app.get("/api/datasets")
def datasets() -> dict:
    """List approved synthetic datasets; names are never treated as paths."""
    return {"datasets": list(DATASETS), "synthetic": True}


@app.get("/api/replay-clock")
def replay_clock_endpoint(dataset: str) -> dict:
    """Expose synthetic navigation times before requesting measured reports."""
    try:
        records = load_station_status(_dataset_path(dataset))
        return {"dataset": dataset, "synthetic": True, **replay_clock(records)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/report")
def report(dataset: str, as_of: str | None = None) -> dict:
    """Produce both rush-window charts and the network maintenance chart."""
    try:
        records = load_station_status(_dataset_path(dataset))
        replay = prepare_replay(records, parse_as_of(as_of))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    baseline_dates = replay["baseline_dates"]
    availability = build_availability(
        replay["records"], baseline_dates, as_of=replay["as_of"] if as_of else None,
        calibrated=replay["calibrated"],
    )
    maintenance = build_maintenance(
        replay["records"], baseline_dates, as_of=replay["as_of"] if as_of else None,
        calibrated=replay["calibrated"],
    )
    return {
        "dataset": dataset,
        "synthetic": True,
        "baseline_dates": [day.isoformat() for day in baseline_dates],
        "warnings": ["Synthetic demonstration data; control-chart signals are exploratory."],
        "availability": availability,
        "maintenance": maintenance,
        "replay": replay["metadata"],
        "current_station_status": replay["station_status"],
    }


STATIC_DIR = APP_DIR / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets", check_dir=False), name="assets")


@app.get("/", include_in_schema=False)
def root():
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"message": "Bikeshare Fleet Quality Control API", "docs": "docs"}


@app.get("/{path:path}", include_in_schema=False)
def frontend_route(path: str):
    """Serve built Vite files and client routes without taking over API paths."""
    if path.startswith(("api/", "assets/")):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = STATIC_DIR / path
    if STATIC_DIR.is_dir() and candidate.is_file() and STATIC_DIR in candidate.resolve().parents:
        return FileResponse(candidate)
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend is not built")
