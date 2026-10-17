// A p-chart drawn from backend points. It does no statistics: every value it plots (p, p_bar,
// lcl, ucl, flags) comes from GET api/report. Limits are drawn as steps because they move
// with n (a day with missing snapshots gets a wider limit).

const W = 760
const H = 300
const PAD = { l: 48, r: 92, t: 16, b: 40 }

const pct = (x) => `${(100 * x).toFixed(1)}%`

export default function PChart({ points, pBar, target, baselineCount, title, unitLabel }) {
  if (!points.length) return <p className="notice">No points to plot.</p>
  const hasLimits = points.some((p) => p.ucl !== null)
  const values = points.flatMap((p) => [p.p ?? 0, p.ucl ?? 0])
  if (pBar !== null && pBar !== undefined) values.push(pBar)
  if (target !== undefined) values.push(target)
  // Proportions never exceed 100%, so the axis stops there.
  const top = Math.min(1, Math.max(0.05, ...values) * 1.12)

  const step = (W - PAD.l - PAD.r) / points.length
  const x = (i) => PAD.l + step * (i + 0.5)
  const y = (v) => PAD.t + (H - PAD.t - PAD.b) * (1 - v / top)

  const stepPath = (key) =>
    points
      .map((p, i) => (p[key] === null ? null : `M${x(i) - step / 2},${y(p[key])}H${x(i) + step / 2}`))
      .filter(Boolean)
      .join('')

  const flagged = points.filter((p) => p.flagged_high || p.flagged_low).length
  const label = `${title}: ${points.length} days, ${flagged} outside the control limits`
  const ticks = [0, top / 2, top].map((v) => Number(v.toFixed(3)))
  const lastLimit = [...points].reverse().find((p) => p.ucl !== null)

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        {ticks.map((t) => (
          <g key={t} className="tick">
            <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} />
            <text x={PAD.l - 6} y={y(t) + 4} textAnchor="end">{pct(t)}</text>
          </g>
        ))}
        {baselineCount > 0 && baselineCount < points.length && (
          <g className="baseline">
            <line x1={x(baselineCount - 1) + step / 2} x2={x(baselineCount - 1) + step / 2} y1={PAD.t} y2={H - PAD.b} />
            <text x={x(baselineCount - 1) + step / 2 - 4} y={PAD.t + 12} textAnchor="end">baseline</text>
          </g>
        )}
        {target !== undefined && (
          <g className="target">
            <line x1={PAD.l} x2={W - PAD.r} y1={y(target)} y2={y(target)} />
            <text x={W - PAD.r + 6} y={y(target) + 4}>target {pct(target)}</text>
          </g>
        )}
        {pBar !== null && pBar !== undefined && (
          <g className="center">
            <line x1={PAD.l} x2={W - PAD.r} y1={y(pBar)} y2={y(pBar)} />
            <text x={W - PAD.r + 6} y={y(pBar) + 4}>p̄ {pct(pBar)}</text>
          </g>
        )}
        {hasLimits && <path className="limit" d={stepPath('ucl')} />}
        {hasLimits && <path className="limit" d={stepPath('lcl')} />}
        {lastLimit && (
          <text className="limit-label" x={W - PAD.r + 6} y={y(lastLimit.ucl) + 4}>UCL {pct(lastLimit.ucl)}</text>
        )}
        {lastLimit && lastLimit.lcl > 0 && (
          <text className="limit-label" x={W - PAD.r + 6} y={y(lastLimit.lcl) + 4}>LCL {pct(lastLimit.lcl)}</text>
        )}
        <polyline className="series" points={points.map((p, i) => `${x(i)},${y(p.p ?? 0)}`).join(' ')} />
        {points.map((p, i) => {
          const out = p.flagged_high || p.flagged_low
          return (
            <circle key={p.date} cx={x(i)} cy={y(p.p ?? 0)} r={out ? 7 : 4} className={out ? 'pt out' : 'pt'}>
              <title>
                {`${p.date}: ${p.d} of ${p.n} ${unitLabel} (${pct(p.p ?? 0)})`}
                {p.ucl !== null ? `, limits ${pct(p.lcl)} to ${pct(p.ucl)}` : ', no control limits'}
                {p.flagged_high ? ', ABOVE the upper limit' : ''}
                {p.flagged_low ? ', BELOW the lower limit' : ''}
              </title>
            </circle>
          )
        })}
        {points.map((p, i) =>
          i % 2 === 0 || i === points.length - 1 ? (
            <text key={`d${p.date}`} className="axis" x={x(i)} y={H - PAD.b + 18} textAnchor="middle">
              {p.date.slice(5)}
            </text>
          ) : null,
        )}
      </svg>
      <figcaption>
        <span className="key series-key">share per day</span>
        {pBar !== null && pBar !== undefined && <span className="key center-key">center line p̄</span>}
        {hasLimits ? <span className="key limit-key">control limits (step with n)</span> : <span className="key">no control limits</span>}
        {target !== undefined && <span className="key target-key">service target (not a control limit)</span>}
        <span className="key out-key">outside the limits</span>
      </figcaption>
    </figure>
  )
}
