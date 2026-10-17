import { describe, expect, it } from 'vitest'
import { availabilityVerdict, chartPath, eventJumps, initialReplayIndex, maintenanceVerdict, replayTicks } from './App.jsx'

describe('replay navigation', () => {
  it('includes both rush closing boundaries and skips the overnight period', () => {
    const ticks = replayTicks('2026-10-19T07:00', '2026-10-19T17:55')
    expect(ticks[0]).toBe('2026-10-19T07:00')
    expect(ticks).toContain('2026-10-19T09:00')
    expect(ticks).toContain('2026-10-19T18:00')
    expect(ticks).not.toContain('2026-10-19T12:00')
  })
  it('begins paused at the original tenth baseline day close', () => {
    const ticks = replayTicks('2026-10-05T07:00', '2026-10-23T17:55')
    const baseline = ticks.filter((tick) => tick.endsWith('T07:00')).slice(0, 10).map((tick) => tick.slice(0, 10))
    const defaultAsOf = `${baseline[9]}T18:00`
    expect(ticks[initialReplayIndex(ticks, defaultAsOf)]).toBe(defaultAsOf)
  })
})

describe('chart paths', () => {
  const x = (index) => index * 10
  const y = (value) => value * 100
  it('breaks across null observations rather than plotting a zero or connecting a gap', () => {
    expect(chartPath([{ p: .2 }, { p: null }, { p: .4 }], 'p', x, y)).toBe('M0 20 M20 40')
  })
  it('joins consecutive varying exact limits with a horizontal then vertical step', () => {
    expect(chartPath([{ ucl: .3 }, { ucl: .4 }, { ucl: .4 }], 'ucl', x, y, true)).toBe('M0 30 H10 V40 H20 V40')
  })
})

describe('event jumps', () => {
  it('open the window, station and tab where each planted event shows', () => {
    const ticks = replayTicks('2026-10-05T07:00', '2026-10-23T17:55')
    const [stadium, broken] = eventJumps('planted_events', ticks)
    expect(stadium).toMatchObject({ tick: '2026-10-20T18:00', tab: 'availability', windowName: 'PM', stationId: 'stadium_01' })
    expect(broken).toMatchObject({ tick: '2026-10-21T07:00', tab: 'maintenance' })
    expect(ticks).toContain(stadium.tick)
    expect(eventJumps('stable', ticks)).toEqual([])
  })
})

describe('verdict lines', () => {
  const row = (station_id, action, extra = {}) => ({ station_id, action, status: 'in_control', ...extra })
  it('names out-of-control stations and counts actions from backend fields', () => {
    const section = { provisional: false, stations: [
      row('a', 'van: drop bikes before 07:40'), row('b', 'van: drop bikes before 07:50'),
      row('c', 'collect broken bikes first', { flagged_high: true }), row('d', 'capacity review: unusable every day'),
    ] }
    expect(availabilityVerdict(section, 'PM')).toEqual({ tone: 'bad', headline: '1 station out of control: c', details: ['2 van drops', '1 broken-bike pickup', '1 capacity review'] })
  })
  it('withholds the verdict while the rush window is open', () => {
    expect(availabilityVerdict({ provisional: true, stations: [] }, 'AM').headline).toBe('AM rush in progress')
  })
  it('reads the latest maintenance point and never invents limits', () => {
    const maintenance = (point) => ({ chart: { points: [{ p: 0.05, d: 20, n: 400, ucl: 0.085, date: 'x' }, point] }, stations: [{ station_id: 's1' }] })
    expect(maintenanceVerdict(maintenance({ p: 0.1, d: 40, n: 400, ucl: 0.085, flagged_high: true, date: '2026-10-21' })).headline)
      .toBe('Above normal: 10.0% broken (40/400) on 2026-10-21, UCL 8.5%')
    expect(maintenanceVerdict(maintenance({ p: 0.05, d: 20, n: 400, ucl: null, date: '2026-10-05' })).headline).toMatch(/^No limits yet/)
    expect(maintenanceVerdict(maintenance({ p: null, date: '2026-10-22' })).headline).toMatch(/^Within normal: 5.0%/)
  })
})
