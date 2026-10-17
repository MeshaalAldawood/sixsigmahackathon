# CONTRACT — Bike-share Two-Hour MVP

**Status:** Approved architectural direction; execution has not started.  
**Product scope:** [SPEC.md](SPEC.md) (authoritative for what the tool does).  
**Executable task ledger:** [CONTRACT.yaml](CONTRACT.yaml) (authoritative for owners, status, paths, and completion checks).

## Goal and non-goals

Build a reproducible, synthetic-data demonstration for one bike-share operations supervisor making **two independent station-level decisions**: (A) which stations need a working bike added/removed; (B) which stations need broken-bike inspection/collection. Provide one exploratory p-chart and one prioritized station table per module. **No** van routing, repair scheduling, forecasting, optimization, logins, databases, live feeds, or third statistical method.

## Architecture decisions — frozen for this sprint

| ID | Decision | Why |
|---|---|---|
| A | **Python/FastAPI + one minimal React/Vite page, served by one FastAPI deployment** | Matches SPEC; only one public URL. |
| B | **One plain, tested `app/qc.py` p-chart function** | One source of statistical truth, independent of UI. |
| C | **`availability.py` and `maintenance.py` are independent** | Distinct file ownership; neither imports the other. |
| D | **Two bundled synthetic CSVs with one five-column schema** | Reproducible, minimal inputs, no backend storage. |
| E | **One combined JSON reporting endpoint** | Frontend displays results rather than recalculating them. |
| F | **Deterministic station-level rules, no weighted prioritization model** | Simple, explainable, testable. |
| G | **Deployment bundle includes compiled React and copies of both CSVs** | Posit Connect deploys `app/` only; files outside it cannot be assumed available. |

Decision comparison (subjective engineering estimates; criteria: speed 30%, statistical testability 25%, independent work 20%, deployment 10%, SPEC fit 15%; each rated 1–5):

| Architecture | Speed | Stats | Parallel | Deploy | SPEC | Weighted /100 |
|---|---:|---:|---:|---:|---:|---:|
| **Single FastAPI + React build** | 4 | 5 | 5 | 4 | 5 | **92** |
| FastAPI + plain HTML | 5 | 5 | 5 | 5 | 1 | 88 |
| Separate FastAPI + React deployments | 2 | 5 | 4 | 2 | 5 | 72 |
| Python Shiny | 4 | 4 | 3 | 4 | 2 | 70 |

We choose the first option. This is a **two-hour target**, not a guarantee that deployment credentials or service availability will cooperate.

## Data and function contracts

Every CSV has exactly `timestamp,station_id,total_docks,working_bikes,broken_bikes`, with one station per daily snapshot. Counts are nonnegative integers and `working_bikes + broken_bikes <= total_docks`; the station set is identical at every checkpoint. `empty_docks = total_docks - working_bikes - broken_bikes`. Reject malformed inputs; do not silently repair them.

The loader returns validated observations ordered by date and station. Each module accepts the same validated observations and independently produces:

- `chart`: `status` (`ok` or `insufficient_basis`), `p_bar` (number or null), `warning` (string or null), and `points` (date, failures, opportunities, p, LCL, UCL, flagged). Use null control limits/flags if the statistical prerequisites fail.
- `stations`: ordered records with `station_id`, relevant counts, `action`, and `reason`. Availability shows actionable stations before nonactionable stations (ties by ID). Maintenance lists stations with broken bikes by count descending, ties by ID.

`GET /api/datasets` returns only `stable.csv` and `deterioration.csv`. `GET /api/report?dataset=stable.csv` returns `{ "dataset": "...", "availability": { ... }, "maintenance": { ... } }`. The API rejects other filenames, returns readable validation errors, and never recomputes statistics in JavaScript.

**Availability rule:** zero rentable bikes plus free dock -> `add_bike`; zero free docks plus a rentable bike -> `remove_bike`; full station containing only broken bikes -> `collect_broken_bike`; otherwise `none`. This is a *station-level suggested action*, not a van dispatch. **Maintenance rule:** any broken bikes -> `inspect_collect`, ordered by number broken.

## Statistical contract: known, conditional, and testable

