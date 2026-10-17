"""The deployable app/ folder is self-contained and matches its committed manifest."""

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.app import DATASETS, app


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


def test_bundled_csvs_are_exact_copies_of_the_approved_sources():
    for name in DATASETS:
        assert (APP / "data" / f"{name}.csv").read_bytes() == (ROOT / "data" / f"{name}.csv").read_bytes()


def test_manifest_is_fastapi_and_lists_only_runtime_files_that_exist():
    manifest = json.loads((APP / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["metadata"] == {"appmode": "python-fastapi", "entrypoint": "app:app"}
    assert manifest["python"]["version"].startswith((APP / ".python-version").read_text().strip())
    files = manifest["files"]
    for required in ("app.py", "qc.py", "availability.py", "maintenance.py", "replay.py",
                     "data_loader.py", "requirements.txt", "static/index.html",
                     *(f"data/{name}.csv" for name in DATASETS)):
        assert required in files
    assert not any(path.startswith(("frontend/", "__pycache__")) or path == ".env" for path in files)
    for path, entry in files.items():
        content = (APP / path).read_bytes()
        assert hashlib.md5(content).hexdigest() == entry["checksum"], f"{path} changed; run app/manifestme.sh"


def test_manifest_lists_every_built_static_asset():
    manifest = json.loads((APP / "manifest.json").read_text(encoding="utf-8"))
    built = {p.relative_to(APP).as_posix() for p in (APP / "static").rglob("*") if p.is_file()}
    assert built == {path for path in manifest["files"] if path.startswith("static/")}


def test_app_serves_page_and_all_three_reports():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/api/datasets").json()["datasets"] == list(DATASETS)
    for name in DATASETS:
        response = client.get("/api/report", params={"dataset": name})
        assert response.status_code == 200, name
