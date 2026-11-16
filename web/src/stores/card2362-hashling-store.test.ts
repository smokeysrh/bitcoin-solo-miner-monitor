import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { api } from '@/lib/api'
import { HASHLING_MOMENTS, fill } from '@/lib/hashlingText'
import type { ActiveAlert, AppEvent, DeviceView, Severity, Settings } from '@/lib/types'
import { HASHLING_TIMING, useHashling } from '@/stores/hashling'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

// Card #2362: the Hashling queue. Pop-ups come only from live events that happen while the page is open, each one
// once (also after a reload), storms become one pop-up, one is visible at a time, and the settings switch turns it all off.

const NOW_S = 1_700_000_000
const SEEN_KEY = 'bsmm.hashlingSeen'
let nextId = 1

function dev(id: string, name: string, over: Partial<DeviceView> = {}): DeviceView {
  return { id, name, status: 'online', hashrate_smooth_hs: 1e12, telemetry: null, ...over } as unknown as DeviceView
}
function ev(type: string, severity: Severity, over: Partial<AppEvent> = {}): AppEvent {
  return { id: nextId++, ts: NOW_S, type, severity, device_id: 'a', title: 'server title', body: null, data: {}, dedupe_key: null, ack_ts: null, ...over }
}
function alertOf(rule: string, over: Partial<ActiveAlert> = {}): ActiveAlert {
  return { key: `rule_${rule}:a`, rule_id: `rule_${rule}`, since: NOW_S, title: 'server title', body: null, device_id: 'a', severity: 'warning', ...over }
}
const NODE = { id: 'src1', kind: 'bitcoin_core', name: 'My node', ok: true, error: null, last_ok: NOW_S, last_poll: NOW_S, implicit: false }
const CONFIRMED_BLOCK = { height: 900_001, hash: 'cd'.repeat(32), source: 'chain' }

/** `popups` is the saved switch; 'absent' is a settings file saved before the switch existed. */
function boot(devices: DeviceView[] = [dev('a', 'Garage'), dev('b', 'Office'), dev('c', 'Rack')], popups: boolean | 'absent' = true) {
  setActivePinia(createPinia())
  useSession().state = 'ready'
  const settings = useSettings()
  settings.data = { ui: popups === 'absent' ? {} : { hashling_popups: popups } } as unknown as Settings
  const live = useLive()
  live.devicesById = Object.fromEntries(devices.map((d) => [d.id, d]))
  live.network = { sources: [NODE] } as never
  live.loaded = true
  return { live, settings, hashling: useHashling(), toasts: useToasts() }
}

/** Let one quiet coalescing window pass (counted from the last offer) so whatever was offered becomes visible. */
const settle = (): void => void vi.advanceTimersByTime(HASHLING_TIMING.coalesceMs + 1)

