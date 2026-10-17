# CONTRACT — Bikeshare Fleets Hackathon

**Source of truth:** `SPEC.md` defines the product; this **`CONTRACT.md`** is the task ledger; `docs/plan.md` describes architecture and sequencing. The task order below is intentional: H-09 and H-10 run before the H-04 backend gate.

## Working rules

1. Build only a listed task; propose any new task before starting it.
2. Check out one task per agent/person by changing only its **Status**, **Owner**, and **Started at** fields. Allowed statuses: `todo`, `in_progress`, `blocked`, `done`.
3. Work only in **Owns** paths. If two agents need the same file, coordinate its owner first. When work is verified, change **Status** to `done` and record a factual one-line **Result** in the same commit as the task files.
4. Run the task's **Definition of done** and quote its actual output; never mark a task done without verification. Code, tests and task-specific documentation are completed together.
5. The **frontend cannot start until H-04's backend gate is done**. Keep all statistics in Python and the three datasets synthetic. Do not add new features or secrets.
6. Read this Markdown file directly. **No YAML ledger or YAML parser is required**. Use `bash .claude/skills/superagent/scripts/check.sh` to inspect task statuses.

## Tasks (execution order)

### H-01 — Confirm finalized SPEC and record implementation decisions

**Points:** 15 - Tool Design: prompt alignment (5), clear user/decision (5), minimal inputs (5)

**Status:** `done`

**Owner:** `Codex + Team Six`

**Started at:** `2026-10-17 00:38`

**Owns:** `SPEC.md`, `docs/plan.md`

**Notes:** The uploaded SPEC is the finalized product contract; preserve its full nine-section template. Align docs/plan.md with exact binomial p-charts, AM/PM station windows, maintenance at 07:00, fixed 0.10 target, three datasets, one FastAPI plus React deployment, and backend-first sequencing. Only team name and official Devpost prompt number remain to confirm; do not guess them or block initial code on these metadata blanks.

**Definition of done:** test -f docs/plan.md && grep -q "exact binomial" docs/plan.md && grep -q "planted_events.csv" SPEC.md && grep -q "edge_case.csv" SPEC.md; team has reviewed this finalized scope.

**Result:** `Team Six spec and reviewed 56-line execution plan approved for push; H-01 file checks passed, all 10 tasks and 38 ownership entries covered; official prompt number remains a metadata follow-up.`

### H-02 — Three reproducible rush-hour CSV datasets and codebook

**Points:** 10 - Tool Documentation: 2-3 working test datasets (5), codebook (5)

**Status:** `done`

**Owner:** `Codex implementer: h02_data`

**Started at:** `2026-10-17 09:40`

**Owns:** `data/`, `app/data_loader.py`, `tests/test_loader.py`, `tests/test_data.py`

**Notes:** Create stable.csv, planted_events.csv, edge_case.csv and data/README.md with a recorded random seed and generation method. EXACT input columns: timestamp,station_id,num_bikes_available,num_bikes_disabled, num_docks_available. Normal/event datasets: 10 stations x 15 weekdays x 48 five-minute snapshots (24 AM 07:00-08:55 and 24 PM 16:00-17:55); first 10 weekdays are the shared baseline. Edge dataset: 2 stations x 15 weekdays with one always-usable station and missing snapshots. Plant: day-12 PM stadium full-station anomaly, broken-bike share doubles starting day 13. Include residential/downtown opposing rush patterns, chronic hilltop above 0.10 but in control, stable broken share. Never represent synthetic values as real observations. Codebook documents units, seed, expected flags, stable false-alert count and GBFS logging.

**Definition of done:** python -m pytest tests/test_data.py tests/test_loader.py -q && test -f data/stable.csv && test -f data/planted_events.csv && test -f data/edge_case.csv && test -f data/README.md; tests prove file schemas, checkpoint counts, shared baseline, seeded reproducibility, planted signals and missing-snapshot case. app/data_loader.py rejects invalid row counts and duplicates with row numbers and filters weekdays/rush windows; its tests pass here.

**Result:** `15 loader/data tests passed; three reproducible synthetic CSVs, codebook and validated sorted loader delivered.`

### H-03 — One exact-binomial p-chart function with numeric tests

**Points:** 25 - Tool Implementation: valid quality-control statistics in Python

**Status:** `done`

**Owner:** `Codex implementer: h03_qc`

**Started at:** `2026-10-17 09:40`

**Owns:** `app/qc.py`, `app/requirements.txt`, `tests/test_qc.py`, `docs/statistics.md`

