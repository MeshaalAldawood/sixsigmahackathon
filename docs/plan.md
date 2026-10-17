# Build Plan — Superagent orchestration (Bikeshare Fleets)

**Truth hierarchy:** [SPEC.md](../SPEC.md) = WHAT; [CONTRACT.md](../CONTRACT.md) = task ownership/status/acceptance; this plan = HOW. Do not edit SPEC or rewrite task scope during implementation. Execute tasks in CONTRACT document order, except independently owned tasks may run concurrently in separate workspaces. Two-hour target is aspirational.

## Frozen decisions and interfaces
- A: One Python FastAPI service returns JSON and serves a built minimal React/Vite page on the same origin; frontend **last**, after a verified backend. No database, polling, uploads, routing, or new statistic.
- B: One shared framework-independent `app/qc.py` uses **exact binomial** tails at `alpha=0.00135`; availability and maintenance modules independently call it; they never import one another. All calculations and decisions are Python-only.
- C: Input is the five SPEC GBFS-shaped columns. B owns `data/`, `app/data_loader.py`, `tests/test_loader.py`, `tests/test_data.py`; A owns `app/qc.py`, `app/requirements.txt`, `tests/test_qc.py`, `docs/statistics.md`. Freeze loader return type and QC function arguments before H-09/H-10; consumers follow B's validated loader interface.
- D: API contract is `GET /api/datasets` (exactly three bundled filenames) and `GET /api/report?dataset=<allowlisted>` (availability AM/PM per-station chart series + dispatch table; maintenance 07:00 network chart + sorted list; warnings, target and synthetic/exploratory labels). UI only renders API data.
- E: H-02, H-03 may run in parallel; after both pass, H-09, H-10 may run in parallel; **H-04 backend gate must pass before H-05 frontend starts**. Document/test alongside each task; H-07 is a final audit.

## People, branches and supervision
- **Person B currently working on H-02** (reported by team; CONTRACT.md on main still shows `todo`, so verify B checks out the task on B's working branch). B must finish datasets, deterministic seed, codebook, validated loader, and both tests before handoff.
- **Person A + one superagent coordinator:** start **H-03 now**, in a separate git worktree/clone/feature branch, without touching B's `owns` paths. No two agents write to the same checkout or the same CONTRACT task section concurrently.
- Before coding each task: run `bash .claude/skills/superagent/scripts/check.sh`; read SPEC + CONTRACT; load the relevant skill; check out ONLY that task using real owner/time. The human approves commits/pushes. A reviewer in a FRESH context verifies actual tests and outputs, then a human approves check-in.
- For each finished branch: run its tests, check PR diff for unowned edits, review, commit the task code + docs + its CONTRACT section together, then merge into main. Rebase/refresh the next worktree **before** starting tasks depending on it; resolve ledger-only merge conflicts without replacing other task results.
- Claude Code: `/superagent` coordinator delegates one task at a time to named `implementer` and read-only `stats-reviewer` subagents; parallelize only disjoint task worktrees. Codex/OpenCode: use their `AGENTS.md` route, one build agent per worktree, and a fresh separate review session (OpenCode free tier: one model call stream per user key).
- Treat team name and Devpost prompt number in SPEC as **unconfirmed metadata**, never invent them. Existing /superagent may ask to fill `FILL IN`; get human input or invoke `/build H-03` for the targeted task rather than allowing a speculative SPEC rewrite.

## Exact statistics and acceptance (SPEC section 4)
- Core: baseline `p_bar=Σd/Σn`; for each daily subgroup `X~Binomial(n,p_bar)`, upper count `u=min{k:P(X>k)≤.00135}`, lower count `l=max{k:P(X<k)≤.00135}`; limits `u/n`, `l/n`; only rule 1 (beyond a limit). First **10 weekdays** establish report baseline; tests may use the SPEC's shorter hand-calculation fixture.
- H-03 known answer: availability `d=[2,4,3,3]`, `n=[24,24,24,24]`, `p_bar=.125`, `u24=9`/`UCL=.375`, `u20=8`/`UCL=.40`, `d10` flagged, `d8` not; maintenance `10/100`, `u=20`, `l=2`, `UCL=.20`, `LCL=.02`, `25/100` flagged. Test equality, `n=0`, `p_bar=0/1`, fewer than 10 baseline days and missing values.
- H-09 availability: distinct AM/PM p-charts per station, empty/full counts, median first-unusable time (07:35,07:40,07:50 → 07:40 on 3 of 10 days), all SPEC section-4 first-match actions and deterministic tie ordering; test chronic `p_bar > .10` vs special-cause signal and missing snapshots.
- H-10 maintenance: one weekday network subgroup at exactly 07:00 using `d=Σdisabled`, `n=Σ(available+disabled)`; sorted inspection list, changing counts, zero opportunities, tie/ordering and planted-event flag. All signals labeled **exploratory** because snapshots can be correlated.
- H-02 datasets: `stable.csv`, `planted_events.csv` (10 stations × 15 weekdays × 48 snapshots); `edge_case.csv` (2 stations × 15 weekdays, missing snapshots); baseline unchanged; day-12 PM stadium and day-13 broken-bike deterioration. Record stable false alarms in demo.

## Orchestration schedule and non-negotiable gates
| Sequence / target | CONTRACT task | Agent owner | Exit evidence |
|---|---|---|---|
| Already underway, parallel | **H-02** | Person B | CSVs + loader + tests + `data/README.md`; B confirms actual branch/check-in |
| Now, parallel with H-02 (~25 min) | **H-03** | Person A / implementer → independent reviewer | Exact numeric test report + degenerate PASS; frozen QC interface |
| After H-02/H-03 (~30 min) | **H-09 / H-10** | A / B, independent worktrees | Availability/maintenance tests, per-module docs, read-only review |
| Once both modules merged (~20 min) | **H-04** | Integrator / superagent | **HARD BACKEND GATE**: full pytest, all three datasets, whitelist/rejections, both report endpoints, root and app startup; stop on FAIL |
| ONLY after H-04 (~25 min) | **H-05** | A / frontend implementer | Vite build, same-origin React + API, AM/PM station selection, warning states, dataset demo documentation |
| Remaining time (~15+ min) | **H-06 + H-07 + H-08** | Integrator + available teammate | Public Connect URL tested logged out, fresh-clone docs/test audit, verified submission; do not falsely check in external steps |

## Agent handoff and stop conditions
- Every subagent receives exactly: `TASK ID`, `MISSION`, `OWNS`, `DEPENDENCIES`, `READ FIRST` (SPEC §4, contract task, this plan, relevant skill), `VERIFY` (command + known/degenerate case), and `REPORT` (changed files, exact output, blocked items). Do not run all ten tasks in one coding prompt.
- **Build → run tests → fresh independent review → human diff approval → check in + merge → refresh other worktree**. Coordinator never marks a task done without check output. If the contract checkout or shared interface would conflict with B, pause and ask.
- If H-02 is delayed, H-03 continues independently. If backend gate fails, **no frontend**; diagnose backend first. If deployment credentials are missing, record blocked, prepare docs locally; do not claim a live submission.

## Three risks and response
1. Shared CONTRACT edits across branches → disjoint task sections + review/rebase before merge; no simultaneous editing of one checkout.
2. Serial correlation and small n → exact binomial arithmetic but exploratory signals; no calibrated real-world false-alarm claims.
3. Two-hour deadline / Connect packaging → one service, backend-first gates, copy CSVs and static assets into `app/`, reserve deployment time; cut styling, never numerical verification.
