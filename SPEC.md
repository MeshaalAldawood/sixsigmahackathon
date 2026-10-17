# SPEC: Six Sigma Hackathon team project

What your tool IS. Your agent reads this before every task. Where the code and this file
disagree, the code is the bug: change this file first, then the code.

Most of this page is already decided by the event and the [rubric](docs/criteria.md).
**Only the `FILL IN` lines change, and you do not have to write them by hand:** describe your app and ask your agent to update them. They depend on the prompt your team picks at kickoff
(prompts are secret until then, see [`docs/prompts.md`](docs/prompts.md)) and on your team.
The examples after each `FILL IN` show the shape of an answer. They are not hints about the prompts.

Implement **only** what is written here. All data is synthetic and labelled as such.

## 1. Team and prompt
- **Team name:** Team Six
- **Track:** On-campus (24 hours). Submissions due Sat Oct 17, 1 PM ET; showcase 2-3 PM.
- **Prompt we chose:** Urban Systems: "Bikeshare Fleets" (prompt number: copy it from Devpost). A municipal bikeshare system has a "docks full / docks empty" crisis at rush hour and maintenance vans are dispatched blindly; design a tool to track dock availability, when and where stations are unusable, and support the network's performance.
- **Our public repo:** github.com/MeshaalAldawood/sixsigmahackathon