beforeEach(() => {
  localStorage.clear()
  nextId = 1
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
  vi.setSystemTime(new Date(NOW_S * 1000))
})
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('card 2362: which events become pop-ups', () => {
  it('shows the pose, title and line for the moment, with the miner named', () => {
    const { hashling } = boot()
    expect(hashling.offer(ev('device_offline', 'critical'))).toBe(true)
    settle()
    expect(hashling.items).toHaveLength(1)
    expect(hashling.current).toMatchObject({
      momentId: 'M02',
      pose: 'alert',
      tone: 'bad',
      title: HASHLING_MOMENTS.M02.title,
      line: fill(HASHLING_MOMENTS.M02.line, { miner: 'Garage' }),
    })
  })

  it.each([
    ['healthy: device_recovered', ev('device_recovered', 'success')],
    ['healthy: pool_restored', ev('pool_restored', 'success')],
    ['info: device_restarted', ev('device_restarted', 'info')],
    ['info: difficulty_adjusted', ev('difficulty_adjusted', 'info', { device_id: null })],
    ['an unknown event type', ev('something_new', 'critical')],
  ])('shows nothing for %s and leaves it to the toaster path (offer returns false)', (_name, event) => {
    const { hashling } = boot()
    expect(hashling.offer(event)).toBe(false)
    settle()
    expect(hashling.items).toEqual([])
  })

  it('a block_found event only pops up on the wall display; on the dashboard the celebration dialog carries it', () => {
    const block = ev('block_found', 'success', { device_id: null, data: CONFIRMED_BLOCK })
    const dashboard = boot()
    dashboard.hashling.surface = 'dashboard'
    expect(dashboard.hashling.offer(block)).toBe(true)
    settle()
    expect(dashboard.hashling.items).toEqual([])

    const wall = boot()
    wall.hashling.surface = 'wall'
    expect(wall.hashling.offer(ev('block_found', 'success', { device_id: null, data: CONFIRMED_BLOCK }))).toBe(true)
    settle()
    expect(wall.hashling.current).toMatchObject({ momentId: 'M13', pose: 'found-block', title: HASHLING_MOMENTS.M13.title, line: HASHLING_MOMENTS.M13.line })
  })

  it('a miner-reported block (no chain evidence) is never the found-block pose', () => {
    const { hashling } = boot()
    hashling.surface = 'wall'
    expect(hashling.offer(ev('block_found', 'success', { data: { source: 'device', blocks_found: 2 } }))).toBe(false)
    settle()
    expect(hashling.items).toEqual([])
  })

  it('an offline alert rule does not pop up a second time for a miner whose offline event already did', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_offline', 'critical'))
    settle()
    hashling.observeAlerts([alertOf('device_offline', { severity: 'critical' })])
    settle()
    expect(hashling.items).toHaveLength(1)
  })
})

describe('card 2362: once per event, also across reloads', () => {
  it('the same event offered twice shows once', () => {
    const { hashling } = boot()
    const e = ev('new_best_share', 'success')
    hashling.offer(e)
    hashling.offer({ ...e })
    settle()
    expect(hashling.items).toHaveLength(1)
  })

  it('a dismissed pop-up does not come back when the same event arrives again', () => {
    const { hashling } = boot()
    const e = ev('new_best_share', 'success')
    hashling.offer(e)
    settle()
    hashling.dismiss()
    expect(hashling.items).toEqual([])
    hashling.offer({ ...e })
    settle()
    expect(hashling.items).toEqual([])
  })

  it('remembers what it has shown across a reload (new app, same browser storage)', () => {
    const first = boot()
    const e = ev('device_offline', 'critical')
    first.hashling.offer(e)
    settle()
    expect(first.hashling.items).toHaveLength(1)

    const reloaded = boot()
    expect(reloaded.hashling.items).toEqual([])
    expect(reloaded.hashling.offer({ ...e })).toBe(true)
    settle()
    expect(reloaded.hashling.items).toEqual([])
    // a different event is still new
    reloaded.hashling.offer(ev('device_offline', 'critical', { device_id: 'b' }))
    settle()
    expect(reloaded.hashling.items).toHaveLength(1)
  })

  it('an event id the server reuses after a data reset is a new event (the time is part of the key)', () => {
    const first = boot()
    first.hashling.offer(ev('new_best_share', 'success', { id: 7, ts: NOW_S }))
    settle()
    const again = boot()
    again.hashling.offer(ev('new_best_share', 'success', { id: 7, ts: NOW_S + 30 }))
    settle()
    expect(again.hashling.items).toHaveLength(1)
  })

  it('keeps the memory in the bsmm.* storage and bounds it', () => {
    const { hashling } = boot()
    for (let i = 0; i < 300; i++) hashling.offer(ev('new_best_share', 'success', { id: 1000 + i }))
    settle()
    const stored = JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]') as string[]
    expect(Array.isArray(stored)).toBe(true)
    expect(stored.length).toBeGreaterThan(0)
    expect(stored.length).toBeLessThanOrEqual(200)
  })

  it('survives unreadable stored memory by starting empty', () => {
    localStorage.setItem(SEEN_KEY, '{not json')
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    const { hashling } = boot()
    hashling.offer(ev('new_best_share', 'success'))
    settle()
    expect(hashling.items).toHaveLength(1)
    expect(warn).toHaveBeenCalled()
  })
})

