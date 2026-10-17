# One-shot Superagent prompt — simulated-live replay and release fixes

**Base:** `feature/simulated-live-replay-release-fixes` (forked from the built `overnight/complete-build`). Read `SPEC.md`, `CONTRACT.md`, `docs/plan.md` and this file before implementation. This document is ready for a Claude Code coordinator with Codex as an optional isolated worker.

---

## BEGIN EXECUTION PROMPT

You are our sole Claude Code Superagent coordinator. Your objective is to **FINISH** the existing Bikeshare Dispatch hackathon application: add an honest, beautiful synthetic-live replay using the EXISTING three CSVs, repair the final-release defects, prove statistical correctness, and make the built app fully demo/deployment-ready.

**Start in repo MeshaalAldawood/sixsigmahackathon branch `feature/simulated-live-replay-release-fixes` (or fetch it to a new clean worktree).** Do NOT start over from main; the finished code is already in this branch. Preserve every existing 152-test result and the completed H-01–H-10 ledger history. No fourth dataset, no real feed connector, no database, no new statistic, no map or route optimizer.

**Work autonomously** through task H-11, then H-12, then H-13, as specified in `CONTRACT.md`. Read `SPEC.md` sections 2–9; follow the EXACT new replay scope. Follow `.claude/skills/superagent/SKILL.md` and stats-first-steering. You may install documented dependencies, run local servers/tests, create non-destructive branches/worktrees, edit files OWNED by the active task, and make local commits after recording the exact diff and actual passing tests. Respect any host consent prompt; **do not push, merge PRs, publish to Connect or submit to Devpost unless I separately authorize the concrete external action**. Don't interrupt to ask routine design questions. If a genuine external obstacle appears, finish independent work and report the smallest step needed.

**Agent orchestration:** use Claude Code as ONE coordinator, Codex CLI as implementation worker for H-11 in its own worktree if available, and fresh read-only Claude reviewer for statistical and API checks. H-12 can use a separately isolated frontend implementer after H-11 passes; H-13 is final auditor/release integrator. Never run two independent superagents editing one checkout. Keep scoped owners/statuses/results up to date without overwriting historic tasks or Person B's code. Never weaken tests to green.

### H-11 — causal backend replay + existing correctness fix

1. Keep unchanged `GET /api/datasets` and `GET /api/report?dataset=stable.csv`. Add `GET /api/replay/timeline?dataset=...` returning actual sorted 5-minute timestamp frames for **days 11–15 only** (first 10 weekdays are completed historical baseline), plus useful baseline/replay metadata. No observations from later frames in this response.
2. Add optional `as_of=YYYY-MM-DDTHH:MM` to existing report GET. Accept only timestamps in that dataset's replay timeline and only the 3 whitelisted dataset names. No `as_of` means the existing 15-day historical report stays backward-compatible. For `as_of`, filter ALL domain input observations to `timestamp <= as_of`; report observed station status at that clock time and mark nonreporting stations STALE/UNKNOWN, never quietly reuse old data as current.
3. Freeze the **complete first-ten-weekday baseline**, regardless of playback position. Only observations until synthetic clock can influence latest-day conditions, actions, current counts, maintenance and plotted history. Do not show future PM data while in the morning; don't expose day12 anomaly during day11 replay. Preserve exact-binomial `app/qc.py` unchanged.
4. Completed rush-window points use existing p-chart rules. Any active rush window with fewer than its full expected observation slots must be marked **PROVISIONAL** with observed d/n. Do not label provisional points or instantaneous bike shortages as final statistical special causes. Treat missing snapshots as missing; don't fabricate them. Provide instantaneous operational alerts separately from historical statistical conclusions.
5. Fix `app/availability.py` onset text: affected days / **10 fixed baseline weekdays**, not only baseline days observed for the station; disclose missing baseline station-day coverage. Keep median based only on days with actual applicable onset. Ensure the displayed onset/deadline is action-relevant.
6. Add targeted tests for every as-of boundary (07:00, 08:55, 09:00, 16:00, 17:55), weekend transitions, invalid datasets and timestamps, baseline invariance, no future leakage, missing E02 snapshots, unchanged historical responses, completed vs provisional alerts, stale current data and onset frequency. Run H-11 DoD exactly; provide test output and independent fresh-context review.

### H-12 — polished replay UI, precise charts and accessibility

