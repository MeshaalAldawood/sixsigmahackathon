"""Tests that one FastAPI origin serves the built React page next to the API (task H-05).

Run after building the page:  npm --prefix app/frontend run build
then, from the repo root:     python -m pytest tests/test_static.py -q
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.app as api

REPO = Path(__file__).resolve().parent.parent
STATIC = REPO / "app" / "static"
FRONTEND = REPO / "app" / "frontend"
client = TestClient(api.app)


def test_page_is_built():
    assert (STATIC / "index.html").is_file(), "run: npm --prefix app/frontend run build"


def test_root_serves_the_built_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="root"></div>' in response.text
    assert "<title>Bikeshare Dispatch</title>" in response.text


def test_assets_are_relative_and_served():
    html = client.get("/").text
    assets = re.findall(r'(?:src|href)="([^"]+)"', html)
    assert assets and all(a.startswith("./assets/") for a in assets), assets  # works under a Connect prefix
    for asset in assets:
        response = client.get("/" + asset.removeprefix("./"))
        assert response.status_code == 200, asset


def test_api_routes_are_not_shadowed_by_the_page():
    assert client.get("/api/datasets").json() == {"datasets": ["stable.csv", "planted_events.csv", "edge_case.csv"]}
    assert client.get("/api/report", params={"dataset": "nope.csv"}).status_code == 400
    assert client.get("/docs").status_code == 200


def bundle_text():
    return "".join(p.read_text(encoding="utf-8") for p in (STATIC / "assets").glob("*.js"))


def test_page_fetches_the_api_with_relative_urls():
    js = bundle_text()
    assert "api/report?" in js and "api/datasets" in js
    assert "/api/report" not in js and "127.0.0.1" not in js and "localhost" not in js


def test_page_shows_the_synthetic_and_exploratory_warning():
    assert "Synthetic demonstration data; control-chart signals are exploratory." in bundle_text()


def test_browser_code_computes_no_statistics():
    sources = "".join(p.read_text(encoding="utf-8") for p in (FRONTEND / "src").glob("*.js*"))
    assert not (FRONTEND / "src" / "spc.js").exists()  # the starter's browser SPC code was removed
    for forbidden in ["Math.sqrt", "binom", "1.128", "imrLimits", "mrBar", "reduce("]:
        assert forbidden not in sources, forbidden
    # The page reads limits and flags from the report instead of deriving them.
    for field in ["p_bar", "ucl", "lcl", "flagged_high", "action"]:
        assert field in sources, field


@pytest.mark.parametrize("name", ["stable.csv", "planted_events.csv", "edge_case.csv"])
def test_every_dataset_the_page_offers_has_a_report(name):
    body = client.get("/api/report", params={"dataset": name}).json()
    assert body["meta"]["synthetic"] and body["meta"]["exploratory"]
    for window in ("AM", "PM"):
        stations = body["availability"][window]["stations"]
        assert stations and all(r["station_id"] in body["availability"][window]["charts"] for r in stations)
