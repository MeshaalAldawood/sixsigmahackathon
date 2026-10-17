import { useEffect, useState } from 'react'
import { getDatasets, getReplayClock, getReport } from './api.js'

const percent = (value) => value == null ? '—' : `${(value * 100).toFixed(1)}%`
const signal = (point) => point?.flagged_high || point?.flagged_low
const pretty = (value) => value.replaceAll('_', ' ')
const clock = (value) => value?.replace('T', ' · ') ?? '—'

export function replayTicks(first, last) {
  if (!first || !last) return []
  const ticks = []
  const day = new Date(`${first.slice(0, 10)}T00:00:00`)
  const end = new Date(`${last.slice(0, 10)}T00:00:00`)
  while (day <= end) {
    if (day.getDay() !== 0 && day.getDay() !== 6) {
      const date = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
      for (const [start, finish] of [[420, 540], [960, 1080]]) for (let minute = start; minute <= finish; minute += 5) {
        const tick = `${date}T${String(Math.floor(minute / 60)).padStart(2, '0')}:${String(minute % 60).padStart(2, '0')}`
        if (tick >= first && tick <= `${last.slice(0, 10)}T18:00`) ticks.push(tick)
      }
    }
    day.setDate(day.getDate() + 1)
  }
  return ticks
}

const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`

// One-line answers built only by counting backend fields; no statistic is recomputed here.
export function availabilityVerdict(section, windowName) {
  const rows = section.stations
  if (section.provisional) return { tone: 'caution', headline: `${windowName} rush in progress`, details: [`Verdicts withheld until ${windowName === 'AM' ? '09:00' : '18:00'}`] }
  if (rows.every((row) => row.status === 'no_data')) return { tone: 'neutral', headline: `No ${windowName} observations yet`, details: [] }
  const flagged = rows.filter(signal).map((row) => row.station_id)
  const count = (prefix) => rows.filter((row) => row.action?.startsWith(prefix)).length
  const details = [
    [count('van: drop'), 'van drop'], [count('van: pull'), 'van pull'],
    [count('collect broken'), 'broken-bike pickup'], [count('capacity review'), 'capacity review'],
  ].filter(([n]) => n > 0).map(([n, word]) => plural(n, word))
  if (flagged.length) return { tone: 'bad', headline: `${plural(flagged.length, 'station')} out of control: ${flagged.join(', ')}`, details }
  return { tone: details.some((item) => item.includes('capacity')) ? 'caution' : 'ok', headline: 'No station out of control', details }
}

export function maintenanceVerdict(maintenance) {
  const latest = [...maintenance.chart.points].reverse().find((point) => point.p != null)
  const first = maintenance.stations.slice(0, 3).map((row) => row.station_id)
  const inspect = first.length ? [`Inspect first: ${first.join(', ')}`] : []
  if (!latest) return { tone: 'neutral', headline: 'No 07:00 measurement yet', details: [] }
  const share = `${percent(latest.p)} broken (${latest.d}/${latest.n}) on ${latest.date}`
  if (latest.ucl == null) return { tone: 'neutral', headline: `No limits yet: ${share}`, details: inspect }
  if (latest.flagged_high) return { tone: 'bad', headline: `Above normal: ${share}, UCL ${percent(latest.ucl)}`, details: inspect }
  if (latest.flagged_low) return { tone: 'ok', headline: `Below normal: ${share}, LCL ${percent(latest.lcl)}`, details: inspect }
  return { tone: 'ok', headline: `Within normal: ${share}, UCL ${percent(latest.ucl)}`, details: inspect }
}

function Verdict({ verdict }) {
  return <p className={`verdict ${verdict.tone}`}><strong>{verdict.headline}</strong>{verdict.details.map((item) => <span key={item}>{item}</span>)}</p>
}

export function initialReplayIndex(ticks, defaultAsOf) {
  return Math.max(0, ticks.indexOf(defaultAsOf))
}

export function chartPath(points, key, x, y, stepped = false) {
  let path = '', previous = false
  points.forEach((point, index) => {
    const value = point[key]
    if (value == null) { previous = false; return }
    path += previous ? stepped ? ` H${x(index)} V${y(value)}` : ` L${x(index)} ${y(value)}` : ` M${x(index)} ${y(value)}`
    previous = true
  })
  return path.trim()
}

function withMissingDays(points) {
  if (points.length < 2) return points
  const byDate = new Map(points.map((point) => [point.date, point]))
  const day = new Date(`${points[0].date}T12:00:00`)
  const end = new Date(`${points.at(-1).date}T12:00:00`)
  const filled = []
  while (day <= end) {
    if (day.getDay() !== 0 && day.getDay() !== 6) {
      const date = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
      filled.push(byDate.get(date) ?? { date, p: null, ucl: null, lcl: null })
    }
    day.setDate(day.getDate() + 1)
  }
  return filled
}

function Warnings({ items = [] }) {
  return items.length ? <div className="warnings" role="note"><strong>Data and chart notes</strong><ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></div> : null
}

function Chart({ points = [], center, target, title }) {
  points = withMissingDays(points)
  const observed = points.filter((point) => point.p != null)
  if (!observed.length) return <p className="empty">No observed points to chart.</p>
  const width = 900, height = 300, left = 48, right = 20, top = 18, bottom = 48
  const measured = points.flatMap((point) => [point.p, point.ucl, point.lcl]).filter((value) => value != null)
  const max = Math.min(1, Math.max(0.2, ...measured, center ?? 0, target ?? 0) * 1.1)
  const x = (index) => left + (width - left - right) * (points.length === 1 ? 0.5 : index / (points.length - 1))
  const y = (value) => top + (height - top - bottom) * (1 - value / max)
  const reference = (value, label, className, end = false) => value == null ? null : <g className={className}><line x1={left} x2={width - right} y1={y(value)} y2={y(value)} /><text x={end ? width - right - 4 : left + 4} y={y(value) - 5} textAnchor={end ? 'end' : 'start'}>{label}</text></g>
  return <div className="chart-wrap"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}: ${observed.length} observed points, ${observed.filter(signal).length} exploratory signals; missing days break the line`}>
    {[0, max / 2, max].map((value) => <g key={value} className="grid"><line x1={left} x2={width - right} y1={y(value)} y2={y(value)} /><text x={left - 7} y={y(value) + 4} textAnchor="end">{Math.round(value * 100)}%</text></g>)}
    {reference(target, '10% target', 'target', true)}
    {reference(center, 'baseline', 'center')}
    <path className="ucl" d={chartPath(points, 'ucl', x, y, true)} /><path className="lcl" d={chartPath(points, 'lcl', x, y, true)} />
    <path className="series" d={chartPath(points, 'p', x, y)} />
    {points.map((point, index) => point.p == null ? null : <circle key={`${point.date}-${index}`} className={point.provisional ? 'point provisional' : signal(point) ? 'point signal' : 'point'} cx={x(index)} cy={y(point.p)} r={point.provisional || signal(point) ? 6 : 4}><title>{`${point.date}: ${point.d}/${point.n} = ${percent(point.p)}; ${pretty(point.status)}`}</title></circle>)}
    <text className="date-label" x={left} y={height - 12}>{points[0]?.date}</text><text className="date-label" x={width - right} y={height - 12} textAnchor="end">{points.at(-1)?.date}</text>
  </svg><p className="chart-key">● Observed share <span className="key-limit">━ Exact control limits</span> <span className="key-target">┄ 10% service target</span> <span className="key-signal">● Exploratory signal</span></p></div>
}

