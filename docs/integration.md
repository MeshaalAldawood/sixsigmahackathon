# Integration: one origin for the page and the API

The React page and the FastAPI backend are served from **one address by one process**, so there
is no CORS setup and Posit Connect hosts a single content item.

```text
browser ──GET /──────────────► FastAPI ──► app/static/index.html + assets/ (built React page)
        ──GET api/datasets ──►         ──► ["stable.csv", "planted_events.csv", "edge_case.csv"]
        ──GET api/report?… ──►         ──► load_dataset → build_availability + build_maintenance → JSON
```

## Build and serve

```bash
npm --prefix app/frontend ci          # first time (uses the committed package-lock.json)
npm --prefix app/frontend run build   # writes app/static/index.html and app/static/assets/
python -m uvicorn app.app:app         # from the repo root, venv active; open http://localhost:8000
```

`bash app/testme.sh` does all of this in one command. For page development with hot reload, run
the backend on :8000 and `npm --prefix app/frontend run dev` (Vite on :5173 proxies `/api` to it).

## How the pieces connect

- **Build output:** `app/frontend/vite.config.js` sets `outDir: '../static'` and `base: './'`,
  so every asset path in `index.html` is relative (`./assets/...`).
- **API calls:** `app/frontend/src/api.js` fetches `api/datasets` and `api/report?dataset=...`
  with **relative** URLs. Together with relative assets, the same build works at
  `http://localhost:8000/` and under a Connect path like `https://connect.example/content/<guid>/`.
- **Serving order:** `app/app.py` registers the `/api/...` routes first and mounts `app/static/`
  at `/` last, so the page never shadows the API. If the page has not been built, the API still
  starts and `/` returns a short JSON note pointing at `/docs`.
- **No statistics in the browser:** the starter's browser SPC code (`spc.js`) was removed. The page
  draws exactly the `p`, `p_bar`, `lcl`, `ucl` and flags in the report, and shows the backend's
  action and onset text. One report per dataset holds every station's AM and PM chart, so switching
  tab, window or station makes no further request. `tests/test_static.py` checks that the page
  source contains no statistical code.
- **The 0.10 line:** the page draws the service-level target from SPEC.md as a reference line. It
  is not a control limit and no decision on the page is computed from it; the capacity-review
  action comes from the backend.

## What the page shows

- A dataset selector (the three bundled files) and a persistent banner: "Synthetic demonstration
  data; control-chart signals are exploratory."
- **Availability** tab: an AM/PM switch, the latest-day dispatch table (red rows are above their
  UCL), and the selected station's p-chart with its center line, stepped UCL/LCL, the 0.10 target,
  the baseline divider and red out-of-limit points. Missing limits read "no limits (insufficient
  basis)".
- **Maintenance** tab: the network 07:00 broken-bike p-chart and the ranked station list, with its
  `as_of_date` and a stale-data notice if that date is older than the latest day.

## Checked in a browser

Opened at `http://localhost:8720/` in the Claude desktop app's browser on 2026-10-17, served by
`python -m uvicorn app.app:app`; no console errors.

| Check | Observed |
|---|---|
| stable.csv, AM | 10 dispatch rows; S07 "capacity review: unusable every day"; no red rows |
| planted_events.csv, PM, station S08 | the 2026-09-29 point drawn red at 91.7% above the 20.8% UCL |
| planted_events.csv, Maintenance | 09-30, 10-01 and 10-02 red above the 17.0% UCL; list starts S09 10, S10 10 |
| edge_case.csv, AM | E01 "no limits (insufficient basis)" with the matching action text; E02 drawn with limits |

`tests/test_static.py` covers the serving side automatically: `/` returns the page, its assets are
relative and load, the API routes still answer, and the bundle uses relative API URLs and shows the
warning banner.