**Notes:** Load stats-first-steering first. Implement the one tested p-chart statistic with exact binomial tail limits alpha=0.00135 and Western Electric rule 1 only; never substitute normal 3-sigma limits. Core arithmetic must accept a four-day hand-calculation fixture independent of the application's minimum-ten-baseline-day gate. Check availability: baseline d=2,4,3,3 with n=24 each => p_bar=.125, n24 upper count 9/UCL=.375, n20 upper count 8/UCL=.40, d10 high, d8 not high; lower count 0. Maintenance: 10/100 => upper count 20/UCL=.20, lower count 2/LCL=.02; d25 high, d20 not; d<=1 below lower limit. Test p_bar=0/1, n=0, insufficient baseline at report level, missing inputs and varying n. Use scipy.stats.binom.sf/cdf as source of exact tails and pin dependencies. Write docs/statistics.md now, including correlation/exploratory warning.

**Definition of done:** python -m pytest tests/test_qc.py -q && test -f docs/statistics.md; numeric assertions reproduce every SPEC section-4 hand answer including changed-n limits, boundary equality, lower flags and invalid cases.

**Result:** `13 QC tests passed; independent review confirmed the exact availability and maintenance limits and degenerate cases.`

### H-09 — Availability AM/PM decision module and tests

**Points:** 25 - Working-tool implementation (availability portion)

**Status:** `done`

**Owner:** `Codex implementer: h09_availability`

**Started at:** `2026-10-17 09:44`

**Owns:** `app/availability.py`, `tests/test_availability.py`, `docs/availability.md`

**Notes:** Separate station p-charts for AM and PM; subgroup is station x weekday x rush window, d=count of unusable snapshots, n=count actually logged. Unusable = bikes_available==0 OR docks_available==0. Empty and full counts remain distinct. Baseline is first 10 weekdays; target=.10 is an SLA target, NOT a statistical control limit. Compute median first empty/full clock times over baseline affected days with numerator/ denominator wording, e.g. "07:40 on 3 of 10 days". Follow EXACT first-match action precedence from SPEC: full with disabled bikes => collect first; high special-cause flag => investigate PLUS van direction; in-control but p_bar > .10 => capacity review; then empty>full drop or full>empty pull BEFORE typical onset time; otherwise OK. Actionable rows first; tie station_id; show both windows and latest-day table. Missing snapshot reduces n; n=0 gets no limits/warning. Must not import maintenance module. Document rules as this is built.

**Definition of done:** python -m pytest tests/test_availability.py -q && test -f docs/availability.md; tests cover AM/PM separation, exact control limits, actions/precedence, missing snapshots, chronic target vs special-cause signal, median time and ties.

**Result:** `5 availability tests passed; independent review confirmed separate windows, stepped limits, onset timing and action precedence.`

### H-10 — Maintenance 07:00 network p-chart and station list

**Points:** 25 - Working-tool implementation (maintenance portion)

**Status:** `done`

**Owner:** `Codex implementer: h10_maintenance`

**Started at:** `2026-10-17 09:44`

**Owns:** `app/maintenance.py`, `tests/test_maintenance.py`, `docs/maintenance.md`

**Notes:** One daily NETWORK subgroup at 07:00 only: d=sum disabled bikes and n=sum available plus disabled bikes across stations. Use exact-binomial QC function, first 10 weekdays as baseline, and one point per weekday. At most recent 07:00 snapshot, sort broken-bike stations by disabled-bikes descending then station_id. Action "inspect and collect broken bikes", no repair estimates. No availability-module import. Warn if n=0 or baseline invalid. Document fields, assumptions and warnings in same task.

**Definition of done:** python -m pytest tests/test_maintenance.py -q && test -f docs/maintenance.md; tests cover 07:00 aggregation, no duplicate counting, exact binomial flags, changing broken share, zero denominator, station ordering and ties.

**Result:** `7 maintenance tests passed; independent review confirmed exact 07:00 aggregation and the planted 40/400 signal.`

### H-04 — Complete FastAPI backend and pass hard backend test gate

**Points:** 25 - Tool Implementation: effective, working REST API

**Status:** `done`

**Owner:** `Codex implementer: h04_api`

**Started at:** `2026-10-17 09:48`

**Owns:** `app/app.py`, `app/__init__.py`, `app/testme.sh`, `app/manifestme.sh`, `app/deployme.sh`, `app/.python-version`, `app/README.md`, `tests/test_api.py`, `docs/api.md`

**Notes:** Start after H-02, H-03, H-09 and H-10 are implemented and verified. Use the validated app/data_loader.py from H-02. Copy/adapt demos/fastapi (preserve its four-script contract). Reject invalid source records naming row number; ignore weekends and outside-window snapshots, tolerate missing observations. Serve GET /api/datasets (three whitelisted CSVs) and GET /api/report?dataset=<name> with availability AM and PM station results, exact p-chart points, chart warnings, maintenance results. No arbitrary file paths, no live feeds and no statistics in API. API must work without frontend assets and serve a built dist if present. Imports must pass from repo root AND with app/ as cwd. Write app/README.md and docs/api.md during implementation. HARD GATE: do not check this in or start H-05 frontend before all backend tests pass with all three datasets and edge cases.