describe('card 2362: storms become one pop-up', () => {
  it('three miners going offline within a few seconds make one M02N naming them', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    vi.advanceTimersByTime(400)
    hashling.offer(ev('device_offline', 'critical', { device_id: 'b' }))
    vi.advanceTimersByTime(400)
    hashling.offer(ev('device_offline', 'critical', { device_id: 'c' }))
    settle()
    expect(hashling.items).toHaveLength(1)
    expect(hashling.current).toMatchObject({ momentId: 'M02N', title: HASHLING_MOMENTS.M02N.title })
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M02N.line, { count: 3, miners: 'Garage, Office, 1 more' }))
  })

  it('waits for the storm to end but never longer than the maximum wait', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_added', 'info', { device_id: 'a' }))
    for (let i = 0; i < 30; i++) {
      vi.advanceTimersByTime(HASHLING_TIMING.coalesceMs - 100)
      hashling.offer(ev('device_added', 'info', { device_id: i % 2 ? 'b' : 'c' }))
    }
    expect(hashling.items.length).toBeGreaterThan(0)
  })

  it('miners added in one scan make one M15N', () => {
    const { hashling } = boot()
    for (const id of ['a', 'b', 'c']) hashling.offer(ev('device_added', 'info', { device_id: id }))
    settle()
    expect(hashling.items).toHaveLength(1)
    expect(hashling.current).toMatchObject({ momentId: 'M15N', pose: 'celebrate' })
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M15N.line, { count: 3 }))
  })

  it('mixed warnings make one M1XN', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    hashling.offer(ev('pool_failover', 'warning', { device_id: 'b' }))
    hashling.observeAlerts([alertOf('temp_high', { key: 'rule_temp_high:c', device_id: 'c' })])
    settle()
    expect(hashling.items).toHaveLength(1)
    expect(hashling.current).toMatchObject({ momentId: 'M1XN', pose: 'alert', tone: 'bad' })
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M1XN.line, { count: 3 }))
  })

  it('a miner whose fallback pool also made it "need attention" gets one pop-up, the specific one', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_degraded', 'warning', { body: 'Mining on the fallback pool' }))
    hashling.offer(ev('pool_failover', 'warning'))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M08'])
  })
})

describe('card 2362: one at a time, with a short queue', () => {
  it('shows the first, reports how many wait, and moves on when it is dismissed', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.offer(ev('new_best_share', 'success', { device_id: 'b' }))
    settle()
    hashling.offer(ev('device_added', 'info', { device_id: 'c' }))
    settle()
    expect(hashling.current?.momentId).toBe('M02')
    expect(hashling.waiting).toBe(2)
    hashling.dismiss()
    expect(hashling.current?.momentId).toBe('M14')
    expect(hashling.waiting).toBe(1)
    hashling.dismiss()
    hashling.dismiss()
    expect(hashling.current).toBeNull()
    expect(hashling.waiting).toBe(0)
  })

  it('keeps the queue short and drops the oldest waiting pop-up first, never the visible one', () => {
    const { hashling } = boot()
    const first = ev('new_best_share', 'success', { device_id: 'a' })
    hashling.offer(first)
    for (let i = 0; i < 20; i++) hashling.offer(ev('new_best_share', 'success', { device_id: 'b' }))
    settle()
    expect(hashling.items).toHaveLength(HASHLING_TIMING.queueMax)
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M14.line, { miner: 'Garage' }))
  })

  it('dismisses itself after about 12 seconds', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_offline', 'critical'))
    settle()
    expect(hashling.current?.timeoutMs).toBe(12_000)
    vi.advanceTimersByTime(11_000)
    expect(hashling.items).toHaveLength(1)
    vi.advanceTimersByTime(1_500)
    expect(hashling.items).toEqual([])
  })

  it('a found block on the wall display stays for about 60 seconds', () => {
    const { hashling } = boot()
    hashling.surface = 'wall'
    hashling.offer(ev('block_found', 'success', { device_id: null, data: CONFIRMED_BLOCK }))
    settle()
    expect(hashling.current?.timeoutMs).toBe(60_000)
    vi.advanceTimersByTime(30_000)
    expect(hashling.items).toHaveLength(1)
    vi.advanceTimersByTime(31_000)
    expect(hashling.items).toEqual([])
  })

  it('stays while someone is reading it (hold) and restarts the full time when they let go', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_offline', 'critical'))
    settle()
    hashling.hold()
    vi.advanceTimersByTime(60_000)
    expect(hashling.items).toHaveLength(1)
    hashling.release()
    vi.advanceTimersByTime(11_000)
    expect(hashling.items).toHaveLength(1)
    vi.advanceTimersByTime(1_500)
    expect(hashling.items).toEqual([])
  })

  it('clear() drops what is waiting and visible, and stops the timers (sign-out)', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_offline', 'critical'))
    settle()
    hashling.offer(ev('new_best_share', 'success'))
    hashling.clear()
    settle()
    expect(hashling.items).toEqual([])
    expect(vi.getTimerCount()).toBe(0)
  })
})

