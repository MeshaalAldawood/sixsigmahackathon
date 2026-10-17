import { useEffect, useState } from 'react'
import { getReport, listDatasets } from './api.js'
import PChart from './PChart.jsx'

// The service-level target from SPEC.md (the backend's default). It is drawn as a reference
// line only; it is not a control limit and no decision on this page is computed from it.
const TARGET = 0.1

const pct = (x) => (x === null || x === undefined ? '—' : `${(100 * x).toFixed(1)}%`)
const STATUS_TEXT = { ok: 'within limits', no_data: 'no data', insufficient_basis: 'no limits (insufficient basis)' }

function Warnings({ items }) {
  if (!items || !items.length) return null
  return (
    <ul className="warnings">
      {items.map((w) => <li key={w}>{w}</li>)}
    </ul>
  )
}

function DispatchTable({ rows, selected, onSelect }) {
  return (
    <div className="table-wrap">
      <table className="dispatch">
        <thead>
          <tr>
            <th>Station</th>
            <th>Unusable</th>
            <th>Empty / full</th>
            <th>p̄</th>
            <th>UCL</th>
            <th>Today</th>
            <th>Typical onset</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            // Show whichever onset this station actually has in its baseline (both come from the backend).
            const onset = r.full_onset.affected_days > r.empty_onset.affected_days ? r.full_onset : r.empty_onset
            return (
              <tr
                key={r.station_id}
                className={`${r.flagged_high ? 'flag' : ''} ${r.station_id === selected ? 'selected' : ''}`}
                onClick={() => onSelect(r.station_id)}
              >
                <td><button type="button" className="linkish" onClick={() => onSelect(r.station_id)}>{r.station_id}</button></td>
                <td className="num">{r.n ? `${r.d}/${r.n} (${pct(r.p)})` : '—'}</td>
                <td className="num">{r.empty_count} / {r.full_count}</td>
                <td className="num">{pct(r.p_bar)}</td>
                <td className="num">{pct(r.ucl)}</td>
                <td>{r.flagged_high ? 'ABOVE UCL' : r.flagged_low ? 'below LCL' : STATUS_TEXT[r.status]}</td>
                <td className="small">{onset.text}</td>
                <td className={r.action_rank === 0 ? 'action' : 'small'}>{r.action}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function Availability({ data, baselineCount }) {
  const [win, setWin] = useState('AM')
  const rows = data[win].stations
  const [station, setStation] = useState(rows[0]?.station_id)
  const chart = data[win].charts[station] ?? data[win].charts[rows[0]?.station_id]
  const stationId = data[win].charts[station] ? station : rows[0]?.station_id

  return (
    <section aria-label="Availability">
      <div className="row">
        <div className="toggle" role="group" aria-label="Rush window">
          {['AM', 'PM'].map((w) => (
            <button key={w} type="button" aria-pressed={win === w} className={win === w ? 'on' : ''} onClick={() => setWin(w)}>
              {w === 'AM' ? 'AM rush 07:00–09:00' : 'PM rush 16:00–18:00'}
            </button>
          ))}
        </div>
      </div>
      <h2>Dispatch table, {rows[0]?.date} ({win})</h2>
      <p className="howto">
        How to read it: work from the top. Red rows are above their upper control limit today (a special cause:
        investigate). “Capacity review” means the station is in control but unusable more than the 10% target every
        day, which a van will not fix. Click a station to see its chart.
      </p>
      <Warnings items={data[win].warnings} />
      <DispatchTable rows={rows} selected={stationId} onSelect={setStation} />

      {chart && (
        <>
          <h2>
            <label htmlFor="station">Station chart </label>
            <select id="station" value={stationId} onChange={(e) => setStation(e.target.value)}>
              {Object.keys(data[win].charts).sort().map((s) => <option key={s}>{s}</option>)}
            </select>{' '}
            ({win}): share of snapshots unusable per weekday
          </h2>
          <PChart
            points={chart.points}
            pBar={chart.p_bar}
            target={TARGET}
            baselineCount={baselineCount}
            title={`${stationId} ${win} availability p-chart`}
            unitLabel="snapshots unusable"
          />
          <p className="howto">
            How to read it: a red point is a one-off to investigate; points inside the limits but above the target line
            mean a built-in problem that vans will not fix. Limits come from the first {baselineCount} weekdays only.
          </p>
          <Warnings items={chart.warnings} />
        </>
      )}
    </section>
  )
}

function Maintenance({ data, baselineCount, latestDate }) {
  const { chart, stations, as_of_date: asOf, warnings } = data
  return (
    <section aria-label="Maintenance">
      <h2>Broken bikes in the network at 07:00</h2>
      <PChart
        points={chart.points}
        pBar={chart.p_bar}
        baselineCount={baselineCount}
        title="Network 07:00 broken-bike p-chart"
        unitLabel="docked bikes broken"
      />
      <p className="howto">
        How to read it: a red point above the upper limit means more bikes are broken than normal; one below the lower
        limit means fewer (a decrease). Each point is one weekday's 07:00 snapshot over all stations.
      </p>
      <Warnings items={chart.warnings} />
      <h2>Stations to inspect{asOf ? `, ${asOf} 07:00` : ''}</h2>
      {asOf && latestDate && asOf < latestDate && (
        <p className="error">This list is from {asOf}, older than the latest day {latestDate}.</p>
      )}
      <Warnings items={warnings} />
      {stations.length ? (
        <table className="dispatch narrow">
          <thead><tr><th>Station</th><th>Broken bikes</th><th>Action</th></tr></thead>
          <tbody>
            {stations.map((s) => (
              <tr key={s.station_id}><td>{s.station_id}</td><td className="num">{s.num_bikes_disabled}</td><td>{s.action}</td></tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="notice">No broken bikes reported at the latest 07:00 snapshot.</p>
      )}
    </section>
  )
}

export default function App() {
  const [datasets, setDatasets] = useState([])
  const [dataset, setDataset] = useState('')
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('availability')

  useEffect(() => {
    listDatasets()
      .then((r) => { setDatasets(r.datasets); setDataset(r.datasets[0]) })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!dataset) return
    setReport(null)
    setError('')
    getReport(dataset).then(setReport).catch((e) => setError(e.message))
  }, [dataset])

  const baselineCount = report?.meta.baseline_dates.length ?? 0

  return (
    <main>
      <header>
        <h1>Bikeshare dispatch</h1>
        <p className="banner" role="note">
          <strong>Synthetic demonstration data; control-chart signals are exploratory.</strong> Snapshots five minutes
          apart are not independent, so real false alarms are more frequent than the chart's nominal rate.
        </p>
        <label htmlFor="dataset">Dataset</label>
        <select id="dataset" value={dataset} onChange={(e) => setDataset(e.target.value)}>
          {datasets.map((d) => <option key={d}>{d}</option>)}
        </select>
        {report && (
          <p className="meta">
            Baseline {report.meta.baseline_dates[0]} to {report.meta.baseline_dates.at(-1)} ({baselineCount} weekdays);
            latest day {report.meta.latest_date}.
          </p>
        )}
        <Warnings items={report?.meta.warnings} />
      </header>

      {error && <p className="error" role="alert">{error}</p>}
      {!report && !error && <p className="notice">Loading…</p>}

      {report && (
        <>
          <nav className="tabs" role="tablist">
            {[['availability', 'Availability'], ['maintenance', 'Maintenance']].map(([key, text]) => (
              <button key={key} type="button" role="tab" aria-selected={tab === key} className={tab === key ? 'on' : ''} onClick={() => setTab(key)}>
                {text}
              </button>
            ))}
          </nav>
          {tab === 'availability' ? (
            <Availability key={report.dataset} data={report.availability} baselineCount={baselineCount} />
          ) : (
            <Maintenance data={report.maintenance} baselineCount={baselineCount} latestDate={report.meta.latest_date} />
          )}
        </>
      )}
    </main>
  )
}
