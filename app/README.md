# Bikeshare Fleet Quality Control API

This FastAPI service reads three bundled **synthetic** station-status CSVs and serves station availability and network broken-bike p-charts. Signals are exploratory because consecutive five-minute snapshots are dependent.

From the repository root, run `bash app/testme.sh` (installs `app/requirements.txt`, then serves on port 8000), or on Windows `powershell -File app\testme.ps1`. Open `http://127.0.0.1:8000/docs` for the interactive API. `GET /api/datasets` lists the approved names; `GET /api/report?dataset=stable` returns both AM and PM availability charts and the 07:00 maintenance chart. Valid names are `stable`, `planted_events`, and `edge_case`. A built React page in `app/static/` is served at `/` when available. The API also starts from `app/` with `python -m uvicorn app:app`.

The first ten weekdays in each full CSV are the shared fixed baseline. AM is 07:00–08:55 and PM is 16:00–17:55; missing snapshots lower exposure and are never filled. The chart module uses exact binomial limits, and the target is 0.10. See [API response documentation](../docs/api.md) and [statistics](../docs/statistics.md).

`bash app/manifestme.sh` rebuilds the page, copies the three CSVs into `app/data/` and writes `manifest.json`; `bash app/deployme.sh` publishes exactly the files the manifest lists, using `CONNECT_SERVER` and `CONNECT_API_KEY` from a gitignored `app/.env`. See [deployment](../docs/deployment.md).
