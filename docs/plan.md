# Build Plan — Finalized Bikeshare Fleets SPEC

**Authority:** [SPEC.md](../SPEC.md) is the product contract, [CONTRACT.md](../CONTRACT.md) is the executable ledger. Follow the task list order in CONTRACT.md (H-09/H-10 deliberately precede H-04). This plan records architecture and decisions, not task check-ins.

## Decision record
| ID | Choice | Why / rejected alternative |
|---|---|---|
| A | One FastAPI app serves JSON + built React/Vite | One public Posit Connect URL; reject separate frontend deployment |
| B | One framework-free `app/qc.py` with **exact binomial limits** | Small station-window n makes normal 3-sigma approximation unsuitable |
| C | Independent `availability.py` / `maintenance.py` | Separate logic and tests; share validated input + QC function |
| D | Bundled synthetic GBFS-shaped CSVs, no database/feed polling | Repeatable demo with minimal inputs |
| E | `GET /api/datasets` and `GET /api/report?dataset=<allowlisted name>` | Frontend renders JSON and never re-derives statistics |
| F | SPEC's first-match dispatch rules + deterministic ties | Explainable, not an optimizer or route planner |

**Decision criteria used:** 30% speed, 25% correct/testable QC, 20% parallel ownership, 10% deployment risk, 15% SPEC compliance. Earlier indicative scores favored single-deployment FastAPI + React. Do not treat those scores as measured performance.

## Data and fixed definitions
- Five CSV columns: `timestamp,station_id,num_bikes_available,num_bikes_disabled,num_docks_available`. Parse local `YYYY-MM-DDTHH:MM`. Validate nonnegative integer counts and unique station/timestamp with clear row number.
- Weekdays only; AM 07:00–08:55 and PM 16:00–17:55 at five-minute cadence; drop off-window observations, but allow missing snapshots and adjust n.
- `stable.csv`, `planted_events.csv`: 10 stations x 15 weekdays x 48 snapshots. First 10 weekdays common baseline; event day 12 full PM station; broken share doubles from day 13. `edge_case.csv`: 2 stations x 15 weekdays and missing observations. Include seed/codebook.
- Availability: per-station, separate AM and PM p-charts; d=count of empty-or-full snapshots, n=logged snapshots. Show empty/full counts individually, baseline median first-empty/full onset time and affected-day frequency, latest-day prioritized station action.
- Maintenance: daily 07:00 network-level p-chart, d=total disabled bikes, n=total docked bikes. Latest 07:00 station list sorted disabled count desc then station ID. Synthetic/exploratory warning always visible.

## Mathematical specification and tests
- **Exact binomial p-chart** with alpha `0.00135` each tail. `p_bar=sum(d_baseline)/sum(n_baseline)`; find smallest u with `P(X>u)<=alpha`; largest l with `P(X<l)<=alpha`. UCL=u/n; LCL=l/n; high when d>u, low when d<l. Fixed baseline: first 10 weekdays, not contaminated by events. Western Electric rule 1 only.
- Availability hand check (QC calculator fixture, independent of UI 10-day baseline gate): d=[2,4,3,3], n=[24,24,24,24] -> p_bar=.125; n24 u=9/UCL=.375; n20 u=8/UCL=.40; d10 flags, d8 does not. Median 07:35, 07:40, 07:50 -> 07:40 on 3 of 10 baseline days.
- Maintenance: d=10/n=100 baseline -> p_bar=.10; u=20/UCL=.20; l=2/LCL=.02; d25 flags high, d20 does not, d<=1 flags low.
- Suppress limits with explanation if fewer than 10 baseline days, zero-opportunity subgroup, or p_bar exactly 0 or 1. Repeat snapshots are correlated: signals are **exploratory**, not calibrated false-alarm claims. Count stable-dataset flags in demo. Target unusable proportion .10 is an SLA line, NOT a control limit.

## Minimal report contract
- `GET /api/datasets` lists exactly `stable.csv`, `planted_events.csv`, `edge_case.csv`; reject any other path/name.
- `GET /api/report` returns `{dataset, availability:{AM:{stations:[...],selected_station_chart:...},PM:{...}},maintenance:{chart:{...},stations:[...]},meta:{synthetic:true,exploratory:true}}`; selecting another station can be handled by including a chart series for each station in the availability payload.
- Chart points: date, n, d, p, p_bar, LCL, UCL, flagged_high/low, plus status/warnings. When n varies, control limit is stepped; no browser statistical calculations.
- Availability station rows: station ID, latest unusable share, empty/full snapshot counts, p_bar, current UCL/signal, median first-unusable time with affected-day frequency, exactly the SPEC section-4 action and deterministic priority. Maintenance rows: station ID, disabled-bikes count at 07:00 and inspect/collect action.

## Backend first — target 120 minutes, deployment contingent on access
| Elapsed | Tasks | Output / mandatory gate |
|---|---|---|
| 0–10 min | H-01 | SPEC reviewed, interfaces frozen; unresolved name/prompt number tracked |
| 10–35 min | H-02 + H-03 parallel | 3 CSVs/loader/codebook; exact binomial QC function + numerical tests + docs |
| 35–65 min | H-09 + H-10 parallel | Availability/maintenance modules with independent tests and docs |
| 65–80 min | H-04 | Thin FastAPI, full Python tests and live endpoint smoke checks — **HARD BACKEND GATE** |
| 80–105 min | H-05 | React page built LAST, served by FastAPI; 3 dataset demos written |
| 105–120 min | H-06, H-07, H-08 | Deployment + docs audit + submission checks, parallel where possible |

**Owners:** Developer A handles QC + availability; Developer B handles CSV/loader + maintenance; API integrator handles glue/deploy. Specific owned paths and check-in permissions live in CONTRACT.md. Each task writes its own test and documentation alongside its code; H-07 only audits.

## Risks
1. Correlated snapshots invalidate nominal exact-binomial alarm rate: label exploratory and show stable-case false flags, do not claim prediction/causality.
2. Day/window grouping, median-onset timing and precedence introduce many edge cases: assert exact numeric/ordered outcomes before any frontend work.
3. Connect build and credentials could exceed 120 minutes: deploy single bundled FastAPI service, preserve four-script contract, do not claim a URL without checking it.
