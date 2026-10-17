# Deployment to Posit Connect

One FastAPI content item serves both the API and the built React page (same origin, no CORS).
The bundle is the `app/` folder, exactly as listed in the committed `app/manifest.json`.

## What is in the bundle

`app/manifest.json` (`appmode: python-fastapi`, `entrypoint: app:app`, Python 3.12.15) lists 20 files:
the Python modules, `requirements.txt` (pinned with `==`), `.python-version`, the four scripts,
`README.md`, `static/` (built page) and `data/` (the three CSVs). `frontend/` source,
`node_modules`, `__pycache__` and `.env` are excluded. `tests/test_startup.py` fails if any listed
file's checksum no longer matches, if a built asset is missing from the manifest, or if
`app/data/*.csv` differ from the approved `data/*.csv`.

## Before you deploy (already done, 2026-10-17)

```
$ python -m pytest -q
63 passed, 1 warning
```

A manifest-only bundle check was run: only the files in `manifest.json` were copied to an empty
folder and the app was started there with `uvicorn app:app`. Results:

```
200 /
200 /api/datasets
200 /api/report?dataset=stable
200 /api/report?dataset=planted_events
200 /api/report?dataset=edge_case
200 /api/replay-clock?dataset=stable
```

## Deploy: option 1, from your machine (fastest first deploy)

1. Create `app/.env` (gitignored; check with `git status` that it does not appear):
   ```
   CONNECT_SERVER=<the server URL handed out at the event>
   CONNECT_API_KEY=<your publisher key>
   ```
2. If you changed any Python, the page, `requirements.txt` or the CSVs, refresh the bundle and commit it:
   `bash app/manifestme.sh` (runs `npm ci`, builds the page, copies the CSVs, writes `manifest.json`).
3. `bash app/deployme.sh`. This runs `rsconnect deploy manifest manifest.json`, which uploads exactly the
   listed files and prints the content URL.
4. In Connect, open the content item, go to **Access**, and set it to *Anyone - no login required*.

## Deploy: option 2, GitHub Actions

`.github/workflows/deploy-fastapi.yml` publishes the committed manifest with plain `curl` calls
(`.github/scripts/connect-publish-async.sh`). It never regenerates the manifest on the runner.
It runs on pushes to `main` that touch Python, `requirements.txt`, the manifest, `app/static/` or `app/data/`,
and also on demand (**Actions → Deploy FastAPI to Posit Connect → Run workflow**).

1. Repo **Settings → Secrets and variables → Actions**: add `CONNECT_SERVER` and `CONNECT_API_KEY`.
2. Push, or run the workflow by hand. The final step polls `<content URL>/api/datasets` until it returns 200.
3. Set Access to *Anyone - no login required* in Connect, as above.

`.github/workflows/tests.yml` runs the Python and React tests on Ubuntu and Windows on every
push and pull request. It needs no secrets.

## After deploying: verify logged out

In a private browser window (or with `curl`, without an API key), check:

```
<URL>/                                    page loads
<URL>/api/datasets                        200
<URL>/api/report?dataset=stable           200
<URL>/api/report?dataset=planted_events   200
<URL>/api/report?dataset=edge_case        200
```

Record the URL and these results below, and add the URL to the root `README.md`.

## Deployment record

| Date | Route | URL | Logged-out check |
|---|---|---|---|
| *pending: needs the event's publisher key* | | | |

## If it fails

Read Connect's deploy log top to bottom first. The usual causes, most likely first: dependency
resolution, wrong entrypoint, a stale manifest (re-run `manifestme.sh`), or the Python version
(the manifest says 3.12.15; Connect must offer a 3.12).