// Each jump also opens the view where its synthetic event shows.
export function eventJumps(dataset, ticks) {
  if (dataset !== 'planted_events') return []
  const eventDays = ticks.filter((tick) => tick.endsWith('T07:00'))
  return [
    { label: 'Stadium PM event', tick: `${eventDays[11]?.slice(0, 10)}T18:00`, tab: 'availability', windowName: 'PM', stationId: 'stadium_01' },
    { label: 'Broken-bike rise', tick: eventDays[12], tab: 'maintenance' },
  ]
}

function Replay({ report, ticks, index, setIndex, playing, setPlaying, speed, setSpeed, dataset, onJump }) {
  const jumps = eventJumps(dataset, ticks)
  return <section className="replay-panel" aria-label="Synthetic replay controls">
    <div className="replay-title"><div><h2>Simulated replay</h2><p>Step through bundled snapshots. The clock changes what the report can know.</p></div><strong className="clock" aria-live={playing ? 'off' : 'polite'}>{clock(report.replay.as_of)}</strong></div>
    <div className="replay-controls"><button type="button" onClick={() => setPlaying(!playing)}>{playing ? 'Pause' : 'Play'}</button><button type="button" onClick={() => setIndex(Math.max(0, index - 1))} disabled={index === 0}>Previous snapshot</button><button type="button" onClick={() => setIndex(Math.min(ticks.length - 1, index + 1))} disabled={index === ticks.length - 1}>Next snapshot</button><label>Speed<select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}><option value="1000">1×</option><option value="400">2.5×</option><option value="150">6×</option></select></label></div>
    <label className="seek-label" htmlFor="replay-seek">Replay position <strong>{index + 1} / {ticks.length}</strong></label><input id="replay-seek" className="seek" type="range" min="0" max={ticks.length - 1} value={index} onChange={(event) => { setPlaying(false); setIndex(Number(event.target.value)) }} aria-valuetext={clock(ticks[index])} />
    <div className="replay-foot"><span>{clock(ticks[0])}</span><span>{clock(ticks.at(-1))}</span></div>
    {jumps.length > 0 && <div className="event-jumps"><strong>Synthetic event jumps</strong>{jumps.map((jump) => <button type="button" key={jump.label} onClick={() => { setPlaying(false); setIndex(Math.max(0, ticks.indexOf(jump.tick))); onJump(jump) }}>{jump.label}</button>)}</div>}
    <p className="calibration">{report.replay.calibrated ? 'Original ten-day baseline calibrated.' : `Baseline values withheld until ${clock(report.replay.calibration_complete_at)}.`}</p>
  </section>
}

