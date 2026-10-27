import { describe, expect, it, vi } from 'vitest'
import { csvEscape, toCsv } from './csv'
import { fuzzyScore, rank } from './fuzzy'
import { accentForeground, contrast, resolveTheme } from './theme'
import { backoffMs, LiveStream, parsePayload } from './stream'
import { DEFAULT_LAYOUT, resolveLayout, SIMPLE_LAYOUT, WIDGET_BY_ID } from '@/components/dashboard/registry'
import { mergeSettings } from '@/stores/settings'

describe('csv', () => {
  it('quotes commas, quotes and newlines', () => {
    expect(csvEscape('plain')).toBe('plain')
    expect(csvEscape('a,b')).toBe('"a,b"')
    expect(csvEscape('say "hi"')).toBe('"say ""hi"""')
    expect(csvEscape(null)).toBe('')
  })
  it('writes a header, ISO times and empty cells for gaps', () => {
    const out = toCsv([0, 60], [{ name: 'Hashrate, TH/s', data: [1.5, null] }])
    expect(out).toBe('time,"Hashrate, TH/s"\r\n1970-01-01T00:00:00.000Z,1.5\r\n1970-01-01T00:01:00.000Z,\r\n')
  })
})

describe('fuzzy search', () => {
  it('ranks word starts above scattered letters and rejects non-matches', () => {
    expect(fuzzyScore('odds', 'Odds & costs')).toBeGreaterThan(fuzzyScore('odds', 'Dashboard odds tips'))
    expect(fuzzyScore('xyz', 'Dashboard')).toBe(0)
    expect(fuzzyScore('', 'anything')).toBeGreaterThan(0)
  })
  it('needs every word to match', () => {
    expect(fuzzyScore('garage gamma', 'Garage Gamma bitaxe')).toBeGreaterThan(0)
    expect(fuzzyScore('garage zebra', 'Garage Gamma bitaxe')).toBe(0)
  })
  it('sorts results best first', () => {
    const r = rank(['Settings', 'Miners', 'Odds & costs'], 'mi', (s) => s)
    expect(r[0]!.item).toBe('Miners')
  })
})

describe('theme', () => {
  it('chooses readable text for any accent colour', () => {
    expect(accentForeground('#F7931A')).toBe('#1b1203') // bright orange gets dark text
    expect(accentForeground('#1d4ed8')).toBe('#ffffff') // deep blue gets white text
    for (const c of ['#F7931A', '#84CC16', '#06B6D4', '#A78BFA', '#F472B6', '#10B981']) {
      expect(contrast(c, accentForeground(c))).toBeGreaterThanOrEqual(4.5)
    }
  })
  it('resolves "system" from the device preference', () => {
    expect(resolveTheme('system', true)).toBe('light')
    expect(resolveTheme('system', false)).toBe('dark')
    expect(resolveTheme('amoled', true)).toBe('amoled')
  })
})

describe('live stream', () => {
  it('backs off politely and caps at about 30 seconds', () => {
    const none = () => 0
    expect([0, 1, 2, 3, 4, 5, 20].map((n) => backoffMs(n, none))).toEqual([1000, 2000, 4000, 8000, 15000, 30000, 30000])
    expect(backoffMs(0, () => 1)).toBe(1250)
  })
  it('survives malformed payloads', () => {
    expect(parsePayload('{"a":1}')).toEqual({ a: 1 })
    expect(parsePayload('not json')).toBeUndefined()
  })

  class FakeES {
    static all: FakeES[] = []
    readyState = 0
    onerror: (() => void) | null = null
    listeners = new Map<string, ((e: MessageEvent) => void)[]>()
    closed = false
    constructor(public url: string) {
      FakeES.all.push(this)
    }
    addEventListener(t: string, fn: (e: MessageEvent) => void) {
      this.listeners.set(t, [...(this.listeners.get(t) ?? []), fn])
    }
    emit(t: string, data = '{}') {
      for (const fn of this.listeners.get(t) ?? []) fn({ data } as MessageEvent)
    }
    close() {
      this.closed = true
    }
  }

  it('goes live on hello, delivers events, and resyncs after a reconnect', () => {
    vi.useFakeTimers()
    FakeES.all = []
    const seen: unknown[] = []
    const statuses: string[] = []
    let resyncs = 0
    const s = new LiveStream({ fleet: (x) => seen.push(x) }, { eventSourceFactory: (u) => new FakeES(u) as unknown as EventSource, onStatus: (x) => statuses.push(x), onResync: () => resyncs++ })
    s.start()
    const first = FakeES.all[0]!
    first.emit('hello')
    first.emit('fleet', '{"hashrate_hs":5}')
    first.emit('fleet', 'garbage') // ignored, must not throw
    expect(seen).toEqual([{ hashrate_hs: 5 }])
    expect(statuses).toEqual(['connecting', 'live'])
    expect(resyncs).toBe(0)

    first.readyState = 2 // the browser gave up (for example after a 401 or a restart)
    first.onerror?.()
    expect(first.closed).toBe(true)
    expect(s.status).toBe('reconnecting')
    vi.advanceTimersByTime(2000)
    expect(FakeES.all).toHaveLength(2)
    FakeES.all[1]!.emit('hello')
    expect(s.status).toBe('live')
    expect(resyncs).toBe(1) // missed events are refetched
    s.stop()
    vi.useRealTimers()
  })
})

describe('dashboard layout', () => {
  it('falls back to the default (or simple) layout when nothing is saved', () => {
    expect(resolveLayout(null, false)).toEqual(DEFAULT_LAYOUT)
    expect(resolveLayout(undefined, true)).toEqual(SIMPLE_LAYOUT)
  })
  it('drops widgets that no longer exist and collapses duplicates', () => {
    const out = resolveLayout({ version: 1, widgets: [{ id: 'hero', span: 8 }, { id: 'removed-in-v2', span: 4 }, { id: 'hero', span: 6 }, { id: 'odds', span: 4 }] }, false)
    expect(out.map((p) => p.id)).toEqual(['hero', 'odds'])
  })
  it('snaps an unsupported size back to the widget default', () => {
    const out = resolveLayout({ version: 1, widgets: [{ id: 'checklist', span: 3 }] }, false)
    expect(out[0]).toEqual({ id: 'checklist', span: WIDGET_BY_ID.checklist!.defaultSpan })
  })
  it('ignores a layout it does not understand', () => {
    expect(resolveLayout({ version: 2 } as never, false)).toEqual(DEFAULT_LAYOUT)
    expect(resolveLayout({ version: 1, widgets: 'nope' } as never, false)).toEqual(DEFAULT_LAYOUT)
  })
})

describe('settings merge (mirrors the server)', () => {
  it('merges nested sections but replaces opaque blobs whole', () => {
    const base = { energy: { price_per_kwh: 0.12, psu_overhead_pct: 10 }, ui: { theme: 'dark', dashboard: { version: 1, widgets: [{ id: 'a' }] } } }
    const out = mergeSettings(base, { energy: { price_per_kwh: 0.2 }, ui: { dashboard: null } })
    expect(out.energy).toEqual({ price_per_kwh: 0.2, psu_overhead_pct: 10 })
    expect(out.ui).toEqual({ theme: 'dark', dashboard: null })
  })
})
