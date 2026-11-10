import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { api } from '@/lib/api'
import { useLive } from '@/stores/live'

// Issue #23: a full snapshot that resolves after newer stream updates must not overwrite them.

type OverviewResult = Awaited<ReturnType<typeof api.overview>>

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

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((yes) => { resolve = yes })
  return { promise, resolve }
}

const NOW_S = Math.floor(Date.now() / 1000)
const SNAPSHOT_SUMMARY_AT = 100
const STREAM_SUMMARY_AT = 200

const deviceA = { id: 'a', name: 'Miner A' }
const deviceB = { id: 'b', name: 'Miner B' }
const oldEvent = { id: 1, ts: NOW_S - 120, type: 'info', severity: 'info', device_id: null, title: 'old', body: null, data: {}, dedupe_key: null, ack_ts: null }
const newEvent = { id: 2, ts: NOW_S, type: 'device_offline', severity: 'critical', device_id: 'b', title: 'new', body: null, data: {}, dedupe_key: null, ack_ts: null }
const newAlert = { key: 'offline:b', severity: 'critical' }

function staleOverview(): OverviewResult {
  return {
    summary: { updated_at: SNAPSHOT_SUMMARY_AT },
    odds: null,
    network: {},
    alerts: [],
    events: [oldEvent],
    blocks_found: [],
    leaderboard: [],
  } as never
}

function startLive() {
  const live = useLive()
  live.start()
  const source = FakeEventSource.instances[0]!
  source.push('hello', {})
  return { live, source }
}

function deliverNewerStreamUpdates(source: FakeEventSource): void {
  source.push('device_removed', { id: 'b' })
  source.push('alerts', { active: [newAlert] })
  source.push('fleet', { updated_at: STREAM_SUMMARY_AT })
  source.push('event', newEvent)
}

describe('issue 23: stale full snapshot versus newer live updates', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
    vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
    vi.spyOn(api, 'devices').mockResolvedValue([deviceA, deviceB] as never)
    vi.spyOn(api, 'pool').mockResolvedValue({ pools: [] })
    vi.spyOn(api, 'recentBlocks').mockResolvedValue([])
  })

  afterEach(() => {
    useLive().stop()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  function expectNewerStateKept(live: ReturnType<typeof useLive>): void {
    expect(Object.keys(live.devicesById)).toEqual(['a'])
    expect(live.alerts.map((a) => a.key)).toEqual(['offline:b'])
    expect(live.summary?.updated_at).toBe(STREAM_SUMMARY_AT)
    expect(live.events.map((e) => e.id)).toEqual([2, 1])
  }

  it('keeps stream updates that arrive while the initial snapshot is loading', async () => {
    const snapshot = deferred<OverviewResult>()
    vi.spyOn(api, 'overview').mockReturnValue(snapshot.promise)
    const { live, source } = startLive()

    deliverNewerStreamUpdates(source)
    snapshot.resolve(staleOverview())
    await flushPromises()

    expect(live.loaded).toBe(true)
    expectNewerStateKept(live)
  })

  it('keeps stream updates that arrive while a reconnect snapshot is loading', async () => {
    const snapshot = deferred<OverviewResult>()
    vi.spyOn(api, 'overview')
      .mockResolvedValueOnce(staleOverview())
      .mockReturnValueOnce(snapshot.promise)
    const { live, source } = startLive()
    await flushPromises()
    expect(live.loaded).toBe(true)

    source.push('hello', {}) // reconnect: the stream asks the store to reload everything
    deliverNewerStreamUpdates(source)
    snapshot.resolve(staleOverview())
    await flushPromises()

    expectNewerStateKept(live)
  })

  it('still ends a logout epoch cleanly when the snapshot resolves after stop', async () => {
    const snapshot = deferred<OverviewResult>()
    vi.spyOn(api, 'overview').mockReturnValue(snapshot.promise)
    const { live, source } = startLive()

    deliverNewerStreamUpdates(source)
    live.stop()
    snapshot.resolve(staleOverview())
    await flushPromises()

    expect(live.loaded).toBe(false)
    expect(live.devices).toEqual([])
    expect(live.alerts).toEqual([])
    expect(live.events).toEqual([])
    expect(live.summary).toBeNull()
  })
})