function CurrentStatus({ report }) {
  return <section className="panel status-panel" aria-labelledby="current-status-heading"><div className="panel-title"><div><h3 id="current-status-heading">Current station status</h3><p>Latest counts at or before the replay clock; old readings are marked stale.</p></div><span>{report.replay.observed_station_count} / {report.replay.station_count} observed</span></div><div className="status-grid">{report.current_station_status.map((row) => <div className="status-row" key={row.station_id}><strong>{row.station_id}</strong><span className={row.missing ? 'badge neutral' : row.stale ? 'badge caution' : row.unusable ? 'badge bad' : 'badge'}>{row.missing ? 'Missing' : row.stale ? 'Stale' : row.unusable ? 'Unusable' : 'Usable'}</span><span>Bikes <b>{row.num_bikes_available ?? '—'}</b> · Broken <b>{row.num_bikes_disabled ?? '—'}</b> · Docks <b>{row.num_docks_available ?? '—'}</b></span><small>{row.missing ? 'No observation yet' : `${clock(row.observed_at)} · ${row.age_minutes} min old`}</small></div>)}</div></section>
}

function Availability({ report, windowName, setWindowName, stationId, setStationId }) {
  const section = report.availability[windowName]
  const stations = Object.keys(section.charts)
  const chosen = stations.includes(stationId) ? stationId : stations[0]
  const chart = section.charts[chosen]
  return <section aria-labelledby="availability-heading">
    <div className="section-heading"><div><p className="eyebrow">01 / Availability</p><h2 id="availability-heading">Rush dispatch</h2><p>Latest observed day: <strong>{report.availability.latest_date ?? 'none'}</strong>. Work down the list; red signals deserve investigation.</p></div>
      <fieldset className="segmented"><legend>Rush window</legend>{['AM', 'PM'].map((value) => <label key={value}><input type="radio" name="rush" checked={windowName === value} onChange={() => setWindowName(value)} /><span>{value} · {value === 'AM' ? '07–09' : '16–18'}</span></label>)}</fieldset></div>
    <Verdict verdict={availabilityVerdict(section, windowName)} />
    {section.provisional && <p className="provisional-note">{windowName} rush is provisional. Counts are visible; final signals and dispatch verdicts are withheld until the window closes.</p>}
    <div className="panel"><div className="panel-title"><h3>{windowName} dispatch</h3><span>{section.stations.length} stations</span></div><div className="table-wrap"><table><thead><tr><th scope="col">Station</th><th scope="col">Unusable</th><th scope="col">Empty / full</th><th scope="col">Baseline</th><th scope="col">UCL</th><th scope="col">Signal</th><th scope="col">Typical onset</th><th scope="col">Action</th></tr></thead><tbody>
      {section.stations.map((row) => <tr key={row.station_id} className={signal(row) ? 'signal-row' : ''}><th scope="row">{row.station_id}</th><td>{percent(row.p)} <small>({row.d}/{row.n}){row.provisional ? ` of ${row.expected_snapshots} expected` : ''}</small></td><td>{row.empty_count} / {row.full_count}</td><td>{percent(row.p_bar)}</td><td>{percent(row.ucl)}</td><td><span className={signal(row) ? 'badge bad' : row.provisional ? 'badge caution' : 'badge'}>{row.provisional ? 'Provisional' : signal(row) ? 'Out of control' : row.status === 'insufficient_basis' ? 'No limits' : row.status === 'no_data' ? 'No data' : 'In control'}</span></td><td>{row.typical_first_unusable ?? '—'}</td><td>{row.action}</td></tr>)}
    </tbody></table></div></div>
    <div className="panel chart-panel"><div className="panel-title"><div><h3>Station p-chart</h3><p>One point per weekday; exact limits vary with observed snapshot count.</p></div><label className="station-select">Station<select value={chosen ?? ''} onChange={(event) => setStationId(event.target.value)}>{stations.map((station) => <option key={station} value={station}>{station}</option>)}</select></label></div>
      {chart && <><Chart points={chart.points} center={chart.p_bar} target={report.availability.target} title={`${chosen} ${windowName} availability`} /><div className="onset"><span>Typically empty: <strong>{chart.onset.empty.label ?? 'never observed'}</strong></span><span>Typically full: <strong>{chart.onset.full.label ?? 'never observed'}</strong></span></div><Warnings items={chart.warnings} /></>}
    </div>
  </section>
}

