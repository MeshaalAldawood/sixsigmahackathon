# SPEC: Six Sigma Hackathon team project

What your tool IS. Your agent reads this before every task. Where the code and this file
disagree, the code is the bug: change this file first, then the code.

Most of this page is already decided by the event and the [rubric](docs/criteria.md).
**Only the `FILL IN` lines change, and you do not have to write them by hand:** describe your app and ask your agent to update them. They depend on the prompt your team picks at kickoff
(prompts are secret until then, see [`docs/prompts.md`](docs/prompts.md)) and on your team.
The examples after each `FILL IN` show the shape of an answer. They are not hints about the prompts.

## 1. Team and prompt
- **Team name:** FILL IN. Example: "Control Freaks"
- **Track:** On-campus (24 hours). Submissions due Sat Oct 17, 1 PM ET; showcase 2-3 PM.
- **Prompt we chose:** Urban Systems: "Bikeshare Fleets" (prompt number: copy it from Devpost). A municipal bikeshare system has a "docks full / docks empty" crisis at rush hour and maintenance vans are dispatched blindly; design a tool to track dock availability, when and where stations are unusable, and support the network's performance.
- **Our public repo:** github.com/MeshaalAldawood/sixsigmahackathon

## 2. User and use case (rubric: scope 5, user and use case 5)
- **User:** the bikeshare rebalancing dispatcher who assigns the maintenance vans for the weekday morning rush.
- **Decision the tool helps them make, and when:** each evening, before the next morning rush: which stations get a van (and whether to drop bikes or pull bikes), by what time the van must arrive, and which stations vans cannot fix because they are unusable every day (those go to planning for more docks or a standing rebalancing slot instead).
- **Why this matches the prompt:** it turns the dock-availability feed into a record of when and where stations are unusable, and replaces blind van dispatch with a ranked, timed list.

## 3. Inputs (rubric: minimal inputs 5)
Only what this user can actually measure or already knows. Fewer is better; every input a user
cannot measure costs points.

| Input | Type and units | Where the user gets it |
|---|---|---|
| `station_status.csv`, one row per station per snapshot: `timestamp`, `station_id`, `bikes_available`, `docks_available` | timestamp: local time, ISO 8601; station_id: text; bikes and docks: integer counts | the system's public GBFS `station_status` feed, logged every 5 minutes (every bikeshare system already publishes it) |
| Rush window | start and end clock time; default 07:00-09:00, weekdays | the operator's own definition of the morning peak |
| Baseline days | integer count of days; default the first 10 weekdays in the file | a period the dispatcher considers normal operation |
| Target unusable share | a proportion; default 0.10 (a station unusable at most 10% of the rush window) | the city's service-level agreement with the operator |

## 4. The statistics, and why (rubric: valid QC analysis 25)
Say the method in words before any code exists. Load the `stats-first-steering` skill first.
- **Method:** two statistics, built and tested in this order.
  1. **p-chart of the unusable share, one chart per station.** A snapshot is *unusable* (a defect)
     when `bikes_available == 0` (empty: nobody can start a trip) or `docks_available == 0` (full:
     nobody can end one). One subgroup = one station on one weekday's rush window; n_i = the number
     of snapshots logged in that window (normally 24 at 5-minute spacing, fewer if snapshots are
     missing), d_i = unusable snapshots, p_i = d_i / n_i. From the baseline days only:
     p-bar = sum(d) / sum(n). Limits per subgroup (they vary with n_i):
     UCL_i = p-bar + 3 * sqrt(p-bar * (1 - p-bar) / n_i), LCL_i = max(0, p-bar - 3 * sqrt(p-bar * (1 - p-bar) / n_i)).
     Run rule: Western Electric rule 1 only (a point above UCL or below LCL). The empty and full
     counts are also reported separately, so the dispatcher knows whether to drop or pull bikes.
  2. **Time to empty (and time to full), exponential model with right-censoring.** For each
     station-day, t = minutes from the rush-window start to the first snapshot that is empty. If the
     station never empties during the window, it is *censored* at the window length (we only know
     it lasted at least that long). With r = number of station-days that emptied and T = sum of all
     t (emptied and censored): lambda-hat = r / T per minute, MTTF = 1 / lambda-hat,
     P(empty by t) = 1 - exp(-lambda-hat * t), median time to empty = ln(2) / lambda-hat. The same
     function, run on `docks_available == 0`, gives time to full.
- **Why it fits the use case:** the p-chart separates a special cause (one bad day above the limits: an event or a broken dock, so send a van and investigate) from a common cause (a station in control but with p-bar above the 0.10 target every day: vans will not fix it, the station needs more docks or a standing rebalancing slot), and the time-to-empty model tells the van when it has to arrive, not only where.
- **Assumptions and how the tool checks them:**
  - p-chart: snapshots within a window are treated as independent trials, which they are not quite (an empty station at 7:35 is likely still empty at 7:40), so the limits are somewhat too narrow; the README says so and the demo shows how many points flag on the in-control dataset. Limits come from the baseline days only, never from days that include the event we want to detect.
  - Exponential model: constant hazard. Bikes drain steadily, so the true hazard probably rises through the rush; the demo plots the observed share of station-days empty by each 15-minute mark next to the model curve, so the fit can be judged by eye. A Weibull fit is out of scope unless the exponential is clearly wrong and time remains.
  - Censoring is handled: MTTF is never the plain average of the observed emptying times.
