# Build Plan — Superagent orchestration (Bikeshare Fleets)

**Truth hierarchy:** [SPEC.md](../SPEC.md) = WHAT; [CONTRACT.md](../CONTRACT.md) = task ownership/status/acceptance; this plan = HOW. Do not edit SPEC or rewrite task scope during implementation. Execute tasks in CONTRACT document order, except independently owned tasks may run concurrently in separate workspaces. Two-hour target is aspirational.

## Frozen decisions and interfaces
- A: One Python FastAPI service returns JSON and serves a built minimal React/Vite page on the same origin; frontend **last**, after a verified backend. No database, polling, uploads, routing, or new statistic.
- B: One shared framework-independent `app/qc.py` uses **exact binomial** tails at `alpha=0.00135`; availability and maintenance modules independently call it; they never import one another. All calculations and decisions are Python-only.
- C: Input is the five SPEC GBFS-shaped columns. B owns `data/`, `app/data_loader.py`, `tests/test_loader.py`, `tests/test_data.py`; A owns `app/qc.py`, `app/requirements.txt`, `tests/test_qc.py`, `docs/statistics.md`. Freeze loader return type and QC function arguments before H-09/H-10; consumers follow B's validated loader interface.
- D: API contract is `GET /api/datasets` (exactly three bundled filenames) and `GET /api/report?dataset=<allowlisted>` (availability AM/PM per-station chart series + dispatch table; maintenance 07:00 network chart + sorted list; warnings, target and synthetic/exploratory labels). UI only renders API data.
- E: H-02, H-03 may run in parallel; after both pass, H-09, H-10 may run in parallel; **H-04 backend gate must pass before H-05 frontend starts**. Document/test alongside each task; H-07 is a final audit.