function Maintenance({ report }) {
  const { chart, stations, warnings, as_of_date } = report.maintenance
  return <section aria-labelledby="maintenance-heading"><div className="section-heading"><div><p className="eyebrow">02 / Maintenance</p><h2 id="maintenance-heading">Broken bikes</h2><p>Network measurement at exactly 07:00 on each weekday. A red point means more broken bikes than the baseline predicts.</p></div></div>
    <Verdict verdict={maintenanceVerdict(report.maintenance)} />
    <div className="panel chart-panel"><div className="panel-title"><h3>Network p-chart</h3><span>Latest 07:00: {as_of_date ?? 'none'}</span></div><Chart points={chart.points} center={chart.p_bar} title="Network broken-bike share" /><Warnings items={warnings} /></div>
    <div className="panel"><div className="panel-title"><h3>Inspect and collect</h3><span>{stations.length} stations</span></div>{stations.length ? <div className="table-wrap"><table><thead><tr><th scope="col">Station</th><th scope="col">Broken bikes</th><th scope="col">Action</th></tr></thead><tbody>{stations.map((row) => <tr key={row.station_id}><th scope="row">{row.station_id}</th><td>{row.num_bikes_disabled}</td><td>{row.action}</td></tr>)}</tbody></table></div> : <p className="empty">No broken bikes recorded at the latest 07:00 snapshot.</p>}</div>
  </section>
}

