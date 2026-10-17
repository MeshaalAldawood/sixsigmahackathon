// The only place the page talks to the backend. URLs are RELATIVE ('api/...'), so the same
// build works at http://localhost:8000/ and under a Posit Connect content path.
// The backend computes every number; the page only displays what it returns.

async function getJson(path) {
  const res = await fetch(path, { headers: { Accept: 'application/json' } })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail ? `${res.status}: ${body.detail}` : `${path} returned HTTP ${res.status}`)
  return body
}

/** GET api/datasets -> {"datasets": ["stable.csv", ...]} */
export function listDatasets() {
  return getJson('api/datasets')
}

/** GET api/report?dataset=<name> -> {dataset, availability, maintenance, meta} */
export function getReport(name) {
  return getJson(`api/report?${new URLSearchParams({ dataset: name })}`)
}