describe('card 2362: every miner is hashing again (M17), once per outage', () => {
  it('replaces the single "back" pop-up when the outage is over and every miner hashes', () => {
    const { hashling, live } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office'), dev('c', 'Rack')])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    live.devicesById = { ...live.devicesById, a: dev('a', 'Garage') }
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M17'])
    expect(hashling.current).toMatchObject({ pose: 'thumbs-up', title: HASHLING_MOMENTS.M17.title, line: HASHLING_MOMENTS.M17.line })
  })

  it('judges the returning miner by its view when the window closes, so an update that arrives meanwhile counts', () => {
    const { hashling, live } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office')])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    live.devicesById = { ...live.devicesById, a: dev('a', 'Garage') }
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M17'])
  })

  // The server announces device_online on any offline to reachable change, even when the miner then reports paused or
  // not hashing. Only a miner that is online and hashing in its current view closes the outage.
  it.each([
    ['still offline in its view', { status: 'offline', hashrate_smooth_hs: null }],
    ['paused', { status: 'paused', hashrate_smooth_hs: null }],
    ['paused with a leftover hashrate', { status: 'paused', hashrate_smooth_hs: 1e12 }],
    ['degraded with a hashrate', { status: 'degraded', hashrate_smooth_hs: 1e12 }],
    ['online with zero hashrate', { status: 'online', hashrate_smooth_hs: 0 }],
    ['degraded with zero hashrate', { status: 'degraded', hashrate_smooth_hs: 0 }],
    ['online with no hashrate reading at all', { status: 'online', hashrate_smooth_hs: null, telemetry: null }],
    ['online with zero telemetry hashrate', { status: 'online', hashrate_smooth_hs: null, telemetry: { hashrate_hs: 0 } as never }],
  ] as Array<[string, Partial<DeviceView>]>)('a miner that returns %s does not close the outage: it is the plain "back" pop-up', (_name, view) => {
    const { hashling, live } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office'), dev('c', 'Rack')])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    live.devicesById = { ...live.devicesById, a: dev('a', 'Garage', view) }
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M16'])
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M16.line, { miner: 'Garage' }))
  })

  it('a miner that hashes only in its telemetry reading still counts as hashing', () => {
    const { hashling, live } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office')])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    live.devicesById = { ...live.devicesById, a: dev('a', 'Garage', { hashrate_smooth_hs: null, telemetry: { hashrate_hs: 9e11 } as never }) }
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M17'])
  })

  it('stays the plain "back" pop-up while another miner is paused or not hashing, even if the returning one hashes', () => {
    const { hashling, live } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office', { status: 'paused', hashrate_smooth_hs: null }), dev('c', 'Rack', { hashrate_smooth_hs: 0 })])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    live.devicesById = { ...live.devicesById, a: dev('a', 'Garage') }
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M16'])
  })

  it('a miner the user switched off is not part of the fleet that has to hash', () => {
    const { hashling, live } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office', { status: 'disabled', hashrate_smooth_hs: null }), dev('c', 'Rack')])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    live.devicesById = { ...live.devicesById, a: dev('a', 'Garage') }
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M17'])
  })

  it('is the plain "back" pop-up while another miner is still down', () => {
    const { hashling } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office', { status: 'offline', hashrate_smooth_hs: null }), dev('c', 'Rack')])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    hashling.offer(ev('device_offline', 'critical', { device_id: 'b' }))
    settle()
    hashling.dismiss()
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M16'])
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M16.line, { miner: 'Garage' }))
  })

  it('is the plain "back" pop-up when there was no outage to end', () => {
    const { hashling } = boot()
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M16'])
  })

  it('is shown once per outage, never as a permanent state', () => {
    const { hashling, live } = boot([dev('a', 'Garage', { status: 'offline', hashrate_smooth_hs: null }), dev('b', 'Office')])
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    live.devicesById = { ...live.devicesById, a: dev('a', 'Garage') }
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    hashling.dismiss()
    hashling.offer(ev('device_online', 'success', { device_id: 'a' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M16'])
  })
})

describe('card 2362: alerts that have no event of their own', () => {
  it('pops up for an alert that fires while the page is open, once', () => {
    const { hashling } = boot()
    const hot = alertOf('temp_high', { severity: 'critical' })
    hashling.observeAlerts([hot])
    settle()
    expect(hashling.current).toMatchObject({ momentId: 'M04', pose: 'alert', tone: 'bad', line: fill(HASHLING_MOMENTS.M04.line, { miner: 'Garage' }) })
    hashling.dismiss()
    hashling.observeAlerts([hot, { ...hot }]) // the server repeats the active list every few seconds
    settle()
    expect(hashling.items).toEqual([])
  })

  it('does not pop up for alerts that were already active when the page loaded', () => {
    const { hashling } = boot()
    const active = [alertOf('temp_high'), alertOf('fan_failure', { key: 'rule_fan_failure:b', device_id: 'b' })]
    hashling.seedAlerts(active)
    hashling.observeAlerts(active)
    settle()
    expect(hashling.items).toEqual([])
  })

  it('a problem that clears and comes back later is a new alert (it fires with a new start time)', () => {
    const { hashling } = boot()
    hashling.seedAlerts([alertOf('temp_high', { since: NOW_S - 3600 })])
    hashling.observeAlerts([alertOf('temp_high', { since: NOW_S })])
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M04'])
  })

  it('names the node or pool for node trouble (M09 by source id, M10 by the node)', () => {
    const { hashling } = boot()
    hashling.observeAlerts([alertOf('node_down', { key: 'rule_node_down:src1', device_id: null })])
    settle()
    expect(hashling.current?.momentId).toBe('M09')
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M09.line, { source: 'My node' }))
    hashling.dismiss()
    hashling.observeAlerts([alertOf('node_behind', { key: 'rule_node_behind:node', device_id: null })])
    settle()
    expect(hashling.current?.momentId).toBe('M10')
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M10.line, { source: 'My node' }))
  })

  it('shows the fleet alert without a miner name (M06)', () => {
    const { hashling } = boot()
    hashling.observeAlerts([alertOf('fleet_hashrate_drop', { key: 'rule_fleet_hashrate_drop:fleet', device_id: null })])
    settle()
    expect(hashling.current).toMatchObject({ momentId: 'M06', line: HASHLING_MOMENTS.M06.line })
  })

  it('shows nothing, and says so in the console, when a name it needs is unknown', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    const { hashling } = boot()
    hashling.observeAlerts([alertOf('temp_high', { key: 'rule_temp_high:gone', device_id: 'gone' })])
    settle()
    expect(hashling.items).toEqual([])
    expect(warn).toHaveBeenCalled()
  })
})