**Definition of done:** python -m pytest tests/test_data.py tests/test_qc.py tests/test_availability.py tests/test_maintenance.py tests/test_loader.py tests/test_api.py -q exits 0; test -f app/testme.sh && test -f app/manifestme.sh && test -f app/deployme.sh && test -f app/README.md && test -f docs/api.md; verify both API endpoints with stable, planted_events, edge_case and invalid-name requests and startup from both the repo root and app/ directory.

**Result:** `44 backend tests passed; all three reports, invalid-name handling, and root/app startup were verified.`

### H-05 — Minimal React frontend after backend gate and demo walk-through

**Points:** 10 - Tool Design: clear demonstration on three test datasets

**Status:** `done`

**Owner:** `Codex implementer: h05_frontend`

**Started at:** `2026-10-17 09:53`

**Owns:** `app/frontend/`, `app/static/`, `tests/test_static.py`, `docs/integration.md`, `demo/README.md`

**Notes:** DO NOT START BEFORE H-04 IS DONE. Start from demos/reactfront/ under app/frontend/ and build dist to app/static/ (same API origin). Page: selector for all three datasets, persistent synthetic/exploratory warning, Availability tab with AM/PM switch, latest-day dispatch table, station selector and station p-chart including stepped UCL/LCL, centerline, target=.10, red flags, median first-unusable time. Maintenance tab: network 07:00 chart, ranked broken-bike list. React must render backend results, not recalculate any statistic. demo/README.md records observed output and stable false-alert count for each dataset; docs/integration.md documents build/serve steps.

**Definition of done:** npm --prefix app/frontend run build && python -m pytest tests/test_static.py -q && python -m pytest -q; one local FastAPI origin renders a built React page, three datasets, AM/PM station and maintenance charts, recommended actions and warning states; demo/README.md walks through all three examples with actual observed results.

**Result:** `React bundle built; 3 static tests and 47 full-suite tests passed with three dataset walkthroughs.`

### H-06 — Deploy one bundled FastAPI and React app to Posit Connect

**Points:** Protects 25 working-tool points - public app required

**Status:** `todo`

**Owner:** `unassigned`

**Started at:** `—`

**Owns:** `app/data/`, `app/manifest.json`, `.github/workflows/`, `.github/scripts/`, `docs/deployment.md`

**Notes:** Source CSVs remain in root data/ and are copied into app/data/ for Connect deployment from app/. Include built React static assets, all required Python modules and pinned dependencies. Follow connect-publish instructions and the four scripts. Use actual course Connect publisher credentials from local secret settings; NEVER commit keys, tokens or server secret values. Produce docs/deployment.md with real commands/errors/URL while working.

**Definition of done:** A public Posit Connect URL, visited logged out, serves the React page and all three whitelisted reports with HTTP 200; deployment docs contain actual test commands/results and URL, and app/data/ contains the exact three approved CSVs.

**Result:** `—`

### H-07 — Audit incremental documentation and reproducibility

**Points:** 10 - Tool Documentation: complete user and function documentation

**Status:** `done`

**Owner:** `Claude Code`

**Started at:** `2026-10-17 10:50`

**Owns:** `README.md`, `docs/verification.md`

**Notes:** Documentation was produced alongside each implementation task: data/README.md, docs/statistics.md, docs/availability.md, docs/maintenance.md, docs/api.md, docs/integration.md, docs/deployment.md and demo/README.md. THIS IS AN AUDIT, not an end-of-project documentation writing phase. Root README explains who/decision, every input/parameter, exact p-chart rules and assumptions, how to run, and one worked demo per each of the three datasets. Record an independent review in docs/verification.md.

**Definition of done:** python -m pytest -q passes and test -f README.md && test -f docs/verification.md; a fresh-clone reader can run app/testme.sh and reproduce exact binomial hand-answer checks and the three dataset demonstrations from documentation.

**Result:** `63 pytest + 4 vitest pass on a fresh clone; testme.sh and testme.ps1 serve all three reports; README rewritten for the tool with inputs, exact rules, hand checks and three demos; docs/verification.md records the review.`

### H-08 — Verify reproducible public repo and submit on Devpost

**Points:** 5 - Tool Documentation: public reproducible GitHub repository

**Status:** `todo`

**Owner:** `unassigned`

**Started at:** `—`

**Owns:** `.gitignore`

**Notes:** Confirm the previously unknown team name and exact Devpost prompt number in SPEC through the H-01 owner. Verify on-campus deadline, public repository, live demonstration and fresh-clone tests. Check .gitignore and absence of secrets; never falsely claim a submission or live service before verifying it.

