# Demo: the tool on each test dataset

Every number below was **observed** from the running tool (`GET /api/report`, and the page in a
browser) on 2026-10-17, not predicted. All three datasets are **synthetic**
([data/README.md](../data/README.md)).

## Start it

```bash
bash app/testme.sh
```

Open <http://localhost:8000>. Pick a dataset at the top; switch between the **Availability** and
**Maintenance** tabs and between the **AM** and **PM** rush. To see the raw numbers instead:

```bash
curl -s "http://localhost:8000/api/report?dataset=planted_events.csv" | python -m json.tool | less
```

Every dataset has the same calendar: baseline **2026-09-14 to 2026-09-25** (10 weekdays), latest
day **2026-10-02**, which is the day the dispatch table describes.

---

## 1. `stable.csv`: a normal network

**Availability, AM, dispatch table for 2026-10-02:**

| Station | Unusable | Empty / full | p̄ | UCL | Action |
|---|---|---|---|---|---|
| S01 | 1/24 | 1 / 0 | 5.4% | 25.0% | van: drop bikes before 08:52 |
| S04 | 3/24 | 0 / 3 | 9.2% | 29.2% | van: pull bikes before 08:50 |
| S05 | 2/24 | 0 / 2 | 7.5% | 29.2% | collect broken bikes first |
| S06 | 3/24 | 0 / 3 | **10.0%** | 33.3% | van: pull bikes before 08:50 |
| S07 | 7/24 | 7 / 0 | **26.3%** | 54.2% | **capacity review: unusable every day** |
| S10 | 0/24 | 0 / 0 | 1.3% | 12.5% | OK |

(S02, S03, S08 and S09 also get a van direction; the page lists every station.)

How to read it:
- **S07, the hilltop**, is inside its control limits every day, but empty 26% of the morning rush on
  average, far above the 10% target. A van will not fix that; it is a capacity problem.
- **S06** sits exactly on the target (24 of 240 baseline snapshots = 10.0%). The rule is "above the
  target", so it is not sent to capacity review.
- **S05** was full while holding broken bikes, so the first job is to collect them, not to pull
  working bikes.
- "Before 08:52" is the median first-empty time over the 8 baseline days on which S01 emptied
  (08:50 and 08:55 in the middle, averaged and rounded down).

**Maintenance:** 20 broken of 200 docked bikes on a normal day; p̄ = 10.0%, limits 8 to 34 broken
bikes (LCL 4.0%, UCL 17.0%). Daily counts 18-22. Station list for 2026-10-02 07:00: S09 5, S10 5,
S01 3, S03 3, S02 2, S05 2, S07 1, each "inspect and collect broken bikes".

**False-alert count on the stable data:** across both windows there are 200 baseline points and
100 monitored points with valid limits. **0 high flags and 0 low flags** on either, and **0 of 15**
maintenance points flag. That zero is a property of these designed files; real dock data, where
empty spells come in clumps, would flag more often (see [docs/statistics.md](../docs/statistics.md)).

---

## 2. `planted_events.csv`: two planted problems

The same network, identical through 2026-09-25, plus two planted signals.

**Stadium event (Availability, PM, station S08):** on 2026-09-29 S08 was full in **22 of 24** PM
snapshots (p = 91.7%). Its baseline share is 4.2%, so the exact binomial upper count for a
24-snapshot day is 5 (UCL 20.8%), and **22 > 5 flags it high**. On the page, that point is red on
S08's PM chart. It is the only availability flag in the file: 0 of the 200 baseline points and
1 of the 100 monitored points flag. The dispatch table describes 2026-10-02, when S08 was back to
normal (1 empty snapshot, "van: drop bikes before 17:55"); the chart keeps the history visible.

**Broken-bike surge (Maintenance):**

| Day | Broken / docked at 07:00 | Result |
|---|---|---|
| 2026-09-28, 09-29 | 20 / 200, 21 / 200 | inside the limits |
| **2026-09-30** | **40 / 200** | **above UCL 17.0% (40 > 34)** |
| **2026-10-01** | **38 / 200** | **above** |
| **2026-10-02** | **42 / 200** | **above** |

How to read it: from 2026-09-30 the network suddenly has twice the usual broken bikes, a special
cause worth finding (a bad batch of bikes, vandalism). The station list for 2026-10-02 says where to
start: S09 10, S10 10, S01 6, S03 6, S02 4, S05 4, S07 2.

The S07 capacity review and every other AM action are the same as in `stable.csv`, because the
planted events do not touch them.

---

## 3. `edge_case.csv`: what the tool does with thin data

Two stations; 1,432 rows (8 snapshots are missing).

| Station | What happens | What the page shows |
|---|---|---|
| **E01** | never empty or full in the baseline: p̄ = 0 in both windows | no control limits, status "no limits (insufficient basis)", action "no action needed today; no control limits (insufficient basis)", and the chart warning "p_bar = 0 (never defective in the baseline): insufficient basis for control limits". It never claims E01 is "in control". |
| **E02 AM** | 4 snapshots missing on 2026-09-16 (07:30-07:45), so n = 20 that day | the limit steps up: upper count 6 of 20, **UCL 30.0%** instead of 25.0% on full days |
| **E02 PM** | 4 snapshots missing on 2026-09-28 (17:00-17:15), n = 20 | upper count 5 of 20, **UCL 25.0%** instead of 20.8% |

Latest-day actions: E02 AM "van: drop bikes before 08:50"; E02 PM "collect broken bikes first"
(full while holding a broken bike). Maintenance: 3 broken of 31 docked every day, no flags.

---

## The four things to say at the showcase

1. One statistic, an exact binomial p-chart, checked against hand-worked answers
   ([docs/statistics.md](../docs/statistics.md)).
2. A red point is a special cause: investigate. In control but above the 10% target is a
   capacity problem, which is a different decision.
3. The planted stadium day and the broken-bike surge are found; the stable network raises nothing.
4. With too little information the tool says so instead of inventing an alert.