describe('card 2362: the settings switch', () => {
  it('is on unless it was switched off (settings saved before the switch existed count as on)', () => {
    expect(boot(undefined, 'absent').hashling.enabled).toBe(true)
    expect(boot(undefined, true).hashling.enabled).toBe(true)
    expect(boot(undefined, false).hashling.enabled).toBe(false)
  })

  it('off: events are not taken (so the toaster shows them as before), alerts and UI moments show nothing', () => {
    const { hashling } = boot(undefined, false)
    expect(hashling.offer(ev('device_offline', 'critical'))).toBe(false)
    hashling.observeAlerts([alertOf('temp_high')])
    expect(hashling.show('M23')).toBe(false)
    settle()
    expect(hashling.items).toEqual([])
  })

  it('switching it off stops what is queued from appearing', () => {
    const { hashling, settings } = boot()
    hashling.offer(ev('device_offline', 'critical'))
    settings.data = { ui: { hashling_popups: false } } as unknown as Settings
    settle()
    expect(hashling.items).toEqual([])
  })

  // The visible pop-up and the ones already waiting are on screen or in the queue when the switch is turned off.
  it.each<[string, 'dashboard' | 'wall']>([['the dashboard', 'dashboard'], ['the wall display', 'wall']])('switching it off hides the visible pop-up and the waiting ones at once on %s', (_name, surface) => {
    const { hashling, settings } = boot()
    hashling.surface = surface
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.offer(ev('new_best_share', 'success', { device_id: 'b' }))
    settle()
    hashling.show('M22')
    expect(hashling.current?.momentId).toBe('M02')
    expect(hashling.waiting).toBe(2)

    settings.data = { ui: { hashling_popups: false } } as unknown as Settings
    expect(hashling.enabled).toBe(false)
    expect(hashling.current).toBeNull()
    expect(hashling.waiting).toBe(0)
    expect(hashling.items).toEqual([])
    expect(vi.getTimerCount()).toBe(0)
  })

  it('while it is off nothing waiting appears later, not as time passes and not when the visible one would have ended', () => {
    const { hashling, settings } = boot()
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.offer(ev('new_best_share', 'success', { device_id: 'b' }))
    settle()
    settings.data = { ui: { hashling_popups: false } } as unknown as Settings
    vi.advanceTimersByTime(HASHLING_TIMING.popupMs * 3)
    expect(hashling.current).toBeNull()
    hashling.dismiss()
    expect(hashling.current).toBeNull()
    expect(hashling.items).toEqual([])
  })

  it('switching it back on starts clean: what was hidden does not return, and new moments show again', () => {
    const { hashling, settings } = boot()
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.show('M22')
    settings.data = { ui: { hashling_popups: false } } as unknown as Settings
    settings.data = { ui: { hashling_popups: true } } as unknown as Settings
    expect(hashling.items).toEqual([])
    hashling.offer(ev('new_best_share', 'success', { device_id: 'b' }))
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M14'])
  })

  it('a pop-up that is being read (held) goes with the switch, and the next one gets its full time', () => {
    const { hashling, settings } = boot()
    hashling.offer(ev('device_offline', 'critical', { device_id: 'a' }))
    settle()
    hashling.hold()
    settings.data = { ui: { hashling_popups: false } } as unknown as Settings
    settings.data = { ui: { hashling_popups: true } } as unknown as Settings
    hashling.show('M22')
    vi.advanceTimersByTime(HASHLING_TIMING.popupMs + 500)
    expect(hashling.items).toEqual([])
  })
})

