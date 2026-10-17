import { describe, expect, it } from 'vitest'
import { chartPath, initialReplayIndex, replayTicks } from './App.jsx'

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
