# Autonomous Build Architecture — Bikeshare Fleets

**Status:** implementation-ready design decisions, not an implementation report. **Authority:** `SPEC.md` defines behavior, `CONTRACT.md` defines actual task/status/owned paths, `docs/plan.md` is the execution index, and this document defines interfaces and quality gates. If any guidance conflicts with SPEC, SPEC wins. The only unstated human facts are team name, exact Devpost prompt number, credentials and the status/location of Person B's H-02 branch. Never fabricate any of them.

## Outcome

Ship one publicly reproducible, visually polished, responsive **rush-hour bike-share dispatcher console**: separate per-station AM/PM availability diagnostics and timed bike movement/collection recommendations; a 07:00 network maintenance p-chart and ranked broken-bike station list. Every chart uses the **one exact-binomial p-chart** specified in SPEC §4, with transparent assumptions and an always-visible exploratory warning. Two REST GET endpoints; three generated synthetic datasets; FastAPI serves the built React application from the same Posit Connect service. No route optimization, maps, rider forecasts, uploads, live feed, authentication or second statistical technique.

## Architectural decision matrix

Scores: 1 (poor) to 5 (excellent), **subjective implementation estimates**. Weights are rubric/spec correctness 30%, completion speed 25%, integration safety 20%, deployability 15%, UX potential 10%. Score = weighted mean × 20; a decision is **locked** unless proven incompatible with SPEC or the runtime.

| ID and alternative | Correct (30) | Speed (25) | Safe integration (20) | Deploy (15) | UX (10) | /100 | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| A: One FastAPI service + built React | 5 | 4 | 5 | 4 | 5 | **92** | **Choose** |
| A: Separate React and API deployments | 5 | 2 | 3 | 2 | 5 | 68 | Reject CORS/multi-deploy |
| A: Python dashboard only | 3 | 4 | 4 | 4 | 3 | 72 | Reject SPEC mismatch |
| B: exact binomial + SciPy | 5 | 4 | 5 | 4 | 5 | **92** | **Choose** |
| B: normal 3-sigma p-chart | 1 | 5 | 5 | 5 | 4 | 74 | Reject small-n error |
| C: validated loader + two independent domain functions | 5 | 4 | 5 | 5 | 5 | **95** | **Choose** |
| C: monolithic FastAPI analytics | 3 | 4 | 2 | 5 | 4 | 69 | Reject coupling |
| D: bundled CSVs (allowlist) | 5 | 5 | 5 | 5 | 4 | **98** | **Choose** |
| D: database or live GBFS integration | 2 | 1 | 2 | 2 | 4 | 39 | Reject out of scope |
| E: return all station chart series in one JSON report | 5 | 5 | 5 | 4 | 5 | **97** | **Choose** |
| E: per-station additional endpoints | 3 | 3 | 3 | 4 | 4 | 65 | Reject endpoints creep |
| F: Recharts + custom CSS tokens | 5 | 4 | 5 | 4 | 5 | **92** | **Choose** |
| F: handcrafted SVG charts | 4 | 2 | 3 | 5 | 5 | 71 | Reject implementation risk |
| G: Claude Code orchestrates, Codex builds isolated tasks | 5 | 4 | 5 | 4 | 5 | **92** | **Choose** |
| G: both agents independently orchestrate one checkout | 2 | 3 | 1 | 4 | 4 | 51 | Reject conflicting edits |

Further locked choices: **G1** Python `csv` + `datetime` in loader (no DataFrame required), SciPy for exact tails; **G2** pytest+FastAPI TestClient, Vitest for presentation helpers, Playwright if available for visual checks; **G3** React/Vite with a single page and **relative** `/api` calls; **G4** no dependency on paid fonts, APIs, icon kits or hosted image assets; **G5** the only exposed controls are dataset selector, Availability/Maintenance tabs, AM/PM switch and station selector; **G6** light, high-contrast professional operator-console visuals; **G7** preserve `demos/fastapi/` four-script contract, deploy `app/` as one folder; **G8** no browser-side formula or action recomputation; **G9** all tests/reviews and documentation ship with their associated task, not at sprint end.

## Component and responsibility diagram