describe('card 2362: moments the app itself decides (setup, notifications, checklist, pool change)', () => {
  it('shows a moment now, with its words and a thumbs-up for a success', () => {
    const { hashling } = boot()
    expect(hashling.show('M23')).toBe(true)
    expect(hashling.current).toMatchObject({ momentId: 'M23', pose: 'thumbs-up', tone: 'ok', title: HASHLING_MOMENTS.M23.title, line: HASHLING_MOMENTS.M23.line })
  })

  it('fills the miner name for the accepted pool change', () => {
    const { hashling } = boot()
    hashling.show('M24', { miner: 'Garage' })
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M24.line, { miner: 'Garage' }))
  })

  it('shows a once-only moment (the checklist) once, remembered across reloads', () => {
    const first = boot()
    expect(first.hashling.show('M21', {}, { once: 'checklist' })).toBe(true)
    expect(first.hashling.current).toMatchObject({ momentId: 'M21', pose: 'thumbs-up' })
    first.hashling.dismiss()
    first.hashling.show('M21', {}, { once: 'checklist' })
    expect(first.hashling.items).toEqual([])
    const reloaded = boot()
    reloaded.hashling.show('M21', {}, { once: 'checklist' })
    expect(reloaded.hashling.items).toEqual([])
  })
})

// ---------------------------------------------------------------------------------------------------- through the live stream

