"""HTTP contract and import-mode checks for the bundled service."""

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

import app.app as api_module
from app.app import app


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_dataset_allowlist_and_path_rejection():
    listed = client.get("/api/datasets")
    assert listed.status_code == 200
    assert listed.json() == {
        "datasets": ["stable", "planted_events", "edge_case"], "synthetic": True,
    }
    for name in ("../stable", "stable.csv", "../../SPEC.md", "unknown"):
        assert client.get("/api/report", params={"dataset": name}).status_code == 422
    assert client.get("/api/report").status_code == 422


def test_all_bundled_reports_include_two_windows_and_maintenance():
    for name in ("stable", "planted_events", "edge_case"):
        response = client.get("/api/report", params={"dataset": name})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["dataset"] == name and body["synthetic"] is True
        assert len(body["baseline_dates"]) == 10
        assert set(body["availability"]) >= {"AM", "PM", "latest_date", "target"}
        assert body["availability"]["target"] == .1
        assert body["availability"]["AM"]["charts"]
        assert body["availability"]["PM"]["charts"]
        assert body["maintenance"]["chart"]["points"]
        assert "exploratory" in body["warnings"][0]


def test_invalid_source_record_exposes_row_number(monkeypatch):
    def invalid(_path):
        raise ValueError("row 17: num_bikes_available must be a non-negative integer")

    monkeypatch.setattr(api_module, "load_station_status", invalid)
    response = client.get("/api/report", params={"dataset": "stable"})
    assert response.status_code == 422
    assert "row 17" in response.json()["detail"]


def test_report_replay_cutoff_calibration_and_current_status():
    historical = client.get("/api/report", params={"dataset": "stable"}).json()
    tenth = historical["baseline_dates"][-1]
    before = client.get("/api/report", params={"dataset": "stable", "as_of": f"{tenth}T17:55"})
    assert before.status_code == 200, before.text
    body = before.json()
    assert body["replay"]["calibrated"] is False
    assert all(chart["p_bar"] is None for chart in body["availability"]["AM"]["charts"].values())
    assert body["maintenance"]["chart"]["p_bar"] is None
    assert all(status["observed_at"] <= f"{tenth}T17:55"
               for status in body["current_station_status"] if not status["missing"])
    assert all(status["observed_at"] is None and status["num_bikes_available"] is None
               for status in body["current_station_status"] if status["missing"])
    at_close = client.get("/api/report", params={"dataset": "stable", "as_of": f"{tenth}T18:00"})
    assert at_close.status_code == 200
    assert at_close.json()["replay"]["calibrated"] is True
    for value in ("2026-01-01", "wrong", "9999-01-01T07:00"):
        assert client.get("/api/report", params={"dataset": "stable", "as_of": value}).status_code == 422


def test_replay_clock_is_metadata_only_and_allowlisted():
    response = client.get("/api/replay-clock", params={"dataset": "planted_events"})
    assert response.status_code == 200, response.text
    clock = response.json()
    assert set(clock) == {
        "dataset", "synthetic", "first_timestamp", "last_timestamp",
        "last_as_of", "calibration_complete_at", "default_as_of",
        "snapshot_timestamps",
    }
    assert clock["dataset"] == "planted_events" and clock["synthetic"] is True
    assert clock["default_as_of"] == clock["calibration_complete_at"]
    assert clock["first_timestamp"] == clock["snapshot_timestamps"][0]
    assert clock["last_timestamp"] == clock["snapshot_timestamps"][-1]
    assert clock["snapshot_timestamps"] == sorted(set(clock["snapshot_timestamps"]))
    assert "num_bikes_available" not in response.text
    assert "num_bikes_disabled" not in response.text
    assert "station_id" not in response.text
    assert "residential_01" not in response.text
    assert client.get("/api/replay-clock", params={"dataset": "../stable"}).status_code == 422
    assert client.get("/api/replay-clock").status_code == 422


def test_imports_from_root_and_app_working_directories():
    for working_dir, module in ((ROOT, "app.app"), (ROOT / "app", "app")):
        result = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, '.'); from {module} import app; print(app.title)"],
            cwd=working_dir, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "Bikeshare Fleet Quality Control" in result.stdout
