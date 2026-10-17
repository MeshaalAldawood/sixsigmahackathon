"""The bundled page and report API share one FastAPI origin."""

import re

from fastapi.testclient import TestClient

from app.app import app


client = TestClient(app)


def test_built_page_and_assets_are_served_from_one_origin():
    page = client.get("/")
    assert page.status_code == 200
    assert "Bikeshare Fleet Quality Control" in page.text
    assets = re.findall(r'(?:src|href)="([^"]+assets/[^"]+)"', page.text)
    assert len(assets) == 2
    for asset in assets:
        response = client.get(asset.replace("./", "/"))
        assert response.status_code == 200
        assert response.content


def test_page_bundle_uses_report_api_without_starter_spc():
    page = client.get("/")
    script = re.search(r'src="([^"]+\.js)"', page.text)
    assert script is not None
    bundle = client.get(script.group(1).replace("./", "/")).text
    assert "api/datasets" in bundle
    assert "api/report?dataset=" in bundle
    assert "Bikeshare fleet" in bundle
    assert "imrLimits" not in bundle


def test_each_dataset_has_sections_needed_by_page():
    for dataset in ("stable", "planted_events", "edge_case"):
        response = client.get("/api/report", params={"dataset": dataset})
        assert response.status_code == 200
        body = response.json()
        for window in ("AM", "PM"):
            section = body["availability"][window]
            assert section["stations"]
            assert section["charts"]
            assert all("action" in station for station in section["stations"])
            assert all("onset" in chart for chart in section["charts"].values())
        assert body["maintenance"]["chart"]["points"]
