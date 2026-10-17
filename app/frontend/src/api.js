// Relative URLs work under Posit Connect content paths as well as at the origin root.
async function request(path, signal) {
  const response = await fetch(new URL(path, document.baseURI), { signal })
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try { message = (await response.json()).detail ?? message } catch { /* plain response */ }
    throw new Error(message)
  }
  return response.json()
}

export const getDatasets = () => request('api/datasets')
export const getReplayClock = (dataset, signal) =>
  request(`api/replay-clock?dataset=${encodeURIComponent(dataset)}`, signal)
export const getReport = (dataset, asOf, signal) =>
  request(`api/report?dataset=${encodeURIComponent(dataset)}${asOf ? `&as_of=${encodeURIComponent(asOf)}` : ''}`, signal)