## 2. User and use case (rubric: scope 5, user and use case 5)
- **User:** the bikeshare operations dispatcher who assigns the maintenance vans for the weekday morning and evening rush.
- **Decision A, availability (each evening, for the next day's two rushes):** which stations get a van in the morning rush (07:00-09:00) and in the evening rush (16:00-18:00), whether the van drops or pulls bikes, and by what time; and which stations vans cannot fix because they are unusable every day (those go to planning for more docks or a standing rebalancing slot).
- **Decision B, maintenance (each morning, before the 07:00 rush):** whether the share of broken bikes in the network has risen beyond normal, and which stations to inspect and collect broken bikes from first.
- **Why this matches the prompt:** it turns the dock-availability feed into a record of when and where stations are unusable, and replaces blind van dispatch with a ranked, timed list.
- **Boundary:** the tool ranks stations and says what a van should do there. It does not assign vans, plan routes or schedule crews.

## 3. Inputs (rubric: minimal inputs 5)
Only what this user can actually measure or already knows. Fewer is better; every input a user
cannot measure costs points.

| Input | Type and units | Where the user gets it |
|---|---|---|
| `station_status.csv`, one row per station per snapshot: `timestamp`, `station_id`, `num_bikes_available`, `num_bikes_disabled`, `num_docks_available` | timestamp: local time, ISO 8601 (`YYYY-MM-DDTHH:MM`); station_id: text; the three counts: non-negative integers (bikes, bikes, docks) | the system's public GBFS `station_status` feed, logged every 5 minutes; the column names are GBFS's own. Every bikeshare system already publishes it |
| Rush windows | two clock-time ranges; fixed at 07:00-09:00 (AM) and 16:00-18:00 (PM), weekdays | the operator's own definition of the peaks |
| Baseline days | integer; default the first 10 weekdays in the file | a period the dispatcher considers normal operation |
| Target unusable share | a proportion; default 0.10 (a station unusable at most 10% of a rush window) | the city's service-level agreement with the operator |

Validation: reject the file, with a message naming the row, on missing values, negative counts,
non-integer counts, or a duplicate `station_id` + `timestamp` pair. Snapshots outside the two rush
windows and weekend days are ignored. A missing snapshot is allowed; it lowers n for that window.
Snapshots record state only: they do not measure rider demand, trips, or repair times.

## 4. The statistics, and why (rubric: valid QC analysis 25)
Say the method in words before any code exists. Load the `stats-first-steering` skill first.
- **Method:** **one statistic, a p-chart with exact binomial limits**, computed by one tested
  function in `app/qc.py` and reused for both decisions.
  - *The function:* given baseline counts (d, n) and new counts (d, n), p-bar = sum(baseline d) /
    sum(baseline n). For each subgroup of size n, with X ~ Binomial(n, p-bar) and alpha = 0.00135
    (the tail area beyond 3 sigma on a normal curve):
    upper count u = the smallest integer with P(X > u) <= alpha, so the subgroup flags high when d > u;
    lower count l = the largest integer with P(X < l) <= alpha, so the subgroup flags low when d < l.
    UCL = u / n and LCL = l / n. Exact limits are used because the usual
    p-bar +/- 3 sqrt(p-bar(1 - p-bar)/n) formula needs n * p-bar >= 5, and one station's rush window
    (n = 24 snapshots, p-bar around 0.05-0.15) gives n * p-bar of only 1-4.
    Run rule: Western Electric rule 1 only (a point beyond a limit).
  - *Availability (Decision A):* a snapshot is *unusable* when `num_bikes_available == 0` (empty:
    nobody can start a trip) or `num_docks_available == 0` (full: nobody can end one). One subgroup =
    one station, one weekday, one rush window; n = snapshots logged in that window (24 at 5-minute
    spacing, fewer if some are missing); d = unusable snapshots. **The AM and PM windows are charted
    separately**, because the same station often empties in the morning and fills in the evening.
    So each station has two p-charts, one point per weekday on each.
  - *Maintenance (Decision B):* one network-level p-chart, one point per weekday, from the 07:00
    snapshot. n = all docked bikes in the network (`num_bikes_available + num_bikes_disabled`, summed
    over stations); d = broken bikes (`num_bikes_disabled`, summed).
  - *Plain counts next to the charts (descriptive, not modelled):* for each station and window, the
    empty and full snapshot counts separately, and the **typical first-unusable time**: the median
    clock time of the first empty (or full) snapshot over the baseline days on which it happened,
    reported with how many days that was ("usually empty by 07:40, on 3 of 10 days").
- **Actions in the dispatch table (latest day, per station and window, first match wins):**
  1. the station was full at a snapshot where `num_bikes_disabled > 0`: "collect broken bikes first"
     (broken bikes are taking docks);
  2. today's point is above UCL: "investigate: special cause" (an event or a broken dock), plus the
     van direction from rule 4;
  3. today's point is in control but p-bar > the 0.10 target: "capacity review: unusable every day";
  4. empty snapshots > full snapshots: "van: drop bikes before HH:MM"; full > empty: "van: pull bikes
     before HH:MM", where HH:MM is the typical first-unusable time;
  5. otherwise "OK".
  Actionable rows first; ties broken by `station_id` so the order is deterministic. The maintenance
  list shows stations with `num_bikes_disabled > 0` at 07:00, most broken bikes first, then `station_id`;
  the action is "inspect and collect broken bikes". No repair times.
- **Why it fits the use case:** the p-chart separates a special cause (one bad day above the limits: send a van and investigate) from a common cause (a station in control but above the 0.10 target every day: vans will not fix it, the station needs more docks or a standing rebalancing slot), and the first-unusable time tells the van when it has to arrive, not only where.
- **Assumptions and how the tool checks them:**
  - Snapshots within a window are treated as independent trials, which they are not (an empty
    station at 07:35 is likely still empty at 07:40), so real false alarms are more frequent than
    alpha. The page labels every signal **exploratory**, and the demo reports how many points flag
    on the stable dataset.
  - Limits come from the baseline days only, never from days that include the event we want to detect.
  - Control limits are not targets: the 0.10 target comes from the service-level agreement, not from the data.
  - Fewer than 10 baseline days, a subgroup with n = 0, or p-bar of exactly 0 or 1: no limits are
    drawn and the page says "insufficient basis for control limits", never an invented alert.
- **Known-answer check:** worked by hand, must be reproduced exactly. Cross-check the binomial tails
  in R with `1 - pbinom(k, n, p)` or in Python with `scipy.stats.binom.sf(k, n, p)`.
  - *Availability:* baseline of 4 days, n = 24 snapshots each, unusable counts d = 2, 4, 3, 3.
    sum(d) = 12, sum(n) = 96, p-bar = 12 / 96 = 0.125.
    Upper, n = 24: P(X >= 10) = 0.000342 <= 0.00135 but P(X >= 9) = 0.001656 > 0.00135, so u = 9 and
    UCL = 9 / 24 = 0.375. Lower: P(X = 0) = 0.875^24 = 0.0406 > 0.00135, so l = 0 and no day can flag low.
    For a day with only n = 20 snapshots: u = 8, UCL = 8 / 20 = 0.40.
    A new day with n = 24 and d = 10: p = 0.416667 > 0.375, **flagged**. A new day with d = 8:
    p = 0.333333 <= 0.375, **not flagged**. (The normal formula's UCL is
    0.125 + 3 * sqrt(0.125 * 0.875 / 24) = 0.327523, which would wrongly flag d = 8; the test must not.)
  - *Maintenance:* baseline 10 broken of 100 docked bikes, p-bar = 0.10, n = 100.
    Upper: P(X >= 21) = 0.000808 <= 0.00135 but P(X >= 20) = 0.001979, so u = 20 and UCL = 0.20.
    Lower: P(X <= 1) = 0.000322 <= 0.00135 but P(X <= 2) > 0.00135, so l = 2 and LCL = 0.02 (flag d <= 1).
    A monitored day with 25 of 100: p = 0.25 > 0.20, **flagged**. A day with 20 of 100: not flagged.
  - *Typical first-unusable time:* baseline first-empty times 07:35, 07:40 and 07:50 on 3 of 10 days
    (the other 7 never emptied): median = 07:40, reported as "on 3 of 10 days".
  - *Degenerate cases:* a station never unusable in the baseline (p-bar = 0) or always unusable
    (p-bar = 1): no limits and the "insufficient basis" message, never a limit of 0 or 1. A subgroup
    with n = 0 is dropped with a message. Bad input (negative count, duplicate snapshot, missing
    value) is rejected with a message naming the row.

Fixed for every team:
- The statistic lives in **one plain, tested function** (`app/qc.py` or `app/qc.R`). The API, app or
  package only calls it and displays the result. No statistics inside UI code.
- Every statistic has a test against a known answer and a degenerate case (constant data, n = 1, missing values).
- You can explain every number the tool prints. If you cannot, it is not done.

## 5. Delivery (rubric: working tool 25)
- **Stack:** REST API (FastAPI, Python) that also serves one built React (Vite) page: **one deployed
  service** on Posit Connect, so there is no CORS and no second content item.
  API: `GET /api/datasets` and `GET /api/report?dataset=<name>`; `<name>` must be one of the bundled
  files in `data/` (no arbitrary paths). The report holds both windows and the maintenance chart.
- **Starting demo:** `demos/fastapi/` copied into `app/`; the React page from `demos/reactfront/` goes in `app/frontend/` (task H-05) and its built `dist/` is served by FastAPI.
- **Code split:** `app/qc.py` (the p-chart function, written and tested first, then frozen);
  `app/availability.py` and `app/maintenance.py` (each builds its subgroups from the CSV and calls
  `qc.py`; separate tests; neither imports the other). Imports must work both from the repo root
  (`pytest`) and from inside `app/` (`testme.sh` and Posit Connect run from `app/`).

Fixed for every team:
- Start from **one** demo in `demos/`, copied to `app/`. Keep its four-script contract
  (`testme`, `manifestme`, `deployme`, `README.md`); `testme` starts the tool with one command.
- Deployed on the course **Posit Connect** server with a public URL (publisher key handed out at the
  event). Deploy early: copy one workflow from
  [`.claude/skills/connect-publish/workflows/`](.claude/skills/connect-publish/workflows/).
- A small tool that runs beats a large tool that does not.

## 6. Outputs
- **What the user sees:** one page with a dataset selector, a banner "Synthetic demonstration data;
  control-chart signals are exploratory", and two tabs.
  - **Availability tab**, with an AM / PM switch:
    - a **dispatch table**, one row per station for the latest day: share unusable (0-1) with empty
      and full counts, p-bar, UCL, an out-of-control flag, the typical first-unusable time, and the
      action from section 4. How to read it: work from the top; red rows are out of control today.
    - a **p-chart for the selected station**: share unusable per weekday, the center line, the
      stepped UCL and LCL (they move with n), and the 0.10 target line; out-of-control days in red.
      How to read it: a red point is a one-off to investigate; points inside the limits but above
      the target line mean a built-in problem that vans will not fix.
  - **Maintenance tab:** the network p-chart of the broken-bike share per weekday, and the list of
    stations to inspect, most broken bikes first. How to read it: a red point means more bikes broke
    than normal; work down the list.

## 7. Test datasets and codebook (rubric: demo 10, datasets 5, codebook 5)
2-3 small CSVs in `data/`, invented but shaped like real field data, each showing one behavior.
`data/README.md` is the codebook: every file, every column with units, and what it would take to
collect this data for real.
- **Datasets:** each is 10 stations x 15 weekdays x 48 five-minute snapshots (24 in 07:00-08:55, 24 in
  16:00-17:55), in the `station_status.csv` format; the first 10 weekdays are the baseline.
  - `stable.csv`: a normal network. Residential stations empty in the AM and fill in the PM;
    downtown stations do the opposite. One "chronic" hilltop station is in control but above the
    0.10 target every morning. A low, steady broken-bike share.
  - `planted_events.csv`: the same network with two planted signals after the baseline: on day 12 a
    downtown station is full for most of the PM window (a stadium event), and from day 13 the
    broken-bike share doubles. Both must flag; no baseline day may.
  - `edge_case.csv`: 2 stations x 15 weekdays: one never empty or full (p-bar = 0, "insufficient
    basis"), and missing snapshots on some days (n < 24, so the limits step up).
  `data/README.md` gives every column with units, the baseline, how each file was generated (with
  the random seed), the chart behavior each one should show, and how a real operator would log the
  GBFS feed to get the same file.

## 8. Documentation and reproducibility (rubric: docs 10, public repo 5)
- `README.md` says what the tool does, for whom, every input and parameter, how to run it in one
  command, and walks through the demo on each test dataset.
- Public GitHub repo; a fresh clone runs `testme` and the tests pass with no extra steps.
- Submit on Devpost: the repo link plus a demo.

## 9. Out of scope
What we will NOT build, so nobody (human or agent) builds it by accident.
- Default: logins, databases, real customer data, a second statistic before the first one is tested.
- No live polling of a GBFS feed (the tool reads bundled CSVs); no file upload; no maps; no van
  assignment, routing or crew scheduling; no demand forecasting; no repair-time estimates; no ML;
  no extra charts or visual polish before the tests pass. Stretch, only if everything else is done
  and deployed: a time-to-empty reliability model with censoring.