```text
       Person B: H-02                         Person A: H-03
 data/*.csv + data/README.md             app/qc.py + exact-tail tests
                |                                  |
                v                                  |
      app/data_loader.py                            |
         validated rows                             |
                |                                   |
          +-----+-----------------------------------+--------+
          |                                              |
          v                                              v
H-09 app/availability.py                      H-10 app/maintenance.py
 AM + PM per-station groups                      07:00 network/day groups
 charts + dispatch rules                         chart + inspection ranking
          |                                              |
          +----------------------+-----------------------+
                                 v
                           H-04 app/app.py
                 GET /api/datasets   GET /api/report
                          BACKEND TEST GATE
                                 |
                                 v
                      H-05 React/Vite (last)
         dataset | AM/PM | station | QC charts | action tables
                                 |
                                 v
                   compiled app/static + app/data
                                 |
                                 v
                        H-06 Posit Connect
                     ONE service; no cross-origin
```

## Data boundary and validation

- **CSV exact header:** `timestamp,station_id,num_bikes_available,num_bikes_disabled,num_docks_available`. Local ISO `YYYY-MM-DDTHH:MM` timestamps, station IDs as nonempty text, counts as nonnegative integers. Do **not** derive a total dock count from these fields or reject situations just because a dock total is missing: the SPEC does not supply one.
- Validate **all raw rows before filtering**: missing values, noninteger or negative counts, duplicate `(station_id,timestamp)` must return a clear error naming the CSV row. Then ignore weekends and snapshots outside 07:00–08:55 and 16:00–17:55. Missing 5-minute snapshots are permitted and reduce subgroup `n`.
- Record `timestamp` as local naive time, no timezone conversion. Chronologically sort weekdays and station IDs. Baseline = **first 10 distinct weekdays** of the dataset; never recompute baseline from event days. Report latest day = latest observed weekday.
- **Person B owns the loader API**. Canonical semantic record is `{timestamp: datetime, station_id: str, num_bikes_available: int, num_bikes_disabled: int, num_docks_available: int}`. If B returns DataFrames or models, use B's actual exported loader interface and a small adapter **inside an existing task-owned file** after B merges; do not overwrite B's H-02 implementation. Domain functions consume one normalized set of validated records.
- Bundled files: `stable.csv` and `planted_events.csv`: 10 × 15 weekdays × 48 snapshots; first 10 days share a baseline. `edge_case.csv`: 2 stations × 15 weekdays, at least one always usable station and some missing snapshots. Fixed random seed and generator/codebook; planted day-12 full PM and day-13 increased disabled-bike share must flag with exact-binomial limits.
- Counts may be simultaneously `bikes_available=0` and `docks_available=0`; **count that snapshot only once** in unusable `d`, but separately in empty and full descriptive counts. No implied trips or demand.

## Exact mathematical contract and edge policy

- Shared pure calculator accepts baseline counts `(d_i,n_i)` and a sequence of daily subgroup counts `(d_j,n_j)`, returns only numbers/nulls/flags/warnings (no FastAPI or React import). `p_bar = sum(d_baseline)/sum(n_baseline)`; for every subgroup `X~Binomial(n,p_bar)`, `alpha=0.00135`.
- Upper integer `u=min{k∈[0,n]: P(X>k)≤alpha}`; lower integer `l=max{k∈[0,n]: P(X<k)≤alpha}`. Use `scipy.stats.binom.sf(k,n,p_bar)` and `binom.cdf(k-1,n,p_bar)` (or equivalent rigorously tested functions), not `p_bar±3σ`. **UCL=u/n, LCL=l/n; high flag if d>u, low if d<l** (strict inequality); Western Electric rule 1 only.
- **Pure math vs product policy:** H-03 allows 4 baseline subgroups for the SPEC's known-answer fixture; full reports require **10 baseline weekdays**. `n=0` subgroup is omitted with an explicit warning; `p_bar=0` or `1`, fewer than 10 baseline days, or baseline opportunities zero -> `insufficient_basis`, **no fabricated limits or statistical signals**; descriptive station lists remain available.
- Exact known-answer tests copied from SPEC: `d=[2,4,3,3]`, `n=24 each` gives `p_bar=.125`; `u=9`, `UCL=.375`; `n=20 -> u=8, UCL=.40`; `d=10` flags, `d=8` does not. Maintenance `p_bar=.1,n=100 -> u=20,UCL=.20,l=2,LCL=.02`; `d=25` high and `d=20` not high; `d=1` low. Median `07:35,07:40,07:50` is `07:40` on 3 of 10 days.
- Interpret every alarm as **exploratory**, not a calibrated real-world false-positive probability: serially correlated snapshots break binomial independence. **Target=.10 is a service goal, never a control limit**. Show the number of stable-dataset flagged points with an observed count, not a guarantee of zero.

