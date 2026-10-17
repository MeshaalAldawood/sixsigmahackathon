# Deployment to Posit Connect

**Status (2026-10-17 01:30 ET): not deployed. Blocked on the publisher credentials.** The app is
fully prepared and the deployable bundle has been run on its own locally; the only missing input
is the course Connect server address and publisher API key, which are handed out at the event and
are not on this machine. No public URL exists yet, and none is claimed here.

## What gets deployed

One Posit Connect content item, mode `python-fastapi`, entrypoint `app:app`, published from the
`app/` folder. It serves the React page at `/` and the API at `/api/...` from the same address
([integration.md](integration.md)).

The bundle is exactly the files listed in [`app/manifest.json`](../app/manifest.json) (18 files):
the Python modules, `requirements.txt` (pinned), `.python-version` (3.12), the built page in
`app/static/`, the four scripts and README, and **`app/data/`**, which holds byte-identical copies of
the three CSVs. The React source (`app/frontend/`) is not bundled.

## Steps already done, with their real output

1. **Data copied and compared:** `cp data/*.csv app/data/`, then `cmp` passed for all three:

   | File | SHA-256 |
   |---|---|
   | `stable.csv` | `f842e25eed84149164a6163e05f554c1fa16cce0327891ac14158b3cc14e9917` |
   | `planted_events.csv` | `2cdfb527fcf9c8a23ca0542df2badd1db01a2a73b5ea018b8d0a3cc62a981e13` |
   | `edge_case.csv` | `73b2dfe7e1931d1ec2dff47abd9aeaf3bf7cb7fdbfa1392834828f5e5f7c77e0` |

   If `data/generate.py` is ever re-run, copy the files again (and re-run `manifestme.sh`); the
   app reads `app/data/` whenever it exists.
2. **Page built:** `npm --prefix app/frontend run build` wrote `app/static/`.
3. **Manifest written on this machine:** `bash app/manifestme.sh` (rsconnect-python 1.32.0) printed
   `Creating manifest.json... [OK]`. The manifest records `appmode python-fastapi`, `entrypoint
   app:app`, `python 3.12.14`.
4. **Bundle tested on its own:** the 18 manifest files were copied into an empty temporary folder
   and started there with `python -m uvicorn app:app`. Results: `/` returned 200 `text/html`; all
   three `/api/report?dataset=...` calls returned 200; `planted_events.csv` flagged maintenance on
   2026-09-30, 10-01 and 10-02, the same as locally.
5. **CI workflow added:** [`.github/workflows/deploy-fastapi.yml`](../.github/workflows/deploy-fastapi.yml)
   (copied from `.claude/skills/connect-publish/workflows/`) with `APP_DIR: 'app'` and
   `HEALTH_PATH: '/api/datasets'`, plus `.github/scripts/connect-publish-async.sh`. It runs on pushes to
   `main`, verifies the committed manifest (never regenerates it), smoke-imports `app:app`, publishes
   with plain `curl` calls to the Connect API, and fails unless `/api/datasets` answers 200.
6. **Deploy attempted:** `bash app/deployme.sh` printed
   `deployme.sh: set CONNECT_SERVER and CONNECT_API_KEY (export them or put them in .env)` and exited
   1. No `CONNECT_*` variables, no `.env` file and no saved rsconnect server exist on this machine.
   Whether the GitHub repo already has the two secrets could not be checked (no `gh` CLI here).

## To finish the deployment (needs the credentials)

**Never paste the key into chat, a file that is committed, or a commit message.**

Fastest, from a teammate's machine:

```bash
# in a gitignored .env at the repo root (.env is already in .gitignore):
#   CONNECT_SERVER=https://<course connect server>
#   CONNECT_API_KEY=<publisher key>
bash app/deployme.sh
```

Or through GitHub Actions: in the repo, **Settings > Secrets and variables > Actions**, add
`CONNECT_SERVER` and `CONNECT_API_KEY`; the workflow then deploys on the next push to `main`
(merging this branch counts), or run it by hand from the Actions tab (`workflow_dispatch`).

Then, in Connect, set the content's **Access** to "Anyone - no login required" (Connect's default
is restricted to logged-in users), and verify from a logged-out browser or with:

```bash
URL=https://<content url>/
curl -s -o /dev/null -w '%{http_code}\n' "$URL"
for d in stable.csv planted_events.csv edge_case.csv; do curl -s -o /dev/null -w "$d %{http_code}\n" "${URL}api/report?dataset=$d"; done
```

All four must print 200, and `planted_events.csv` must flag maintenance on 2026-09-30, 10-01 and
10-02 as it does locally. Record the URL and those outputs here and in the root README.

## If the deploy fails

Read the Connect deploy log top to bottom (connect-publish skill). Most likely, in order: the
server lacks Python 3.12 (change `app/.python-version`, re-run `manifestme.sh`, commit); a pinned
package is unavailable on the server's index (adjust `app/requirements.txt` through H-03, then
re-run `manifestme.sh`); a stale manifest after a change (re-run `manifestme.sh`). The manifest's
`locale` reads `C.UTF-8` because it was written in a sandboxed shell; the workflow only warns about
that.
