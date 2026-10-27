import { describe, expect, it } from 'vitest'
import * as f from './format'

// The expected strings are the same ones src/bsmm/units.py produces, so the UI, CLI and agents agree.
describe('hashrate', () => {
  it('picks the unit automatically', () => {
    expect(f.formatHashrate(4_726_646_000_000)).toBe('4.73 TH/s')
    expect(f.formatHashrate(1.2e9)).toBe('1.2 GH/s')
    expect(f.formatHashrate(950)).toBe('950 H/s')
    expect(f.formatHashrate(1.03e21)).toBe('1.03 ZH/s')
  })
  it('honours a fixed unit preference', () => {
    expect(f.formatHashrate(4.8e12, 'gh')).toBe('4800 GH/s')
    expect(f.formatHashrate(4.8e12, 'th')).toBe('4.8 TH/s')
  })
  it('shows a dash for missing values instead of NaN', () => {
    expect(f.formatHashrate(null)).toBe('–')
    expect(f.formatHashrate(Number.NaN)).toBe('–')
    expect(f.formatHashrate(undefined)).toBe('–')
  })
})

describe('numbers', () => {
  it('keeps significant digits without trailing zeros', () => {
    expect(f.sig(4.7, 3)).toBe('4.7')
    expect(f.sig(140.57, 3)).toBe('141')
    expect(f.sig(0, 3)).toBe('0')
  })
  it('formats difficulty with SI prefixes', () => {
    expect(f.formatDifficulty(3.49e9)).toBe('3.49 G')
    expect(f.formatDifficulty(140_577_680_051_919)).toBe('141 T')
  })
})

describe('durations', () => {
  it('uses the two largest units', () => {
    expect(f.formatDuration(90_061)).toBe('1d 1h')
    expect(f.formatDuration(125)).toBe('2m 5s')
    expect(f.formatDuration(0.2)).toBe('<1s')
  })
  it('drops trailing zero units', () => {
    expect(f.formatDuration(3600)).toBe('1h')
  })
  it('turns astronomically long waits into years', () => {
    expect(f.formatDuration(46_689_769_658)).toBe('1,480 years')
  })
})

describe('odds and percentages', () => {
  it('writes odds as "1 in N"', () => {
    expect(f.formatOdds(0.000582)).toBe('1 in 1,718')
    expect(f.formatOdds(0.5)).toBe('1 in 2.0')
    expect(f.formatOdds(1)).toBe('certain')
    expect(f.formatOdds(0)).toBe('–')
  })
  it('never prints a tiny chance as 0.00%', () => {
    expect(f.formatFraction(1.3e-8, 2)).toBe('1.3e-6%')
    expect(f.formatFraction(0.0123, 2)).toBe('1.23%')
    expect(f.formatFraction(0)).toBe('0%')
  })
})

describe('temperature, money, text', () => {
  it('converts to Fahrenheit for display only', () => {
    expect(f.formatTemp(100, 'f')).toBe('212°F')
    expect(f.formatTemp(54.26, 'c', 1)).toBe('54.3°C')
    expect(f.formatTemp(null)).toBe('–')
  })
  it('formats power and money', () => {
    expect(f.formatPower(18.17)).toBe('18.2 W')
    expect(f.formatPower(1500)).toBe('1.5 kW')
    expect(f.formatMoney(1234.5, 'USD')).toBe('$1,235')
    expect(f.formatMoney(0.12, 'USD')).toBe('$0.12')
  })
  it('shortens addresses without losing the ends', () => {
    expect(f.shortAddress('bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq')).toBe('bc1qar0s…f5mdq'.replace('f5mdq', 'wf5mdq'))
    expect(f.shortAddress('bc1qshort')).toBe('bc1qshort')
    expect(f.shortAddress(null)).toBe('–')
  })
  it('says how long ago something happened', () => {
    const now = 1_000_000
    expect(f.formatAgo(now - 2, now)).toBe('just now')
    expect(f.formatAgo(now - 90, now)).toBe('1m ago')
    expect(f.formatAgo(now - 7200, now)).toBe('2h ago')
    expect(f.formatAgo(null, now)).toBe('never')
  })
  it('classifies temperatures', () => {
    expect(f.tempLevel(60)).toBe('ok')
    expect(f.tempLevel(76)).toBe('warn')
    expect(f.tempLevel(90)).toBe('crit')
    expect(f.tempLevel(null)).toBe('none')
  })
})