## Domain rules and resolved ambiguity policies

**H-09 Availability** (AM and PM computed separately; station × weekday × window):
- For each group, `n` = actually logged snapshots; `d` = observations with `bikes_available=0 OR docks_available=0`. Keep separate empty/full snapshot counts; table summarizes **latest observed day**.
- For each station/window and for **each condition (empty and full separately)** compute median of the *first affected snapshot clock time per baseline day*, using only affected baseline days, and report `days affected / 10 baseline weekdays`. No event → `median_time=null`, clear "not observed in baseline". Median of even count: midpoint rounded to nearest minute.
- SPEC **first-match priority**: (1) any full snapshot with disabled bikes → `collect_broken_bikes_first`; (2) latest above exact UCL → `investigate_special_cause` **plus** direction from rule 4; (3) latest in control and baseline `p_bar > .10` → `capacity_review`; (4) more empty than full snapshots → `drop_bikes`, more full than empty → `pull_bikes`; otherwise `ok`. "First match" selects **primary** action; a special-cause direction is a secondary display detail, not a second primary classification.
- For a directed van action, use median of the **matching** condition (empty onset for drops, full onset for pulls); if no baseline onset, display "before window starts (07:00/16:00); no baseline onset estimate" rather than inventing a statistical median. When empty/full counts tie, do not infer a movement direction. Deterministic ordering: actionable rows first, then `station_id`; don't invent a severity score.
- With `insufficient_basis` do not label the point "in control" or trigger the p-bar/limit-based actions; continue physically justified collections and count-based bike movements if input exists.
- These recommendations use observed behavior; describe them as **operational guidance**, not predicted demand or optimized van assignments.

**H-10 Maintenance:** at each weekday **07:00 exactly**, sum `d=disabled`, `n=available+disabled` across present stations. Use 10 baseline weekdays for one network chart. For latest day's 07:00 observations, list stations with `disabled>0` sorted by disabled descending then ID; action "inspect and collect broken bikes". Missing 07:00 checkpoint for a station reduces opportunity count; all missing/zero n generates warning; never silently infer 07:00 from 07:05.

## Frozen JSON API contract

`GET /api/datasets`: `{"datasets":["stable.csv","planted_events.csv","edge_case.csv"]}`; no arbitrary CSV paths. `GET /api/report?dataset=stable.csv` returns **one complete** report to eliminate extra frontend calls; preserve stable key spellings:

```json
{
  "dataset": "stable.csv",
  "meta": {
    "synthetic": true, "exploratory": true, "baseline_days": 10,
    "target_unusable_share": 0.1, "latest_day": "2026-10-15",
    "warning": "Synthetic demonstration; signals are exploratory."
  },
  "availability": {
    "AM": {
      "stations": [
        {
          "station_id": "S01", "unusable_share": 0.125,
          "empty_count": 3, "full_count": 0,
          "p_bar": 0.125, "ucl": 0.375, "flagged_high": false,
          "first_unusable_time": "07:40", "affected_baseline_days": 3,
          "baseline_days": 10, "primary_action": "drop_bikes",
          "secondary_note": null, "action_deadline": "07:40"
        }
      ],
      "charts_by_station": {
        "S01": {
          "status": "ok", "p_bar": 0.125, "warning": null,
          "points": [
            {
              "date": "2026-10-15", "d": 3, "n": 24,
              "p": 0.125, "lcl": 0, "ucl": 0.375,
              "flagged_high": false, "flagged_low": false
            }
          ]
        }
      }
    },
    "PM": { "stations": [], "charts_by_station": {} }
  },
  "maintenance": {
    "chart": {"status":"ok","p_bar":0.10,"warning":null,"points":[]},
    "stations": [{"station_id":"S01","num_bikes_disabled":2,"action":"inspect_collect"}]
  }
}
```