class FakeEventSource extends EventTarget {
  static instances: FakeEventSource[] = []
  readyState = 1
  onerror: (() => void) | null = null
  constructor() {
    super()
    FakeEventSource.instances.push(this)
  }
  close(): void {
    this.readyState = 2
  }
  push(topic: string, payload: unknown): void {
    this.dispatchEvent(new MessageEvent(topic, { data: JSON.stringify(payload) }))
  }
}

describe('card 2362: through the live stream', () => {
  const backfilled = ev('device_offline', 'critical', { id: 90, device_id: 'a', ts: NOW_S - 5 })

  async function startLive(alerts: ActiveAlert[], popups = true) {
    setActivePinia(createPinia())
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
    vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
    useSession().state = 'ready'
    useSettings().data = { ui: { hashling_popups: popups } } as unknown as Settings
    vi.spyOn(api, 'overview').mockResolvedValue({ summary: { updated_at: 1 }, odds: null, network: {}, alerts, events: [backfilled], blocks_found: [], leaderboard: [] } as never)
    vi.spyOn(api, 'devices').mockResolvedValue([dev('a', 'Garage'), dev('b', 'Office')])
    vi.spyOn(api, 'pool').mockResolvedValue({ pools: [] })
    vi.spyOn(api, 'recentBlocks').mockResolvedValue([])
    const live = useLive()
    live.start()
    const source = FakeEventSource.instances[0]!
    source.push('hello', {})
    await flushPromises()
    return { live, source, hashling: useHashling(), toasts: useToasts() }
  }

  it('does not pop up for history that arrives with the page (the loaded event list)', async () => {
    const { live, hashling } = await startLive([])
    expect(live.events.map((e) => e.id)).toEqual([90])
    settle()
    expect(hashling.items).toEqual([])
  })

  it('does not pop up for an old event the stream delivers late', async () => {
    const { source, hashling } = await startLive([])
    source.push('event', ev('device_offline', 'critical', { device_id: 'b', ts: NOW_S - 600 }))
    settle()
    expect(hashling.items).toEqual([])
  })

  it('pops up for a fresh event, and the toaster stays quiet for it', async () => {
    const { source, hashling, toasts } = await startLive([])
    source.push('event', ev('device_offline', 'critical', { device_id: 'b' }))
    settle()
    expect(hashling.current?.momentId).toBe('M02')
    expect(toasts.items).toEqual([])
  })

  it('with pop-ups off the same event reaches the toaster as before', async () => {
    const { source, hashling, toasts } = await startLive([], false)
    source.push('event', ev('device_offline', 'critical', { device_id: 'b', title: 'Office is offline' }))
    settle()
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.title)).toEqual(['Office is offline'])
  })

  it('healthy and info events stay on their old path: nothing from Hashling', async () => {
    const { source, hashling } = await startLive([])
    source.push('event', ev('device_restarted', 'info', { device_id: 'b' }))
    source.push('event', ev('difficulty_adjusted', 'info', { device_id: null }))
    settle()
    expect(hashling.items).toEqual([])
  })

  it('alerts active at load are history; one that fires afterwards pops up', async () => {
    const early = alertOf('temp_high', { key: 'rule_temp_high:a', device_id: 'a', since: NOW_S - 900 })
    const { source, hashling } = await startLive([early])
    source.push('alerts', { active: [early] })
    settle()
    expect(hashling.items).toEqual([])
    source.push('alerts', { active: [early, alertOf('fan_failure', { key: 'rule_fan_failure:b', device_id: 'b' })] })
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M03'])
    expect(hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M03.line, { miner: 'Office' }))
  })
})
