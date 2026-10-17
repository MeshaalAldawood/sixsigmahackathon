# Frontend integration

The React source is in `app/frontend/`. Run `npm --prefix app/frontend ci` and
`npm --prefix app/frontend run build` from the repository root. Vite writes the
production page to `app/static/`, which FastAPI serves on the same origin as
`/api/datasets` and `/api/report`. Asset URLs and API requests are relative so
the bundle can be hosted below a Posit Connect content path.

To work on the page locally, start FastAPI from the repository root with
`python -m uvicorn app.app:app --reload`. The page at `http://127.0.0.1:8000/`
serves the last production build. Rebuild after changing React source. The
dataset selector requests only the allowlisted names from `/api/datasets`;
switching datasets aborts an old report request. All shares, limits, flags,
onset counts and actions come from the report response. The page performs
formatting and chart positioning only.

The starter I-MR calculation and sample fill-weight data were removed.
The page retains null chart values as missing and shows the backend warnings,
including the insufficient-basis message. The persistent banner identifies
the data as synthetic and the signals as exploratory.

## Simulated replay

The page first requests `/api/replay-clock` for navigation metadata, then
requests `/api/report` at the original tenth baseline weekday's 18:00 close.
It starts paused there, with no later measurements displayed. Play/Pause,
previous/next snapshot, the seek control, and speed choose an `as_of` clock;
each report is recalculated on the server. The planted-events scenario also
offers jumps to the synthetic stadium and broken-bike events. The speed is a
minimum delay between completed report requests, so slow requests do not cause
the display to skip observations.

Each report section opens with a one-line verdict built only by counting backend
fields: out-of-control station IDs and action counts for the rush window
(withheld while it is provisional), and for maintenance the latest 07:00 point
against its UCL plus the first three stations in the backend's inspection order.
The event jumps also open the view where the event shows: the stadium jump
selects PM and `stadium_01`, the broken-bike jump opens Maintenance. While the
replay steps, the previous report stays on screen (`aria-busy` marks the update)
and the clock is not announced during playback.

Availability points and dispatch rows use the backend's `provisional` flag.
The current station list shows the last observed counts, their timestamp and
age, plus stale or missing state. The maintenance heading shows exact 07:00
station coverage and staleness. Chart paths preserve gaps for absent days and
join consecutive exact limit values as steps. Null observations never receive
a zero ordinate.

## Browser QA record (2026-10-17, Playwright Chromium, local build)

Screenshots are in `demo/screenshots/`.

| Check | Width | Observation |
|---|---|---|
| `stable`, AM, default clock 2026-10-16 18:00 | 1440 | All 10 stations in control; `downtown_01` 2/24 = 8.3%, UCL 29.2%. Screenshot `stable-1440.png`. |
| `planted_events`, "Stadium PM event" jump, PM, `stadium_01` | 1440 | Clock 2026-10-20 18:00; `stadium_01` 18/24 = 75.0%, "Out of control", red point. `planted-stadium-pm-1440.png`. |
| `planted_events`, "Broken-bike rise" jump, Maintenance | 1440 | Clock 2026-10-21 07:00; last point 40/400 = 10.0% flagged high; no later days drawn. `planted-maintenance-1440.png`. |
| Rewind with keyboard (focus seek slider, press Home) | 1440 | Clock 2026-10-05 07:00; "Baseline values withheld until 2026-10-16 · 18:00"; one maintenance point marked insufficient basis; focus outline visible. |
| `edge_case`, `edge_02` and `edge_01` | 768 | `edge_01` 0/24 shows "No limits" and UCL "—" (never 0); dispatch table scrolls inside its card. `edge-768.png`. |
| `edge_case` | 375 | Document scroll width 375 = viewport; the chart keeps a 530px minimum and scrolls inside its card. `edge-375.png`. |
| Console | all | 0 errors, 0 warnings. |

Controls are native buttons, radios, selects and a range input, so they are
keyboard operable; a `prefers-reduced-motion` rule is present. This pass used
Chromium emulation, not physical touch hardware. A label collision between
"10% target" and "baseline" when the centre line is near 10% was fixed by
right-aligning the target label.