**These sample values illustrate shape only; never copy them into the generated dataset or demo as observed results.** For `insufficient_basis`, `p_bar`, `ucl`, `lcl` and signal flags are `null` rather than zero. Chart points always use `YYYY-MM-DD`; clock times use `HH:MM`. Empty/missing series may be `[]`. Decide no additional APIs. Bad dataset name -> HTTP 400 and JSON error; malformed allowlisted CSV -> 422 with source row; missing deployment file -> 500 with readable nonsecret error. Tests assert full schema and exact types.

## UI visual design — "The Shift Desk"

**Goal:** something a dispatcher can understand in **10 seconds**, not an academic control-chart sandbox. No decorative maps or fabricated city imagery. One page, modern operations-console aesthetic, accessible contrast and typography. Build after the backend gate, using `app/frontend/` React/Vite, **Recharts** for actual data charts, and CSS variables with a restrained palette and no paid dependencies.

- **Palette:** canvas `#F5F7FA`, cards `#FFFFFF`, ink `#14243A`, muted `#5A6B7D`, main blue `#2563EB`, safe green `#147D64`, caution amber `#B66A00`, alert red `#C62828`, hairline `#E4E9F0`. No reliance on color alone: pair colors with labels/icons.
- **Typography:** system sans/Inter if already available, clear 28–32px page heading, 16px key values, 12–14px labels; chart grid subtle, labels readable. Rounded 12–16px cards, restrained shadows, consistent 8px spacing rhythm.
- **Header:** "Bikeshare Shift Desk" + concise description + dataset dropdown + fixed "SYNTHETIC · EXPLORATORY SIGNALS" info strip.
- **KPI strip (computed by backend, never invented):** latest day; stations needing action (availability window), network broken-bike share at 07:00, and baseline target `≤10%` for context. Omit unavailable figures instead of filling placeholders with false precision.
- **Availability tab:** AM / PM segmented switch; dispatch table **first** (priority rows with action badge, observed share, empty/full counts, baseline share, UCL, first unusable time and deadline); selected station p-chart below or beside table with daily dots, **stepped** UCL/LCL if n changes, baseline centerline, the 0.10 target line, red highlighted out-of-control days, rich tooltip (date, d/n, control limits), explicit legend. Selecting a station updates the chart without another backend request.
- **Maintenance tab:** 07:00 network p-chart with exact limits and real points; below it ranked stations with disabled-bike counts and the exact "inspect and collect" action. Strong empty/warning states.
- **Responsive:** desktop two-column analysis region where space permits, mobile single column, table scrolls horizontally or becomes accessible stacked cards, controls remain reachable at 390px; no horizontal page overflow. Accessible `button`, `select`, table headers, focus states, chart text alternative and keyboard navigation.
- **Visual QA:** Playwright screenshots at **1280×800 and 390×844**, on both tabs and with `edge_case.csv`. Confirm axes, tooltips, action readability, chart limits, hover/focus and warning states. If Playwright missing, use a headless browser alternative or report visual check unverified; do not claim screenshots exist if they don't.
- **Content microcopy:** "Above the usual range: investigate" / "Above the 10% service target but within control: capacity review" / "No usable control limits for this station"; don't call any point a prediction.

## Build package, operation, deployment

- **One deployable directory `app/`**: `app/app.py` serves `/api/...` first, then static React's `index.html` for UI routes; `app/qc.py`, `app/availability.py`, `app/maintenance.py`, `app/data_loader.py`; `app/data/*.csv` copied from root before manifest; `app/static/` contains compiled Vite output. Build source stays at `app/frontend/`. Include dependency pins, use relative `/api` URLs and same-origin requests; do NOT deploy React as a second Posit item.
- **Four-script contract:** `app/testme.sh` starts local app with one command; `app/manifestme.sh` builds deployment manifest after assets/data staged; `app/deployme.sh` publishes to course Posit Connect; `app/README.md` explains them. Run from root and `app/` as specified. Verify `rsconnect-python` availability and permissions before reporting deployed.
- **Reproducibility:** `python -m pytest -q` passes from fresh clone with documented setup; deterministic dataset generator (seed and source) reproduces CSVs byte-for-byte; `npm ci` then `npm run build` must succeed; the one local `app/testme.sh` must serve the API and page once declared prerequisites are installed.
- **Security:** no secrets, arbitrary filesystem paths, database or uploads; whitelist three datasets; do not commit live keys, tokens or secret-filled screenshots. If Connect credentials aren't available, produce deployment-ready manifest/docs, mark deployment blocked, never fake a URL.