- **Known-answer check:** worked by hand, must be reproduced exactly.
  - *p-chart:* baseline of 4 days, n = 24 snapshots each, unusable counts d = 2, 4, 3, 3.
    sum(d) = 12, sum(n) = 96, p-bar = 12 / 96 = 0.125.
    For n = 24: sqrt(0.125 * 0.875 / 24) = sqrt(0.0045573) = 0.067508; UCL = 0.125 + 3 * 0.067508 = 0.327523;
    LCL = 0.125 - 0.202523 < 0, so LCL = 0.
    For a day with only n = 20 snapshots: sqrt(0.125 * 0.875 / 20) = 0.073951; UCL = 0.346853; LCL = 0.
    A new day with n = 24 and d = 10: p = 10 / 24 = 0.416667 > 0.327523, so it is flagged out of control.
  - *Time to empty:* 5 station-days with a 120-minute window. Three emptied at 30, 45 and 60 minutes;
    two never emptied (censored at 120 and 120). r = 3, T = 30 + 45 + 60 + 120 + 120 = 375 minutes.
    lambda-hat = 3 / 375 = 0.008 per minute; MTTF = 125 minutes;
    P(empty by 30 min) = 1 - exp(-0.24) = 0.213372; P(empty by 60 min) = 1 - exp(-0.48) = 0.381217;
    median = ln(2) / 0.008 = 86.643 minutes. (The wrong, uncensored answer would be the mean of
    30, 45, 60 = 45 minutes; the test must not accept it.)
  - *Degenerate cases:* p-bar = 0 (never unusable in the baseline) or p-bar = 1 (always unusable):
    the limits are undefined, so the function returns no limits and a clear message, never a limit of 0.
    A subgroup with n = 0 is dropped with a message. Zero station-days emptied: lambda-hat and MTTF
    cannot be estimated, so return None and the message "never emptied in T minutes observed", never inf or 0.

Fixed for every team:
- The statistic lives in **one plain, tested function** (`app/qc.py` or `app/qc.R`). The API, app or
  package only calls it and displays the result. No statistics inside UI code.
- Every statistic has a test against a known answer and a degenerate case (constant data, n = 1, missing values).
- You can explain every number the tool prints. If you cannot, it is not done.

## 5. Delivery (rubric: working tool 25)
- **Stack:** REST API (FastAPI, Python) with a React dashboard (Vite) as its front end.
- **Starting demo:** `demos/fastapi/` copied into `app/`; the React front end from `demos/reactfront/` goes in `app/frontend/` (owned by task H-05).

Fixed for every team:
- Start from **one** demo in `demos/`, copied to `app/`. Keep its four-script contract
  (`testme`, `manifestme`, `deployme`, `README.md`); `testme` starts the tool with one command.
- Deployed on the course **Posit Connect** server with a public URL (publisher key handed out at the
  event). Deploy early: copy one workflow from
  [`.claude/skills/connect-publish/workflows/`](.claude/skills/connect-publish/workflows/).
- A small tool that runs beats a large tool that does not.

## 6. Outputs
- **What the user sees:**
  - A **dispatch table**, one row per station, for the latest day: share unusable (0-1) with empty and
    full shown separately, p-bar, UCL, an out-of-control flag, the median time to empty or full (minutes
    after the rush starts), and an action: "send van: drop bikes by HH:MM", "send van: pull bikes by HH:MM",
    "investigate: special cause", "capacity review: unusable every day", or "OK".
    How to read it: work from the top; red rows are out of control today.
  - A **p-chart per station**: share unusable per day, with the center line, the varying UCL and LCL,
    and the target line at 0.10; out-of-control days in red. How to read it: a red point is a one-off
    to investigate; points inside the limits but above the target line mean a built-in problem.
  - A **time-to-empty curve per station**: P(empty by t) over the rush window, with the observed shares as
    dots. How to read it: the van should arrive before the curve crosses 0.5.

## 7. Test datasets and codebook (rubric: demo 10, datasets 5, codebook 5)
2-3 small CSVs in `data/`, invented but shaped like real field data, each showing one behavior.
`data/README.md` is the codebook: every file, every column with units, and what it would take to
collect this data for real.
- **Datasets:** each is 8 stations x 15 weekdays x 24 five-minute snapshots (07:00-08:55), in the `station_status.csv` format.
  - `in_control.csv`: a stable network; most stations rarely unusable, and one "chronic" station
    (a hilltop dock that empties every morning) sits inside its limits but above the 0.10 target.
  - `planted_special_cause.csv`: the same network, except a planted event on day 12 fills one
    downtown station for most of the window; that day must flag, and no baseline day should.
  - `edge_case.csv`: one station that is never empty or full (p-bar = 0, no limits, never emptied),
    plus missing snapshots on some days (n_i < 24, so the limits widen).

## 8. Documentation and reproducibility (rubric: docs 10, public repo 5)
- `README.md` says what the tool does, for whom, every input and parameter, how to run it in one
  command, and walks through the demo on each test dataset.
- Public GitHub repo; a fresh clone runs `testme` and the tests pass with no extra steps.
- Submit on Devpost: the repo link plus a demo.

## 9. Out of scope
What we will NOT build, so nobody (human or agent) builds it by accident.
- Default: logins, databases, real customer data, a second statistic before the first one is tested.
- No live polling of a GBFS feed (the tool reads a CSV log); no van route optimization or maps; no demand
  forecasting; no evening-rush analysis unless the morning rush is done; Weibull fit only if time remains.