- For daily totals `f` problems out of `n` opportunities, `p = f/n`. First **20** checkpoints are the fixed baseline; `p_bar = sum(f_baseline)/sum(n_baseline)`.
- Each day's standard 3-sigma p limits are `max(0, p_bar - 3*sqrt(p_bar*(1-p_bar)/n))` and `min(1, p_bar + 3*sqrt(p_bar*(1-p_bar)/n))`. Flag only strictly outside limits.
- **Verified hand calculation:** baseline 10 failures / 100 opportunities gives `p_bar=0.10`. At `n=100`, standard deviation `sqrt(0.10*0.90/100)=0.03`, so limits are `0.01` and `0.19`; `25/100=0.25` exceeds UCL. This proves the arithmetic **under the p-chart assumptions**, not the validity of a real-world alarm.
- Refuse to report standard control limits when baseline has fewer than 20 checkpoints, any observation has zero opportunities, `p_bar` is 0 or 1, or the approximation check `n*p_bar >= 5` and `n*(1-p_bar) >= 5` fails. Return `insufficient_basis` with an explanation. Still show valid station lists.
- Same stations/bikes are repeatedly observed, so data may be serially correlated; **label all control-chart signals exploratory**, never calibrated failure probabilities. Generate data where the normal approximation is satisfied in the demonstration; never suppress a failed assumption test.
- Test zero/constant counts, invalid capacity, missing data, ties, and a planted deterioration. Control limits are **not** service thresholds.

## Build ownership and parallel documentation

All task state/check-ins live in [CONTRACT.yaml](CONTRACT.yaml); its `owns` paths do not overlap. **Each task must deliver its tests AND its documentation in the same work unit and commit**. Documentation is *not* deferred to the end.

| Workstream | Owner | Owns | Documentation produced while building |
|---|---|---|---|
| Data and validation | Developer B | `data/`, `app/data_loader.py`, loader tests | `data/README.md` |
| Statistical core | Developer A | `app/qc.py`, QC tests | `docs/statistics.md` |
| Availability | Developer A | `app/availability.py`, availability tests | `docs/availability.md` |
| Maintenance | Developer B | `app/maintenance.py`, maintenance tests | `docs/maintenance.md` |
| Backend API | Developer B / integrator | `app/app.py`, backend scripts/deps, API tests | `app/README.md`, `docs/api.md` |
| Frontend (only after gate) | Developer A | `app/frontend/` | `app/frontend/README.md` |
| Bundle, test, publish | Developer B / integrator | `app/static/`, `app/data/`, deployment manifest and tests | `docs/integration.md`, `docs/deployment.md` |
| Demo and submission audit | Developer A | `README.md`, `demo/README.md` | Collates **already-written** documentation; checks completeness |

No developer edits the other's analysis files. Shared interface changes require both developers to agree first and be reflected in this contract.

## Timeline and hard gates (120 minutes)

| Elapsed | Work | Gate |
|---|---|---|
| 0–10 min | Read SPEC + CONTRACT; freeze JSON schema and task ownership | Both owners understand interfaces |
| 10–35 min | **Parallel:** B produces data + loader; A builds shared p-chart + numeric tests | Data codebook + known-answer QC test |
| 35–65 min | **Parallel:** A builds availability; B builds maintenance and thin FastAPI API | Independent tests and JSON endpoints |
| 65–75 min | **BACKEND VERIFICATION GATE** | All Python unit/API tests pass; both datasets yield expected reports |
| 75–95 min | **Frontend begins only now:** one React page, dataset selector, two tabs, one chart/table each | React build succeeds |
| 95–105 min | Integrate built frontend into FastAPI static serving; inspect real API outputs | One local URL serves page and API |
| 105–120 min | Prepare deployment bundle, smoke test, publish and audit README/demo | Public URL verified if credentials available |

**Hard rule:** if backend tests fail at minute 75, fix the backend before frontend work. Cut visual polish or use FastAPI `/docs` as a fallback demo if time runs short; do **not** claim the prescribed React deliverable is complete unless it exists.

Before the gate: run `python -m pytest tests/test_data_loader.py tests/test_qc.py tests/test_availability.py tests/test_maintenance.py tests/test_api.py`. Check both `/api/datasets` and `/api/report` for the two approved datasets and for bad filenames. Test stable behavior and a planted deterioration. **No frontend coding before these pass.**

## Packaging and submission safeguards

The root `data/` directory is the source of truth. Before creating the Posit Connect manifest, **copy exactly the two datasets into `app/data/`**, build React to `app/static/`, and ensure FastAPI finds its bundled data in deployment and the root dataset in local development. The API should serve static files when present; tests/API must still work without static assets. Publish only from `app/` using its existing `testme`, `manifestme`, and `deployme` scripts; verify the live page and live API from a logged-out browser. Do not commit tokens or secrets.

At final review, confirm the exact Devpost challenge title, team name and track still marked TBD in SPEC, then verify the [rubric](docs/criteria.md): working tool (25), valid QC (25), design (25), documentation/reproducibility (25). The team submits its public GitHub repo and demonstration. Documentation is drafted throughout the sprint, with only a final accuracy check at submission.