## Rubric-proof acceptance suite (100 possible points; not a guaranteed score)

| Rubric category | Pts | Hard evidence needed |
|---|---:|---|
| Effective, working tool | 25 | Single local URL, both API GETs and React load; interaction smoke tests; public deployed HTTP 200 when available |
| Valid QC statistics | 25 | All exact-binomial known-answer asserts, baseline contamination test, strict-limit equality tests, degenerate handling, planted signal and independent reviewer PASS |
| Prompt-aligned scope | 5 | AM/PM dock unavailability and maintenance dispatch, no routing/forecasting scope creep |
| Clear user and use case | 5 | Dispatcher role + two decisions explicitly visible in UI and README |
| Minimal reasonable inputs | 5 | Only GBFS-shaped feed, fixed rush windows, 10-day baseline, 0.10 target; no unnecessary input fields |
| Clear dataset demonstrations | 10 | All three datasets selectable with exact observed example outputs, annotated charts and recorded stable false-alarm count |
| Excellent documentation | 10 | Root and per-task docs, exact setup, inputs, parameters, formulas, action precedence, limitations, screenshots and data interpretation |
| 2–3 working datasets | 5 | stable, planted_events, edge_case all validate and visibly demonstrate intended behavior |
| Codebook | 5 | `data/README.md` lists every file/column/unit/seed/generation and how to capture GBFS feed for real |
| Public reproducible repo | 5 | Public GitHub URL, clone/setup/build/tests, no secrets, verified Posit URL and Devpost entry if submitted |
| **TOTAL** | **100** | **Never claim 100/100 awarded; report pass/fail evidence per row** |

## Autonomous orchestration state machine and recovery

1. **PREFLIGHT:** check branch cleanliness, tools (`git`, Python, pytest, Node/npm, `codex`, `claude`, browser support), permissions, SPEC/CONTRACT; record gaps. Avoid modifying Person B's existing H-02 branch. Determine working directory and available CLI commands with `--help`, not guessed flags.
2. **PLAN FROZEN:** use this architecture; do NOT ask routine design questions or re-create the plan. Open tasks H-01–H-10 according to their actual state. Complete H-01 verification without changing SPEC's statistical scope.
3. **PARALLEL BACKEND FOUNDATION:** B finishes H-02 independently; Codex works H-03 in isolated worktree. Reviewer (Claude fresh context) verifies H-03; deterministic tests must print observed numbers.
4. **MODULE FAN-OUT:** once H-02+H-03 merged and interfaces stabilized, Codex H-09 availability and B/another independent Claude worker H-10 maintenance in separate worktrees; no two workers edit the same checkout/task-owned file.
5. **GATE H-04:** after both modules pass read-only reviews, implement API, then full unit/API tests and actual GET checks for all three datasets and errors. Only H-04 **done** unlocks H-05.
6. **FRONTEND H-05:** implement the visual specification above, build React, integrate with single FastAPI process, run screenshots and accessibility/readability checks. Bugs are corrected and tests rerun; no guessed metric values.
7. **RELEASE H-06–H-08:** package assets/CSVs, deploy/verify public URL, audit/reproduce docs, submit if the external submission permissions/session are already available; otherwise explicitly report the single blocking external action.
8. **CLOSED LOOP:** implement → actual tests → fresh independent review → authorized commit → merge/refresh → updated task status and evidence. Limit retries for any repeated failure (e.g. 3 different fixes per root cause) and escalate only after diagnostics; no infinite loops and no false "done". Capture command output and resulting URL/commit. Do not overwrite concurrent H-02 progress or weaken tests just to get green.
9. **AUTONOMY BOUNDARY:** one master execution prompt can give explicit standing permission for task-branch commits/pushes and merging reviewed changes into an integration branch. Any different permission required by repository/host must be respected; deployment secrets and manual Devpost sign-in cannot be synthesized. On blocked external steps, complete all unblocked work then report precise action needed.

**Final deliverable:** working product, tests, three datasets, responsive dashboard, correct exact-binomial charts and dispatch priorities, live link if credentials exist, documented reproducibility, task ledger evidencing completion, and an honest rubric scorecard with screenshots/test outputs.
