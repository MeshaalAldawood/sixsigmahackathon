# Implementation Plan — Bike-share Two-Hour MVP

**Source of truth:** [SPEC.md](../SPEC.md) defines product behavior. [CONTRACT.yaml](../CONTRACT.yaml) is the **only** task/status ledger. This is the architecture/decision record; do not check tasks in here.

## Architecture decisions
| ID | Chosen | Alternatives rejected | Reason |
|---|---|---|---|
| A | FastAPI + tiny React/Vite page, one deployed service | Plain HTML; two deployments; Shiny | Meets SPEC; one public URL |
| B | One framework-free tested Python p-chart function | Duplicated math | Same valid calculation for both analyses |
| C | Independent availability and maintenance modules | One monolithic module | Separately testable and delegable |
| D | Two bundled CSVs, identical schema | Database; live API | Reproducible synthetic demo |
| E | One combined JSON report endpoint | Multiple separate report services | No frontend computation or integration overhead |
| F | Fixed station action/priority rules | Weighted optimizer / vehicle routing | Transparent and within problem scope |

**Selection criteria:** speed 30%, statistical testability 25%, independent work 20%, deployment risk 10%, SPEC fit 15%. Subjective weighted scores: chosen 92/100; plain HTML 88; two deployments 72; Shiny 70. Not empirical measurements.

## System flow and contracts
`data/*.csv` -> `app/data_loader.py` (validate) -> **two independent modules** `app/availability.py` and `app/maintenance.py` -> shared `app/qc.py` (p-chart calculation called by each) -> `app/app.py` (FastAPI JSON) -> React page **only after backend verification**.

- Input: one row per station/day; columns `timestamp, station_id, total_docks, working_bikes, broken_bikes`. Derived `empty_docks = total_docks - working_bikes - broken_bikes`; fail on impossible records.
- Output: `GET /api/datasets` (whitelisted CSV names); `GET /api/report?dataset=stable.csv` returns `{dataset, availability:{chart,stations}, maintenance:{chart,stations}}`.
- Each chart returns `status` (`ok` or `insufficient_basis`), `p_bar`, daily points (`date, failures, opportunities, p, LCL, UCL, flagged`), and optional warning. Never invent limits if assumptions fail.
- Station lists: latest snapshot; availability actionable first with deterministic station-ID ties, maintenance sorted broken count descending then ID. UI simply renders backend output.
- Bundling: keep source data in root `data/`; copy approved CSVs into `app/data/` for deployment. Compile React into `app/static/` and serve through FastAPI. Keep the API functional when static assets are absent.

## Statistical formula, assumptions and tests
- First 20 checkpoints are the fixed baseline. `p_bar = sum(failures_baseline) / sum(opportunities_baseline)`; daily `p=f/n`.
- `LCL=max(0, p_bar-3*sqrt(p_bar*(1-p_bar)/n))`; `UCL=min(1, p_bar+3*sqrt(p_bar*(1-p_bar)/n))`.
- Known answer: 10/100 => `p_bar=.10`; `sqrt(.1*.9/100)=.03`; LCL=.01, UCL=.19; 25/100=.25 => high flag.
- Tests must reject invalid counts, zero opportunities, invalid baseline/approximation, missing fields and insufficient checkpoints; demonstrate a planted deterioration.
- These are exploratory p-charts: repeated station/bike observations can be correlated; do not claim calibrated alarms. Document assumptions in `docs/statistics.md`.

## Contract execution — BACKEND FIRST
| Window | Task IDs | Work and gate |
|---|---|---|
| 0–10 min | H-01 | Check SPEC, architecture, known answer and team/prompt TBDs |
| 10–35 min | H-02, H-03 | In parallel: data/loader + codebook (B); QC function/tests + stats docs (A) |
| 35–65 min | H-04 | A: availability; B: maintenance; integrator: FastAPI; tests and docs alongside each |
| 65–75 min | H-04 gate | **All backend tests pass, both datasets load, API returns both reports. No frontend before this.** |
| 75–105 min | H-05 | React only now; build and integrate one local URL; demo walkthrough written |
| 105–120 min | H-06, H-07, H-08 | Deploy, README/QA, submission checks; some parallel, external steps may take longer |

**Work ownership:** A owns QC, availability and React code; B owns datasets/loader and maintenance; integration owner owns API/deployment. Paths and check-ins are governed by `CONTRACT.yaml`, not this table. Every coding task writes its tests and documentation at the same time.

## Biggest risks
1. **P-chart assumption failure:** validate simulated baseline, fail clearly and show descriptive station rankings rather than false statistical confidence.
2. **Time and integration:** finish/tests-pass backend before React; keep one page, one JSON response, no extra features.
3. **Posit Connect deployment:** verify static assets and bundled CSVs in `app/`; publish early when possible, log actual public URL, never commit credentials.
