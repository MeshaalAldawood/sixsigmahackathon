# Synthetic demonstration walk-through

Build and start the application as described in `docs/integration.md`. The
scenario selector shows the three bundled CSVs. Every number below was
observed from the local report API on 2026-10-17, using the 15 weekdays ending
2026-10-23. Counts and alerts are exploratory because successive five-minute
snapshots are dependent.

1. **Stable:** Select `stable`. Switch between AM and PM, then choose a station
   to view its daily p-chart. The latest day (2026-10-23) has no station
   out-of-control flags in either rush, and the network maintenance chart has
   no flagged days. Across the full stable dataset, there are zero flagged
   station or maintenance points. The latest PM dispatch starts with
   `downtown_01`, “van: drop bikes before 16:48.”
2. **Planted events:** Select `planted_events`, PM, and station `stadium_01`.
   On 2026-10-20 its unusable count is 18/24 and its chart flags the planted
   stadium event. The network broken-bike chart flags 40/400 on each of
   2026-10-21, 2026-10-22 and 2026-10-23. The list below the chart ranks
   stations by disabled bikes; `downtown_01` has four on the latest day.
   No baseline day flags in either chart.
3. **Edge case:** Select `edge_case`. `edge_01` has a zero-unusable
   baseline in both rushes, so its control limits are absent and the chart
   displays an insufficient-basis warning. Missing snapshots at `edge_02`
   make its subgroup sizes vary; the visible UCL changes with n. The latest
   AM action for `edge_02` is “capacity review: unusable every day.”

The dispatch table shows empty and full counts separately and gives typical
first-unusable time only when the baseline observed such an onset. Missing
onsets and limits display as “—” or an explicit warning, never as zero.

## Replay the synthetic shift

The clock starts paused at the original ten-day baseline close (18:00). Use
**Next snapshot** or **Play** to move into later weekdays; change speed or
drag the seek control to move faster. The planted-events scenario has jumps
to the stadium PM event and the following broken-bike rise. Rewind before the
calibration close to see baseline shares, exact limits and onset times withheld.
Stop at 08:55 or 17:55 to see measured rush counts marked provisional, then
step to 09:00 or 18:00 for the final window verdict. Current station status
always states when each synthetic snapshot was last seen, and marks missing
and stale observations explicitly.