## Dual-agent operating model (Claude Code + Codex)
- **One coordinator:** Person A runs Claude Code as the sole **Superagent/orchestrator** from a clean coordinator checkout of main. It reads SPEC, CONTRACT and this plan, plans/delegates, monitors gates, and assigns read-only reviews. **Do not run two autonomous /superagent coordinators**; that duplicates checkouts and contract edits.
- **Independent worker:** Person A runs **Codex** in a separate `git worktree` and task branch for implementation. Codex reads AGENTS.md and the contract task, uses the routed skills, writes code/tests/docs ONLY in that task's `Owns` paths, and reports actual test output. Claude Code remains read-only for those worker-owned code files while Codex is implementing them.
- **Person B currently owns H-02** (user-reported, not yet reflected by main's `todo` status). B continues on an independent branch/checkout; do NOT restart or claim H-02. B checks it out there with actual owner/time, then merges task code, tests, data codebook and contract status when verified.
- **Now:** Codex executes **H-03** while B executes H-02. Claude Code plans/reviews H-03 as its read-only `stats-reviewer` in a **fresh context after Codex finishes**. While Codex codes, Claude Code can inspect documentation, task boundaries and planned acceptance but must not start H-09/H-10 (they depend on H-02 + H-03).
- **Next:** after H-02 and H-03 merge and freeze the loader/QC interfaces, **Codex executes H-09 availability** in one worktree; **B (using Claude Code if preferred) executes H-10 maintenance** in another. Person A's coordinator performs integration planning/reviews; it must never alter their task-owned paths.
- **Then:** Claude Code orchestrates **H-04 API/backend gate**, delegating to an implementer in an isolated worktree. Codex reviews API tests/read-only in fresh context. AFTER the backend gate passes, **Codex builds H-05 React**, while Claude Code can read-only prepare the H-06 deployment checklist; then integration, deployment, documentation audit and submission follow.
- **Git handoff:** branch per task (`task/h03-qc`, `task/h09-availability`, B's separately named branch); worktrees must have separate directories. Build -> tests -> independent fresh review -> human approves diff/commit -> PR/merge -> other worktrees refresh from main before dependent tasks. Resolve shared CONTRACT.md edits section-by-section, retaining the other person's status/result; never blindly overwrite the file.
- **Superagent control:** run `bash .claude/skills/superagent/scripts/check.sh` at each transition. An unfinished team-name or Devpost prompt-number placeholder requires human clarification eventually, **not** permission to modify the frozen statistical scope. No automatic commits, merges, pushes, frontend starts, or claims of PASS without user approval and actual output.

## Exact statistics and acceptance (SPEC section 4)
- Core: baseline `p_bar=Σd/Σn`; for each daily subgroup `X~Binomial(n,p_bar)`, upper count `u=min{k:P(X>k)≤.00135}`, lower count `l=max{k:P(X<k)≤.00135}`; limits `u/n`, `l/n`; only rule 1 (beyond a limit). First **10 weekdays** establish report baseline; tests may use the SPEC's shorter hand-calculation fixture.
- H-03 known answer: availability `d=[2,4,3,3]`, `n=[24,24,24,24]`, `p_bar=.125`, `u24=9`/`UCL=.375`, `u20=8`/`UCL=.40`, `d10` flagged, `d8` not; maintenance `10/100`, `u=20`, `l=2`, `UCL=.20`, `LCL=.02`, `25/100` flagged. Test equality, `n=0`, `p_bar=0/1`, fewer than 10 baseline days and missing values.
- H-09 availability: distinct AM/PM p-charts per station, empty/full counts, median first-unusable time (07:35,07:40,07:50 → 07:40 on 3 of 10 days), all SPEC section-4 first-match actions and deterministic tie ordering; test chronic `p_bar > .10` vs special-cause signal and missing snapshots.
- H-10 maintenance: one weekday network subgroup at exactly 07:00 using `d=Σdisabled`, `n=Σ(available+disabled)`; sorted inspection list, changing counts, zero opportunities, tie/ordering and planted-event flag. All signals labeled **exploratory** because snapshots can be correlated.
- H-02 datasets: `stable.csv`, `planted_events.csv` (10 stations × 15 weekdays × 48 snapshots); `edge_case.csv` (2 stations × 15 weekdays, missing snapshots); baseline unchanged; day-12 PM stadium and day-13 broken-bike deterioration. Record stable false alarms in demo.

## Orchestration schedule and non-negotiable gates
| Sequence / target | CONTRACT task | Agent owner | Exit evidence |
|---|---|---|---|
| Already underway, parallel | **H-02** | Person B in separate checkout | CSVs + loader + tests + `data/README.md`; B confirms actual branch/check-in |
| Now, parallel with H-02 (~25 min) | **H-03** | Codex implementer → Claude reviewer | Exact numeric test report + degenerate PASS; frozen QC interface |
| After H-02/H-03 (~30 min) | **H-09 / H-10** | Codex (A) / B (Claude optional), separate worktrees | Availability/maintenance tests, per-module docs, read-only review |
| Once both modules merged (~20 min) | **H-04** | Claude coordinator → isolated implementer, Codex review | **HARD BACKEND GATE**: full pytest, all three datasets, whitelist/rejections, both report endpoints, root and app startup; stop on FAIL |
| ONLY after H-04 (~25 min) | **H-05** | Codex implementation / Claude read-only QA | Vite build, same-origin React + API, AM/PM station selection, warning states, dataset demo documentation |
| Remaining time (~15+ min) | **H-06 + H-07 + H-08** | Integrator + available teammate | Public Connect URL tested logged out, fresh-clone docs/test audit, verified submission; do not falsely check in external steps |

## Agent handoff and stop conditions
- Every subagent receives exactly: `TASK ID`, `MISSION`, `OWNS`, `DEPENDENCIES`, `READ FIRST` (SPEC §4, contract task, this plan, relevant skill), `VERIFY` (command + known/degenerate case), and `REPORT` (changed files, exact output, blocked items). Do not run all ten tasks in one coding prompt.
- **Build → run tests → fresh independent review (different agent) → human diff approval → check in + merge → refresh other worktree**. Coordinator never marks a task done without check output. If the contract checkout or shared interface would conflict with B, pause and ask.
- If H-02 is delayed, H-03 continues independently. If backend gate fails, **no frontend**; diagnose backend first. If deployment credentials are missing, record blocked, prepare docs locally; do not claim a live submission.

## Three risks and response
1. Shared CONTRACT edits across branches → disjoint task sections + review/rebase before merge; no simultaneous editing of one checkout.
2. Serial correlation and small n → exact binomial arithmetic but exploratory signals; no calibrated real-world false-alarm claims.
3. Two-hour deadline / Connect packaging → one service, backend-first gates, copy CSVs and static assets into `app/`, reserve deployment time; cut styling, never numerical verification.
