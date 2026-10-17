# API contract

The single FastAPI service returns UTF-8 JSON. Both endpoints work from the repository root or from `app/`, and all input files are bundled synthetic data.

`GET /api/datasets` returns `{"datasets":["stable","planted_events","edge_case"],"synthetic":true}`.

`GET /api/report?dataset=stable` accepts only those three names. An unknown name receives HTTP 422; a missing approved bundle receives HTTP 503. The response includes `dataset`, `synthetic`, `baseline_dates`, a top-level exploratory warning, `availability`, and `maintenance`.

`availability` contains `latest_date`, `target`, global warnings, and `AM` and `PM` sections. Each section has `stations` (the latest-day sorted dispatch table), `charts` keyed by station ID, and warnings. Chart points include `date`, `d`, `n`, `p`, `p_bar` at chart level, exact `lcl`/`ucl`, flags and status. Empty or missing windows expose a null share or limit and an explicit warning. Each station includes separate empty/full counts and baseline onset time with affected, observed, missing and partially observed day counts plus snapshot coverage.

`maintenance` contains a network chart, a ranked list of 07:00 stations with broken bikes, `as_of_date`, and warnings. Missing 07:00 measurements are not replaced by a later snapshot.

The API does no statistical calculation beyond choosing the original first ten weekdays. Validation, aggregation and exact p-chart logic live in the Python domain modules. The UI must display their values directly.

## Simulated replay

`GET /api/replay-clock?dataset=stable` returns metadata for initializing playback without requesting a measured report. It uses the same three-name allowlist. The JSON contains `dataset`, `synthetic`, `first_timestamp`, `last_timestamp`, `last_as_of`, `calibration_complete_at`, `default_as_of`, and sorted unique `snapshot_timestamps`. `default_as_of` is the tenth original baseline weekday at 18:00; `last_as_of` is 18:00 on the final observed day. The endpoint contains no station IDs, bike counts, station status, alerts, or chart values. The UI can seek to `default_as_of` and then request its first report.

`GET /api/report?dataset=stable&as_of=2026-10-19T08:55` accepts an optional local timestamp within the bundled dataset's clock range. A malformed or out-of-range timestamp receives HTTP 422. Omission returns the completed historical report. The server loads and validates the bundled CSV, freezes its original first ten weekday dates, then removes every row after `as_of` before calculating either report or current station state.

The response retains the historical fields and adds `replay`: `as_of`, `first_timestamp`, `last_timestamp`, `calibration_complete_at`, `calibrated`, `observed_station_count`, `station_count`, `synthetic`. First/last and the station ID catalog are navigation metadata, not future measurements. `current_station_status` lists every bundled station ID. Observed stations include latest `observed_at`, `age_minutes`, `stale` (age over five minutes), `missing: false`, bike/disabled/dock counts, and `unusable`. A station never seen at the cutoff has `missing: true`, `stale: true`, and null timestamp, age, counts and usability. Future measurements are never attached to its ID. Do not use navigation metadata as measured state.

The tenth original baseline weekday closes at 18:00. Until then, both domains withhold baseline shares and control limits; availability also withholds onset times. Rush windows are half-open: AM `[07:00,09:00)` and PM `[16:00,18:00)`. At 08:55 and 17:55 the current point is `provisional`, with actual `d`, `n`, `p`, but null control limits and no final signal or dispatch verdict. At 09:00 and 18:00 it becomes complete even if snapshots are missing. Point and dispatch rows expose `provisional`, `window_complete`, `expected_snapshots` (24), and `observed_snapshots`; each window exposes its completion state. A missing current subgroup has null share and a `no data` action. Rewinding reuses the same fixed baseline dates and recalculates exclusively from visible rows.