1. Build a professional, high-contrast **"Bikeshare Shift Desk"** dashboard with clean hierarchy, ample whitespace and restrained accents. Prioritize at-a-glance current problems and action table, not decorative stock images.
2. Persistent mode selector: **Historical** and **SIMULATED LIVE (SYNTHETIC DATA)**. In replay, expose Play/Pause, Next 5-minute frame, Reset, speed (1x/5x/20x), simulated date/clock, and event jumps (Day 12 PM S08 stadium anomaly; Day 13 AM broken-bike surge). Initial replay clock is Day 11 at 07:00 with the ten-day baseline already established. Skip all gaps by stepping only through actual dataset timestamps. No backend polling, SSE/WebSockets, timers claiming real wall-clock updates, or browser-side math; timers for replay advancement are fine.
3. Switch datasets without leaking/sticking previous dataset's results. Each replay request uses the backend `as_of` endpoint and the current clock; show loading, stale and error states. Protect against overlapping responses from different timestamps (abort or latest-request-wins).
4. Show current bike status per station (available bikes, disabled bikes, empty docks, sample freshness), visually distinct from historical/exploratory chart flags. Keep availability AM/PM, station charts, dispatch priorities, and maintenance tab. In-progress subgroup visibly says `PROVISIONAL — rush window still running`; no future chart points or end-of-day outcomes.
5. Fix `app/frontend/src/PChart.jsx`: join adjacent UCL/LCL horizontal segments with **vertical steps** when n changes, but leave gaps for null limits; do NOT draw `p=null` as 0% or connect a line across a missing-data gap. Ensure chart labels and tooltips accurately show counts, limits, and provisional status. Current CSS/UI is functional but minimalist: improve card system, navigation, typography, mobile layout, and status treatments without obscuring data.
6. Fix dispatch table's typical first-onset display: show both empty/full onset or only the onset matching recommended direction, not whichever condition happens on more baseline days. Make selected station, row controls, dataset/window toggles and playback keyboard-accessible.
7. Test historical and replay experiences with all 3 datasets. Capture **actual** desktop 1280x800 and mobile 390x844 browser screenshots for initial, S08 event, maintenance surge and E01 no-limits cases. Check no sideways page overflow at 390px, proper focus, labels, contrast, chart legend and visible synthetic banner. Run H-12 DoD and get independent reviewer assessment.

### H-13 — reproducibility, real GBFS sourcing and release hardening

1. Preserve original data files and synthetic labeling. Enhance `data/README.md` with concrete **real-life acquisition** steps: discover `station_status.json` via operator GBFS `gbfs.json`; poll/log approximately every five minutes; persist station ID, observed timestamp and bike/dock counts; distinguish feed's `last_reported` from collector poll time; convert UTC/local time carefully; handle update delay, absent/closed stations, missing polls, and retention of at least ten known-normal weekdays. This is DOCUMENTATION, not a feed integration.
2. Fix native Windows Git Bash startup `app/testme.sh` (`.venv/Scripts/python.exe` fallback) without breaking Unix/macOS `.venv/bin/python` and without hardcoding machine paths.
3. Add a GitHub Actions **TEST** job independent of Posit credentials: install Python 3.12 pinned requirements, run all pytest, npm ci/build, and verify bundled data and build output. Keep deploy job credential-gated, no tokens in logs, and don't claim CI PASS unless the run actually succeeded.
4. Rebuild `app/static/`, copy the 3 CSVs to `app/data/`, regenerate `app/manifest.json` after changes. Verify manifest checksum/entrypoint and that the 18-ish deploy bundle alone serves page and API under a prefixed URL. Don't claim a fixed file count if it changes. Run fresh clone on supported runtime; execute all existing and new tests.
5. Update README, demo/README.md, docs/integration.md, docs/verification.md and docs/deployment.md with replay instructions, three scenarios, actual tests/screenshots and honest blocker status. **No publicly hosted app** until Posit URL is verified with logged-out HTTP 200 for page + each dataset. **No submission** until official Devpost prompt number and an actual submission confirmation exist.

### Non-negotiable acceptance gates

- **Statistical:** all SPEC section-4 exact-binomial known answers still pass, including 12/96 and 10/100 fixtures, changing n, equality, zero/one baseline, day12 S08 PM signal, day13–15 maintenance spike. No new unapproved statistical method.
- **Temporal correctness:** 0 observations later than replay as_of in any report; first-ten-day baseline remains constant; current status is time-accurate/stale labeled; partial window never masquerades as a final SPC alarm. Historical mode remains backward compatible.
- **UI:** every control works; responsive screenshots show readable chart, current state, decision hierarchy and obvious SYNTHETIC LIVE label; no fake streaming claims; no null-as-zero points.
- **Reproducibility:** Python tests, npm build, API smoke checks, dedicated CI green if available, deployment bundle checked, no secrets.
- **Rubric:** 25 working tool + 25 valid QC + 5 prompt fit + 5 dispatcher use case + 5 minimal inputs + 10 dataset demo + 10 docs + 5 datasets + 5 codebook + 5 public reproducibility = 100 **possible** points. Present actual evidence per category; NEVER promise judges award 100/100.

### Handoff

Continue implementation and bounded bug-fix loops until all local gates pass or a genuine external blocker prevents progress. Your final response must list exact commits, changed files, passing/failing test commands and counts, screenshots you actually captured, APIs/behavior demonstrated, real-life GBFS acquisition documentation, pending external deployment/Devpost steps, and a concise honest rubric-readiness scorecard. Do **not** finish by returning only another plan.

## END EXECUTION PROMPT