**Definition of done:** Fresh clone runs app/testme.sh and python -m pytest -q; public repository contains reproducible code and no credentials, Devpost submission references the repository and verified public Posit Connect URL; record the actual confirmation.

**Result:** `—`

### H-11 — Simulated replay backend and statistical integrity

**Points:** Protects valid statistics and working-tool behavior

**Priority:** `P0` replay cutoff and frozen baseline; `P1` onset denominator

**Status:** `done`

**Owner:** `Codex implementer: h11_replay`

**Started at:** `2026-10-17 10:04`

**Owns:** `SPEC.md`, `app/replay.py`, `app/app.py`, `app/availability.py`, `app/maintenance.py`, `tests/test_replay.py`, `tests/test_api.py`, `tests/test_availability.py`, `tests/test_maintenance.py`, `docs/api.md`, `docs/availability.md`, `docs/maintenance.md`

**Notes:** Begin after H-04/H-05 gates. Add an optional as_of cutoff to the bundled synthetic report and return observed current station state without future observations. Keep the original first ten weekdays as the fixed baseline; withhold baseline-derived values before calibration completes. Mark incomplete AM/PM windows provisional, suppress final signals and verdicts, and expose coverage and staleness. Count onset days with observed baseline snapshots in the denominator and report missing days. See docs/plan.md for boundaries and fixtures. Reopen and transfer overlapping files from completed tasks only after their owners release them.

**Definition of done:** python -m pytest tests/test_qc.py tests/test_availability.py tests/test_maintenance.py tests/test_api.py tests/test_replay.py -q exits 0; tests show future-suffix invariance at a fixed cutoff, frozen baseline, prebaseline and closing-boundary behavior, rewind, missing station/07:00 observations, onset 07:40 on 3 of 8 observed days when two baseline days are missing, and historical parity at the final cutoff. Independent numeric review records actual values.

**Result:** `41 tests passed; independent review PASS: future-suffix invariance, frozen 10-day baseline, 09:00/18:00 provisional boundaries, rewind, missing/stale stations, onset 07:40 on 3 of 8 observed days, final-cutoff parity.`

### H-12 — Replay controls, correct chart rendering and dashboard QA

**Points:** Protects working-tool clarity and demonstration quality

**Priority:** `P1`

**Status:** `done`

**Owner:** `Codex implementer: h12_dashboard`

**Started at:** `2026-10-17 10:18`

**Owns:** `app/frontend/`, `app/static/`, `tests/test_static.py`, `docs/integration.md`, `demo/README.md`

**Notes:** Begin after H-11. Add Play/Pause, seek, speed, snapshot steps, explicitly synthetic event jumps and current station status. Use backend values only. Draw connected stepped limits across valid observations and break at null values; never plot missing values at zero. Show provisional points and warnings. Polish mobile layout, keyboard access, focus, contrast and reduced motion. Record browser QA at desktop, tablet and phone sizes.

**Definition of done:** npm --prefix app/frontend ci && npm --prefix app/frontend run test -- --run && npm --prefix app/frontend run build && python -m pytest tests/test_static.py -q exit 0; browser QA covers all three datasets, both windows, maintenance, rewind, null values, keyboard access and 1440px/768px/375px layouts with recorded screenshots and observations.

**Result:** `4 vitest + 3 static tests passed, bundle rebuilt; Playwright QA at 1440/768/375 across all three datasets, both windows, maintenance, keyboard rewind and null limits recorded in docs/integration.md with screenshots.`

### H-13 — Windows startup, CI and release bundle

**Points:** Protects reproducibility, documentation and deployment

**Priority:** `P2`

**Status:** `in_progress`

**Owner:** `Claude Code`

**Started at:** `2026-10-17 10:40`

**Owns:** `app/testme.ps1`, `app/testme.sh`, `app/manifestme.sh`, `app/deployme.sh`, `app/.python-version`, `app/requirements.txt`, `app/README.md`, `app/data/`, `app/manifest.json`, `.github/workflows/`, `.github/scripts/`, `tests/test_startup.py`, `README.md`, `docs/deployment.md`, `docs/verification.md`, `demo/screenshots/`

**Notes:** Begin after H-12. Provide one-command PowerShell startup, real Python/frontend CI on Windows and Linux, final copied CSV/static assets and Connect manifest. Document replay and provisional semantics and capture desktop/mobile screenshots. Pull-request CI needs no publishing credentials; deployment needs a real logged-out check.

**Definition of done:** python -m pytest -q && npm --prefix app/frontend ci && npm --prefix app/frontend run test -- --run && npm --prefix app/frontend run build exit 0; Windows and Linux CI jobs pass, fresh-clone startup works, copied datasets match approved sources, and the public logged-out deployment serves the page and all three reports. Record actual command output and URL; do not claim public deployment if credentials or access are unavailable.

**Result:** `—`
