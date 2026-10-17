"""Tests for the FastAPI backend (task H-04).

Run from the repo root:  python -m pytest tests/test_api.py -q
They use FastAPI's in-process TestClient; tests/test_api.py also starts real
servers from the repo root and from inside app/ to prove both import styles work.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.app as api
from app.availability import build_availability
from app.data_loader import filter_rush, load_dataset
from app.maintenance import build_maintenance

REPO = Path(__file__).resolve().parent.parent
DATASETS = ["stable.csv", "planted_events.csv", "edge_case.csv"]
client = TestClient(api.app)


def get_report(name):
    response = client.get("/api/report", params={"dataset": name})
    assert response.status_code == 200, response.text
    return response.json()


def test_datasets_lists_exactly_the_three_bundled_files():
    response = client.get("/api/datasets")
    assert response.status_code == 200
    assert response.json() == {"datasets": DATASETS}


@pytest.mark.parametrize("name", DATASETS)
def test_report_has_the_frozen_shape(name):
    body = get_report(name)
    assert set(body) == {"dataset", "availability", "maintenance", "meta"}
    assert body["dataset"] == name
    assert set(body["availability"]) == {"AM", "PM"}
    for window in ("AM", "PM"):
        assert set(body["availability"][window]) == {"stations", "charts", "warnings"}
    assert set(body["maintenance"]) == {"chart", "stations", "as_of_date", "warnings"}
    meta = body["meta"]
    assert meta["synthetic"] is True and meta["exploratory"] is True
    assert meta["baseline_dates"] == [f"2026-09-{d}" for d in ("14", "15", "16", "17", "18", "21", "22", "23", "24", "25")]
    assert meta["latest_date"] == "2026-10-02"


@pytest.mark.parametrize("name", DATASETS)
def test_report_equals_the_domain_modules_exactly(name):
    rush = filter_rush(load_dataset(REPO / "data" / name))
    dates = sorted({r["timestamp"].date() for r in rush})
    expected = {"availability": build_availability(rush, dates[:10]), "maintenance": build_maintenance(rush, dates[:10])}
    body = get_report(name)
    assert body["availability"] == json.loads(json.dumps(expected["availability"]))
    assert body["maintenance"] == json.loads(json.dumps(expected["maintenance"]))


def flags(chart):
    return [p["date"] for p in chart["points"] if p["flagged_high"] or p["flagged_low"]]


def test_planted_report_shows_both_planted_signals():
    body = get_report("planted_events.csv")
    assert flags(body["availability"]["PM"]["charts"]["S08"]) == ["2026-09-29"]
    assert flags(body["maintenance"]["chart"]) == ["2026-09-30", "2026-10-01", "2026-10-02"]
    s07 = next(r for r in body["availability"]["AM"]["stations"] if r["station_id"] == "S07")
    assert s07["action"] == "capacity review: unusable every day"


def test_stable_report_has_no_flags():
    body = get_report("stable.csv")
    for window in ("AM", "PM"):
        for chart in body["availability"][window]["charts"].values():
            assert flags(chart) == []
    assert flags(body["maintenance"]["chart"]) == []


def test_edge_report_shows_insufficient_basis_and_short_days():
    body = get_report("edge_case.csv")
    e01 = next(r for r in body["availability"]["AM"]["stations"] if r["station_id"] == "E01")
    assert e01["status"] == "insufficient_basis" and e01["ucl"] is None
    short = body["availability"]["AM"]["charts"]["E02"]["points"][2]
    assert short["n"] == 20 and short["ucl"] == pytest.approx(0.30)


def test_unknown_dataset_is_400_and_paths_are_refused():
    for name in ["nope.csv", "../SPEC.md", "/etc/passwd", "data/stable.csv", "STABLE.CSV"]:
        response = client.get("/api/report", params={"dataset": name})
        assert response.status_code == 400, name
        assert "unknown dataset" in response.json()["detail"]


def test_missing_dataset_query_is_422():
    assert client.get("/api/report").status_code == 422


def test_invalid_source_rows_are_422_with_the_row(tmp_path, monkeypatch):
    bad = tmp_path / "stable.csv"
    bad.write_text("timestamp,station_id,num_bikes_available,num_bikes_disabled,num_docks_available\n"
                   "2026-09-14T07:00,S01,3,-1,5\n", encoding="utf-8")
    monkeypatch.setattr(api, "DATA_DIR", tmp_path)
    response = client.get("/api/report", params={"dataset": "stable.csv"})
    assert response.status_code == 422
    assert "row 2" in response.json()["detail"] and "negative" in response.json()["detail"]


def test_responses_contain_no_nan_or_infinity():
    for name in DATASETS:
        text = client.get("/api/report", params={"dataset": name}).text
        json.loads(text, parse_constant=lambda c: pytest.fail(f"{name}: {c} in JSON"))


def test_api_docs_are_served():
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["paths"].keys() >= {"/api/datasets", "/api/report"}


# ---- real servers: from the repo root and from inside app/ -------------------------------

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.parametrize("cwd, target", [(REPO, "app.app:app"), (REPO / "app", "app:app")])
def test_server_starts_from_root_and_from_app_dir(cwd, target):
    port = free_port()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", target, "--host", "127.0.0.1", "--port", str(port)],
                            cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"{base}/api/datasets", timeout=1) as r:
                    assert json.load(r) == {"datasets": DATASETS}
                    break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        else:
            pytest.fail(f"server in {cwd} never answered: {proc.stdout.read1().decode() if proc.stdout else ''}")
        with urllib.request.urlopen(f"{base}/api/report?dataset=planted_events.csv", timeout=10) as r:
            body = json.load(r)
        assert body["maintenance"]["chart"]["p_bar"] == pytest.approx(0.10)
        try:
            urllib.request.urlopen(f"{base}/api/report?dataset=evil.csv", timeout=5)
            pytest.fail("unknown dataset answered 200")
        except urllib.error.HTTPError as err:
            assert err.code == 400
    finally:
        proc.terminate()  # only the server this test started, by its own handle
        proc.wait(timeout=10)
