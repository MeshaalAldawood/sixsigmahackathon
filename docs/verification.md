# Verification record

What was checked, how, and what it printed. Recorded 2026-10-17 (on-campus track).

## Test suites

| Command | Result |
|---|---|
| `python -m pytest -q` (repo root) | `63 passed, 1 warning` (the warning is a Starlette deprecation in the test client) |
| `npm --prefix app/frontend ci && npm --prefix app/frontend run test -- --run` | `4 passed` |
| `npm --prefix app/frontend run build` | builds `app/static/`; a fresh build is byte-identical to the committed bundle |

## Statistics: independent review (H-03, H-09, H-10, H-11)

H-03, H-09 and H-10 were each reviewed independently when they were built (see their CONTRACT results).
H-11's replay backend was reviewed in a fresh context by a read-only reviewer that ran the code.
Every check passed:

- **Exact limits by hand:** `stable`, `downtown_01`, AM, `n = 24`: `scipy.stats.binom` gives `p̄ = 0.083333`, `u = 7`,
  `UCL = 0.291667`, `l = 0`. The code gives the same values.
- **Worked answers in SPEC section 4** (`tests/test_qc.py`): UCL 0.375 at n = 24, 0.40 at n = 20; d = 10 flags, d = 8 does not;
  maintenance UCL 0.20, LCL 0.02. Onset median 07:40 is tested in `tests/test_availability.py`.
- **Degenerate:** `p̄ = 0` and `p̄ = 1` give no limits and status `insufficient_basis`; a subgroup with n = 0 has a null share.
- **Replay:** future-suffix invariance at four cutoffs; the 10-day baseline stays frozen; values are withheld before 2026-10-16 18:00;
  AM is provisional at 08:55 and 08:59 and final at 09:00; PM is provisional at 17:55 and final at 18:00; rewinding equals a fresh call;
  the final cutoff gives the same result as no cutoff; missing and stale stations are labelled; missing 07:00 coverage is labelled;
  onset is "07:40 on 3 of 8 observed days" with 2 baseline days missing.
- **API errors:** a bad dataset name, a malformed `as_of`, or an out-of-range `as_of` returns HTTP 422 with a message.

Reviewer notes, which do not change the verdict: a station never unusable in the baseline gets the action
"OK" with no limits; a maintenance point with partial 07:00 coverage is still judged, with a coverage warning.

## Demonstrations reproduced from the report API

| Dataset | Observed |
|---|---|
| `stable` | 0 flagged availability points (AM and PM) and 0 maintenance flags; maintenance `p̄ = 0.05`; `hilltop_01` AM action "capacity review: unusable every day" |
| `planted_events` | exactly one availability flag: PM `stadium_01` 2026-10-20, 18/24 (not a baseline day); maintenance flags 40/400 on 2026-10-21, 22, 23 |
| `edge_case` | 0 flags; `edge_01` has status `insufficient_basis` and a null UCL in both windows; `edge_02` AM UCL 0.375 |

## Fresh clone

`git clone` into an empty folder, then:

- `python -m pytest -q`: `63 passed`
- frontend `ci`, tests (`4 passed`) and build: `git status --porcelain app/static` is empty
- `bash app/testme.sh` with `PORT=8767`: `/`, `/api/datasets` and all three `/api/report?dataset=…` return 200
- `powershell -File app\testme.ps1` with `PORT=8768`: `/api/report?dataset=stable` returns 200

## Deployment bundle

Only the files listed in `app/manifest.json` were copied to an empty folder and started there.
`/`, `/api/datasets`, `/api/replay-clock` and all three reports returned 200, so the bundle does not
depend on the repo's `data/` folder. `tests/test_startup.py` keeps the manifest checksums, the static
asset list and the CSV copies in step.

## Browser QA

Recorded in [`integration.md`](integration.md#browser-qa-record-2026-10-17-playwright-chromium-local-build):
1440/768/375 px, all three datasets, both windows, maintenance, keyboard rewind, null limits, 0 console errors.

## Not yet verified

- GitHub Actions runs (`tests.yml`, `deploy-fastapi.yml`): need a push to GitHub.
- Public Posit Connect URL, checked logged out: needs the event's publisher key ([`deployment.md`](deployment.md)).
- Devpost submission and the official prompt number (H-08).
