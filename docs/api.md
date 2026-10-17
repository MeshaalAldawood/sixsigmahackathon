# API

One FastAPI service ([`app/app.py`](../app/app.py)) serves two JSON endpoints and, once built, the
React page. Routes only pick a whitelisted CSV and call the domain modules; no statistic is
computed in the API. Interactive docs: `/docs` (Swagger) on any running copy.

## Run it

```bash
bash app/testme.sh                          # one command: venv, pinned deps, page build, server on :8000
python -m uvicorn app.app:app --port 8000   # from the repo root (venv active)
cd app && python -m uvicorn app:app         # from inside app/, the way Posit Connect runs it
```

Both import styles are tested (`tests/test_api.py` starts a real server each way). The service
starts without the built page; `/` then answers with a short JSON pointer to `/docs`.

Data lookup: `app/data/` if it exists (the Posit Connect bundle), otherwise the repo's `data/`.

## `GET /api/datasets`

```json
{"datasets": ["stable.csv", "planted_events.csv", "edge_case.csv"]}
```

## `GET /api/report?dataset=<name>`

`dataset` is required and must be one of the three names above; nothing else is ever turned into
a file path.

| Request | Status | Body |
|---|---|---|
| `?dataset=stable.csv` (or another bundled name) | 200 | the report below |
| `?dataset=other.csv`, `../SPEC.md`, any other string | 400 | `{"detail": "unknown dataset ...; choose one of [...]"}` |
| no `dataset` parameter | 422 | FastAPI's validation error |
| the bundled file fails validation | 422 | `{"detail": "<file>: row N: <what is wrong>"}` |

The report:

```text
{
  "dataset": "planted_events.csv",
  "availability": {
    "AM": {"stations": [<dispatch row>, ...], "charts": {"S01": <chart>, ...}, "warnings": [...]},
    "PM": {...}
  },
  "maintenance": {"chart": <chart>, "stations": [<broken-bike row>, ...], "as_of_date": "2026-10-02", "warnings": [...]},
  "meta": {"synthetic": true, "exploratory": true,
           "baseline_dates": ["2026-09-14", ..., "2026-09-25"], "latest_date": "2026-10-02", "warnings": []}
}
```

- **Baseline:** the first ten retained weekdays, chosen once here and passed to both modules, so
  every chart uses the same calendar. `latest_date` is the day every dispatch row describes.
- **`<chart>`** = `{baseline_dates, p_bar, points, warnings}`; each point has `date, d, n, p,
  p_bar, lower_count, upper_count, lcl, ucl, flagged_high, flagged_low, status, warnings`
  ([statistics.md](statistics.md)).
- **`<dispatch row>`** fields and the action rules: [availability.md](availability.md).
- **`<broken-bike row>`** = `{station_id, num_bikes_disabled, action}`: [maintenance.md](maintenance.md).
- Unavailable numbers are `null`; the JSON never contains `NaN` or infinity.
- Every chart for every station is included, so switching window, station or tab in the page needs
  no further request and no calculation in the browser.

## Example

```bash
curl -s "http://localhost:8000/api/report?dataset=planted_events.csv" \
  | python -c "import json,sys; r=json.load(sys.stdin); print([p['date'] for p in r['maintenance']['chart']['points'] if p['flagged_high']])"
# ['2026-09-30', '2026-10-01', '2026-10-02']
```
