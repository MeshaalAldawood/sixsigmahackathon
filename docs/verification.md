# Verification

What was checked, by whom, and what it actually printed. Every line below was run, not assumed.
Branch `overnight/complete-build`, 2026-10-17.

## Independent statistical reviews

Each review was done by a separate agent in a fresh context. It had read-only access, did not
write the code, and recomputed the numbers without the project's own functions (its own counting
from the raw CSVs, binomial tails from `math.comb`).

| Review | Scope | Result |
|---|---|---|
| H-03, the p-chart | every SPEC section-4 hand answer; count limits re-derived from the definition for n = 24, 20, 100, 200 and a sweep over n = 1-60 x 7 values of p; degenerate and invalid inputs; output keys | **OVERALL: PASS**, 0 mismatches |
| H-09 and H-10, the decision modules | all 660 availability points and every maintenance point in the three datasets recomputed from the raw CSVs; dispatch actions by SPEC's first-match rules; median onset times by hand (S01, S04, S07 AM); suppressed limits never producing a claim; JSON free of NaN/inf | **OVERALL: PASS**, 0 mismatches |

### Known answers (SPEC section 4), reproduced by `tests/test_qc.py` and both reviews

| Case | Hand answer | Tool |
|---|---|---|
| baseline d = 2, 4, 3, 3 of 24 | p̄ = 0.125 | 0.125 |
| n = 24 | l = 0, u = 9, UCL 0.375 | (0, 9), 0.375 |
| n = 20 | u = 8, UCL 0.40 | (0, 8), 0.40 |
| d = 10 of 24 | flagged high | flagged high |
| d = 8 of 24 | not flagged (normal UCL 0.3275 would flag) | not flagged |
| P(X ≥ 10), P(X ≥ 9) for n 24, p .125 | 0.0003420, 0.0016565 | 0.00034199, 0.00165647 |
| baseline 10 of 100 | l = 2, u = 20, LCL 0.02, UCL 0.20 | (2, 20), 0.02, 0.20 |
| 25 / 20 / 1 of 100 | high / not flagged / low | high / not flagged / low |
| baseline 20 of 200 (the dataset's maintenance network) | u = 34, so 40 flags | (8, 34), 40 flagged |
| median of 07:35, 07:40, 07:50 on 3 of 10 days | 07:40, "on 3 of 10" | 07:40, "on 3 of 10 baseline days" |

## Independent fresh-clone audit (H-07)

A separate agent cloned `overnight/complete-build` into an empty folder (with the then-uncommitted
README copied in), let `testme.sh` build everything from scratch, and checked every concrete claim
in `README.md`, `demo/README.md`, `data/README.md` and the docs against the live API, the CSVs and
its own `math.comb` calculations.

| Check | Observed |
|---|---|
| `bash app/testme.sh` on the fresh clone (new `.venv` via uv, `npm ci`, build) | `/api/datasets` answered 200 after **28 s**; `/` served the page; all three reports 200 |
| `python -m pytest -q` in the clone | `152 passed, 1 warning` (a Starlette/httpx deprecation notice) |
| `npm --prefix app/frontend run build` in the clone | `✓ built`; output hashes identical to the committed `app/static/` |
| every number in the dispatch tables, maintenance lists, flags, onsets, limits and row counts | all reproduced; stable 0 of 300 and 0 of 15 flags; planted only S08 PM 2026-09-29 and maintenance 09-30, 10-01, 10-02 |
| every tail probability quoted in `statistics.md` and `maintenance.md` | all reproduced (e.g. P(X <= 7) = 0.000485 for n 200, p .10, so 7 flags low) |
| API status codes | `other.csv`, `../SPEC.md` (also URL-encoded) and `stable` -> 400; missing parameter -> 422 |
| deployment-doc claims | 18 manifest files present; the three SHA-256 values match; `cmp` identical |
| secrets | no key-shaped strings |

Defects it returned, and what was done:

1. `docs/verification.md` and the new `README.md` were not committed, so the clone had two dead
   links. **Fixed:** both committed with this audit.
2. The README and `statistics.md` described n·p̄ as "1-4"; the demo data spans 0.3 to 6.3.
   **Fixed:** both now say "usually below 5 (0.3 to 6.3 in the demo data)". No result changes.
3. The README's edge-case row gave only the AM limit change. **Fixed:** it now gives AM and PM.
4. `testme.sh` binds `0.0.0.0` rather than `127.0.0.1`. **Left as is:** harmless for a local demo
   and handy on Posit Cloud; Connect does not use `testme.sh`.

Verdict after the fixes: every claim checked reproduces from a fresh clone.

## Test suite

`python -m pytest -q` from the repo root, with the Python 3.12 venv active:

```
152 passed in 11.84s
```

| File | Tests | What it proves |
|---|---|---|
| `tests/test_loader.py` | 34 | validation errors name the CSV row; sorting; rush-window boundaries; rows validated before filtering |
| `tests/test_data.py` | 23 | schemas, row counts, 24 snapshots per window, byte-identical regeneration from the seed, shared baseline, planted signals in raw counts and through the p-chart, stable data flags nothing |
| `tests/test_qc.py` | 30 | every hand answer, equality at limits, changed n, lower flags, degenerate and invalid input |
| `tests/test_availability.py` | 23 | AM/PM separation, exact limits, every action-precedence case, onset medians, ten-day gate, missing data, ordering |
| `tests/test_maintenance.py` | 15 | exact-07:00 aggregation, the 20/200 limits, doubled share, low-flag wording, coverage and stale warnings, ordering |
| `tests/test_api.py` | 17 | both endpoints for all three datasets equal the modules exactly, 400/422 cases, path refusal, real servers from the repo root and from `app/` |
| `tests/test_static.py` | 10 | `/` serves the built page with relative assets, API not shadowed, relative API URLs, no statistics in browser code |

## Application checks

| Check | Result |
|---|---|
| `bash app/testme.sh` (PORT 8713) | installed pinned requirements, started, `GET /api/datasets` answered 200 |
| real servers from the repo root (`app.app:app`) and from `app/` (`app:app`) | both returned identical reports; `../SPEC.md` gave 400, a missing name gave 422 |
| `npm --prefix app/frontend run build` | `✓ built`, 153.8 kB JS (49.8 kB gzip) into `app/static/` |
| browser (Claude desktop app's browser, `http://localhost:8720/`) | all three datasets, both windows, station switching, maintenance tab and the E01 no-limits state render with no console errors ([integration.md](integration.md)) |
| Posit Connect bundle (the 18 manifest files alone in an empty folder) | `/` 200 HTML, all three reports 200, planted maintenance flags as locally |
| deployment | **not done**: no publisher credentials on this machine ([deployment.md](deployment.md)) |
| secrets | `git grep` for key-shaped strings finds only `...` placeholders in the skill docs |

## Known limits of this verification

- The stable dataset flags nothing because its patterns were designed; real dock data is
  overdispersed (unusable snapshots clump), so real false alarms will be more frequent. An earlier
  random-walk version of the data flagged 14 of 300 stable points. Signals are labelled exploratory.
- `tools/check_agent_bundle.py` (the template maintainers' bundle check) reports its check 13 "no new
  top-level folders" as failing, because the project adds `app/`, `data/`, `demo/`, `tests/` and
  `.github/`, as SPEC and CONTRACT require. It is not part of any task's definition of done.
- Nothing was verified on a live Posit Connect server.