export default function App() {
  const [datasets, setDatasets] = useState([])
  const [dataset, setDataset] = useState('stable')
  const [report, setReport] = useState(null)
  const [tab, setTab] = useState('availability')
  const [windowName, setWindowName] = useState('AM')
  const [stationId, setStationId] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [ticks, setTicks] = useState([])
  const [index, setIndex] = useState(null)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(400)
  const asOf = index == null ? null : ticks[index]
  useEffect(() => { getDatasets().then((data) => setDatasets(data.datasets)).catch((cause) => setError(cause.message)) }, [])
  useEffect(() => {
    const controller = new AbortController()
    setPlaying(false); setIndex(null); setTicks([]); setReport(null); setLoading(true); setError('')
    setWindowName('AM'); setStationId('')
    getReplayClock(dataset, controller.signal).then((data) => {
      const available = replayTicks(data.first_timestamp, data.last_timestamp)
      setTicks(available)
      setIndex(initialReplayIndex(available, data.default_as_of))
    }).catch((cause) => { if (cause.name !== 'AbortError') { setError(cause.message); setLoading(false) } })
    return () => controller.abort()
  }, [dataset])
  useEffect(() => {
    if (index == null) return undefined
    const controller = new AbortController()
    setLoading(true)
    setError('')
    getReport(dataset, asOf, controller.signal).then(setReport).catch((cause) => { if (cause.name !== 'AbortError') setError(cause.message) }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [dataset, asOf])
  useEffect(() => {
    if (!playing || loading || index == null || !ticks.length) return undefined
    if (index >= ticks.length - 1) { setPlaying(false); return undefined }
    const timer = window.setTimeout(() => setIndex(index + 1), speed)
    return () => window.clearTimeout(timer)
  }, [playing, loading, index, speed, ticks.length])
  const jumpTo = (jump) => {
    setTab(jump.tab)
    if (jump.windowName) setWindowName(jump.windowName)
    if (jump.stationId) setStationId(jump.stationId)
    window.requestAnimationFrame(() => document.querySelector('.tabs')?.scrollIntoView({ block: 'start' }))
  }
  return <main><header className="hero"><div className="hero-inner"><div><p className="eyebrow">Team Six / Urban systems</p><h1>Bikeshare fleet<br /><em>quality control</em></h1><p className="intro">A dispatch view for rush-hour availability and morning maintenance.</p></div><div className="hero-aside"><span className="hero-number">10</span><span>baseline weekdays<br />exact binomial limits</span></div></div></header>
    <div className="content"><div className="disclaimer" role="note"><strong>Synthetic demonstration data</strong><span>Control-chart signals are exploratory. Consecutive station snapshots are dependent.</span></div>
      <div className="toolbar"><label>Scenario<select value={dataset} onChange={(event) => setDataset(event.target.value)}>{(datasets.length ? datasets : ['stable', 'planted_events', 'edge_case']).map((item) => <option key={item} value={item}>{pretty(item)}</option>)}</select></label><span className="source">Bundled CSV · no live feed</span></div>
      {report && ticks.length > 0 && <Replay report={report} ticks={ticks} index={index ?? ticks.length - 1} setIndex={setIndex} playing={playing} setPlaying={setPlaying} speed={speed} setSpeed={setSpeed} dataset={dataset} onJump={jumpTo} />}
      <nav className="tabs" aria-label="Report section"><button type="button" className={tab === 'availability' ? 'active' : ''} aria-current={tab === 'availability' ? 'page' : undefined} onClick={() => setTab('availability')}>Availability</button><button type="button" className={tab === 'maintenance' ? 'active' : ''} aria-current={tab === 'maintenance' ? 'page' : undefined} onClick={() => setTab('maintenance')}>Maintenance</button></nav>
      {error && <p className="error" role="alert">Unable to load report: {error}</p>}
      {loading && !report && <p className="loading" role="status">Loading {pretty(dataset)} report…</p>}
      {report && <div className="report" aria-busy={loading}>
        {tab === 'availability'
          ? <Availability report={report} windowName={windowName} setWindowName={setWindowName} stationId={stationId} setStationId={setStationId} />
          : <Maintenance report={report} />}
        <CurrentStatus report={report} />
      </div>}
      {report && <footer><Warnings items={report.warnings} /><p>All observations are invented for this demonstration. Limits are calculated by the FastAPI report.</p></footer>}
    </div>
  </main>
}
