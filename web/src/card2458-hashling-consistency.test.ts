import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent, h, nextTick, type Component, type PropType } from 'vue'
import { api } from '@/lib/api'
import { HASHLING_MOMENTS, fill } from '@/lib/hashlingText'
import type { StreamStatus } from '@/lib/stream'
import type { AppEvent, DeviceView, DiscoveryJob, Insight, Settings, Severity } from '@/lib/types'
import AddMinerDialog from '@/components/miners/AddMinerDialog.vue'
import ChecklistWidget from '@/components/dashboard/widgets/ChecklistWidget.vue'
import DiscoveryPanel from '@/components/miners/DiscoveryPanel.vue'
import { HASHLING_TIMING, useHashling } from '@/stores/hashling'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'
import { useUi } from '@/stores/ui'

// Card #2458: the secondary Hashling notifications stay consistent with the accepted #2362 behaviour.
//   G1 a miner that stops hashing without a new status event still gets its one Sleeping moment (and only that once);
//   G2 one add-miner action shows one success notice (Hashling's replaces the toast, as for M22);
//   G3 the checklist's once-only marker is never pushed out of the rolling memory;
//   G4 an insights answer asked for the empty fleet is never taken as current after the miner is re-added.

const NOW_S = 1_700_000_000
const SEEN_KEY = 'bsmm.hashlingSeen'
let nextId = 1

/** A miner's latest poll reading (`telemetry.hashrate_hs`): what "hashing" is judged by, not the smoothed value. */
const reading = (hs: number | null): DeviceView['telemetry'] => ({ hashrate_hs: hs }) as never
/** By default a healthy miner: online, with a positive current reading. */
function dev(id: string, name: string, over: Partial<DeviceView> = {}): DeviceView {
  return { id, name, status: 'online', status_reason: null, hashrate_smooth_hs: 1e12, telemetry: reading(1e12), tags: [], model: 'Bitaxe', model_override: null, host: '192.168.1.50', ...over } as unknown as DeviceView
}
function ev(type: string, severity: Severity, over: Partial<AppEvent> = {}): AppEvent {
  return { id: nextId++, ts: NOW_S, type, severity, device_id: 'a', title: 'server title', body: null, data: {}, dedupe_key: null, ack_ts: null, ...over }
}
const NODE = { id: 'src1', kind: 'bitcoin_core', name: 'My node', ok: true, error: null, last_ok: NOW_S, last_poll: NOW_S, implicit: false }
const deferred = <T>() => {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => { resolve = res })
  return { promise, resolve }
}

/** Everything these cases read; no backend, credentials or private data. `popups` is the saved switch. */
function boot(devices: DeviceView[] = [dev('a', 'Garage'), dev('b', 'Office')], popups = true, stream: StreamStatus = 'live') {
  setActivePinia(createPinia())
  const session = useSession()
  session.state = 'ready'
  session.me = { name: 'owner', scope: 'admin', via: 'token' }
  useSettings().data = {
    general: { onboarding_done: true },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    energy: { price_per_kwh: 0.12 },
    alerts: { quiet_hours: null, temp_warn_c: 75, temp_crit_c: 85 },
    ui: { view_miners: 'grid', hashling_popups: popups },
  } as unknown as Settings
  const live = useLive()
  live.devicesById = Object.fromEntries(devices.map((d) => [d.id, d]))
  live.network = { sources: [NODE] } as never
  live.loaded = true
  live.status = stream
  return { live, hashling: useHashling(), toasts: useToasts() }
}

/** Let one quiet coalescing window pass (counted from the last offer) so whatever was offered becomes visible. */
const settle = (): void => void vi.advanceTimersByTime(HASHLING_TIMING.coalesceMs + 1)
/** A device update from the stream: the whole new view replaces the old one. */
async function update(live: ReturnType<typeof useLive>, view: DeviceView): Promise<void> {
  live.devicesById = { ...live.devicesById, [view.id]: view }
  await nextTick()
}

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []
async function mountWithRouter(component: Component, stubs: Record<string, boolean | Component> = {}): Promise<Wrapper> {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(component, { attachTo: document.body, global: { plugins: [router], stubs } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  localStorage.clear()
  nextId = 1
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
  vi.setSystemTime(new Date(NOW_S * 1000))
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  document.body.innerHTML = ''
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

// ------------------------------------------------------------------------------------------------------------------ G1

describe('card 2458 G1: a miner that stops hashing without a new status event gets one Sleeping moment', () => {
  /** What the server sends for a miner that is already on the needs-attention list and then does no work. */
  const stopped = (over: Partial<DeviceView> = {}): DeviceView =>
    dev('a', 'Garage', { status: 'degraded', status_reason: 'Fan fault; Not hashing', hashrate_smooth_hs: 2e11, telemetry: reading(0), ...over })
  /** Already needs attention (a fan fault) but still does its work. */
  const attentionButHashing = (): DeviceView => dev('a', 'Garage', { status: 'degraded', status_reason: 'Fan fault', telemetry: reading(1e12) })

  it('shows M12 once for the transition, not again while it stays not hashing, and again for a later real transition', async () => {
    const { hashling, live } = boot([attentionButHashing(), dev('b', 'Office')])
    await update(live, stopped()) // degraded stays degraded: the server publishes no device_degraded event for this
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M12'])
    expect(hashling.current).toMatchObject({ pose: 'sleeping', tone: 'warn', title: HASHLING_MOMENTS.M12.title, line: fill(HASHLING_MOMENTS.M12.line, { miner: 'Garage' }) })
    hashling.dismiss()
    await update(live, stopped({ telemetry: reading(0), hashrate_smooth_hs: 1e11 })) // still not hashing
    await update(live, dev('b', 'Office', { hashrate_smooth_hs: 1.1e12 }))
    settle()
    vi.advanceTimersByTime(HASHLING_TIMING.maxWaitMs * 3)
    expect(hashling.items).toEqual([])
    await update(live, attentionButHashing()) // it starts hashing again...
    await update(live, stopped()) // ...and stops again: a new transition
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M12'])
  })

  it('a healthy miner that goes from hashing to not hashing is one moment, also with the status event for the same change (guard)', async () => {
    const viewFirst = boot([dev('a', 'Garage'), dev('b', 'Office')])
    await update(viewFirst.live, stopped())
    viewFirst.hashling.offer(ev('device_degraded', 'warning', { device_id: 'a', body: 'Fan fault; Not hashing' }))
    settle()
    expect(viewFirst.hashling.items.map((i) => i.momentId)).toEqual(['M12'])
    viewFirst.hashling.dismiss()
    vi.advanceTimersByTime(HASHLING_TIMING.maxWaitMs * 3)
    expect(viewFirst.hashling.items).toEqual([])

    localStorage.clear()
    const eventFirst = boot([dev('a', 'Garage'), dev('b', 'Office')])
    eventFirst.hashling.offer(ev('device_degraded', 'warning', { device_id: 'a', body: 'Fan fault; Not hashing' }))
    await update(eventFirst.live, stopped())
    settle()
    expect(eventFirst.hashling.items.map((i) => i.momentId)).toEqual(['M12'])
    eventFirst.hashling.dismiss()
    vi.advanceTimersByTime(HASHLING_TIMING.maxWaitMs * 3)
    expect(eventFirst.hashling.items).toEqual([])
  })

  it('no moment at load or for a full-load snapshot, also when the snapshot already shows a miner not hashing (guard)', async () => {
    const { hashling, live } = boot()
    vi.spyOn(api, 'overview').mockResolvedValue({ summary: { updated_at: 1 }, odds: null, network: {}, alerts: [], events: [], blocks_found: [], leaderboard: [] } as never)
    vi.spyOn(api, 'devices').mockResolvedValue([stopped(), dev('b', 'Office')])
    vi.spyOn(api, 'pool').mockResolvedValue({ pools: [] })
    vi.spyOn(api, 'recentBlocks').mockResolvedValue([])
    await live.reload()
    await flushPromises()
    settle()
    expect(live.devicesById.a?.status).toBe('degraded') // the snapshot really was applied
    expect(hashling.items).toEqual([])
    await update(live, stopped({ hashrate_smooth_hs: 1e11 })) // and it stays quiet while it stays not hashing
    settle()
    expect(hashling.items).toEqual([])
    await update(live, attentionButHashing())
    await update(live, stopped()) // the first real transition after the load is news
    settle()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M12'])
  })

  it('a miner that is only offline or paused, and a healthy screen, show no Sleeping moment (guard)', async () => {
    const { hashling, live } = boot()
    await update(live, dev('a', 'Garage', { status: 'paused', status_reason: 'Mining is paused on the device', hashrate_smooth_hs: null, telemetry: reading(0) }))
    await update(live, dev('b', 'Office', { status: 'offline', hashrate_smooth_hs: null, telemetry: null }))
    await update(live, dev('a', 'Garage', { hashrate_smooth_hs: 1.2e12 }))
    settle()
    expect(hashling.items).toEqual([])
  })
})

// ------------------------------------------------------------------------------------------------------------------ G2

describe('card 2458 G2: one add-miner action shows one success notice', () => {
  // The real dialog draws in a portal and the real segmented control is a radio group; these draw plainly so the test can reach them.
  const InlineDialog = defineComponent({
    name: 'Dialog',
    props: { open: Boolean, title: { type: String, default: '' } },
    setup: (props, { slots }) => () => (props.open ? h('div', { role: 'dialog' }, [slots.default?.()]) : null),
  })
  const PlainSegmented = defineComponent({
    name: 'Segmented',
    props: { modelValue: { type: String, default: '' }, options: { type: Array as PropType<Array<{ value: string; label: string }>>, default: () => [] } },
    emits: ['update:modelValue'],
    setup: (props, { emit }) => () => h('div', props.options.map((o) => h('button', { type: 'button', 'data-mode': o.value, onClick: () => emit('update:modelValue', o.value) }, o.label))),
  })

  /** Add one miner by address; resolves once the add has been answered. The server's `device_added` event is offered afterwards. */
  async function addByAddress(ctx: ReturnType<typeof boot>) {
    vi.spyOn(api, 'addDevice').mockResolvedValue({ device: dev('c', 'Rack'), created: true, note: null } as never)
    useUi().addMinerOpen = true
    const w = await mountWithRouter(AddMinerDialog, { Dialog: InlineDialog, Segmented: PlainSegmented, DiscoveryPanel: true, TagInput: true })
    await w.get('[data-mode="address"]').trigger('click')
    await w.get('[data-testid="add-host"]').setValue('192.168.1.50')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(api.addDevice).toHaveBeenCalledTimes(1)
    return ctx.hashling.offer(ev('device_added', 'info', { device_id: 'c' }))
  }

  it('adding by address shows Hashling\'s first-miner moment instead of the toast', async () => {
    const ctx = boot()
    expect(await addByAddress(ctx)).toBe(true)
    settle()
    expect(ctx.hashling.items.map((i) => i.momentId)).toEqual(['M15'])
    expect(ctx.hashling.current?.line).toBe(fill(HASHLING_MOMENTS.M15.line, { miner: 'Rack' }))
    expect(ctx.toasts.items).toEqual([])
  })

  it('with pop-ups off the ordinary toast is the only notice', async () => {
    const ctx = boot(undefined, false)
    expect(await addByAddress(ctx)).toBe(false)
    settle()
    expect(ctx.hashling.items).toEqual([])
    expect(ctx.toasts.items.map((t) => t.title)).toEqual(['Added Rack'])
  })

  it('while the live stream is not connected the moment cannot arrive, so the toast stays', async () => {
    const ctx = boot(undefined, true, 'reconnecting')
    await addByAddress(ctx)
    expect(ctx.toasts.items.map((t) => t.title)).toEqual(['Added Rack'])
  })

  it('a miner that was already monitored keeps its own notice (no Hashling moment exists for it)', async () => {
    const ctx = boot()
    vi.spyOn(api, 'addDevice').mockResolvedValue({ device: dev('a', 'Garage'), created: false, note: 'Garage is already being monitored.' } as never)
    useUi().addMinerOpen = true
    const w = await mountWithRouter(AddMinerDialog, { Dialog: InlineDialog, Segmented: PlainSegmented, DiscoveryPanel: true, TagInput: true })
    await w.get('[data-mode="address"]').trigger('click')
    await w.get('[data-testid="add-host"]').setValue('192.168.1.50')
    await w.get('form').trigger('submit')
    await flushPromises()
    settle()
    expect(ctx.toasts.items.map((t) => t.title)).toEqual(['Garage was already monitored'])
    expect(ctx.hashling.items).toEqual([])
  })

  describe('adopting scanned miners', () => {
    const found = (): DiscoveryJob['miners'] => [{ key: 'fixture-miner', host: '127.0.0.1', port: 80, driver: 'axeos', family: 'bitaxe', model: 'Fixture miner', mac: null, serial: null, firmware: null,
      hostname: null, identity: 'fixture-miner', hashrate_hs: null, evidence: [], already_added: null, duplicate_of: null }] as DiscoveryJob['miners']
    const job = (status: DiscoveryJob['status']): DiscoveryJob => ({ id: 'fixture-scan', cidrs: ['127.0.0.1/32'], status, phase: 'probing', started_at: 1,
      finished_at: status === 'running' ? null : 2, total_hosts: 1, scanned_hosts: 1, progress: 1, miners: found(), sources: [], error: null })

    async function adopt(ctx: ReturnType<typeof boot>) {
      vi.spyOn(api, 'suggestRanges').mockResolvedValue(['127.0.0.1/32'])
      vi.spyOn(api, 'startDiscovery').mockResolvedValue(job('running'))
      vi.spyOn(api, 'discovery').mockResolvedValue(job('finished'))
      vi.spyOn(api, 'adopt').mockResolvedValue({ added: [dev('c', 'Rack')], merged: [] })
      const w = await mountWithRouter(DiscoveryPanel)
      await w.get('[data-testid="start-scan"]').trigger('click')
      await flushPromises()
      await vi.advanceTimersByTimeAsync(1000) // the poll that finds the scan finished and picks the new miner
      await flushPromises()
      await w.get('[data-testid="adopt"]').trigger('click')
      await flushPromises()
      expect(api.adopt).toHaveBeenCalledTimes(1)
      return ctx.hashling.offer(ev('device_added', 'info', { device_id: 'c' }))
    }

    it('shows Hashling\'s moment instead of the "Added 1 miner" toast', async () => {
      const ctx = boot()
      expect(await adopt(ctx)).toBe(true)
      settle()
      expect(ctx.hashling.items.map((i) => i.momentId)).toEqual(['M15'])
      expect(ctx.toasts.items).toEqual([])
    })

    it('with pop-ups off the toast is the only notice', async () => {
      const ctx = boot(undefined, false)
      expect(await adopt(ctx)).toBe(false)
      settle()
      expect(ctx.hashling.items).toEqual([])
      expect(ctx.toasts.items.map((t) => t.title)).toEqual(['Added 1 miner'])
    })
  })
})

// ------------------------------------------------------------------------------------------------------------------ G3

describe('card 2458 G3: the checklist celebration stays once-only past the rolling memory', () => {
  const CAP_EXCEEDED = 250 // the rolling memory keeps 200

  it('does not show again after more than 200 later events, in the same session or after a reload', () => {
    const first = boot()
    expect(first.hashling.show('M21', {}, { once: 'checklist' })).toBe(true)
    expect(first.hashling.items.map((i) => i.momentId)).toEqual(['M21'])
    first.hashling.dismiss()
    for (let i = 0; i < CAP_EXCEEDED; i++) first.hashling.offer(ev('new_best_share', 'success', { id: 5000 + i, device_id: 'a' }))
    settle()
    first.hashling.clear()
    first.hashling.show('M21', {}, { once: 'checklist' })
    expect(first.hashling.items).toEqual([])
    expect(JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]') as string[]).toContain('ui:checklist')

    const reloaded = boot()
    reloaded.hashling.show('M21', {}, { once: 'checklist' })
    expect(reloaded.hashling.items).toEqual([])
  })

  it('the rolling memory of events and alerts itself stays bounded (guard)', () => {
    const { hashling } = boot()
    hashling.show('M21', {}, { once: 'checklist' })
    for (let i = 0; i < 300; i++) hashling.offer(ev('new_best_share', 'success', { id: 9000 + i }))
    settle()
    const stored = JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]') as string[]
    expect(stored.filter((k) => !k.startsWith('ui:')).length).toBeLessThanOrEqual(200)
    expect(stored.length).toBeLessThanOrEqual(201)
  })
})

// ------------------------------------------------------------------------------------------------------------------ G4

describe('card 2458 G4: a delayed insights answer after remove and re-add does not spend the checklist celebration', () => {
  const insight = (id: string): Insight => ({ id, level: 'tip', title: id, body: '', action: null, device_id: null })
  // What the server answers: with no miners only "no-miners"; with a miner, a reminder for every step still open.
  const NO_MINERS = [insight('no-miners')]
  const FIRST_MINER_REMINDERS = ['no-node', 'energy-default', 'no-channel', 'no-password'].map(insight)
  const spentMarker = (): boolean => (localStorage.getItem(SEEN_KEY) ?? '').includes('checklist')

  it('keeps the marker unspent for the stale empty-fleet answer, and still celebrates a genuine later completion once', async () => {
    const { live, hashling } = boot([dev('a', 'Garage')])
    const emptyFleet = deferred<Insight[]>()
    const reAdded = deferred<Insight[]>()
    const insights = vi.spyOn(api, 'insights')
      .mockResolvedValueOnce(FIRST_MINER_REMINDERS) // the page opens with one miner: one step of five is done
      .mockReturnValueOnce(emptyFleet.promise) // asked after the last miner was removed
      .mockReturnValue(reAdded.promise) // asked again once the miner is back
    await mountWithRouter(ChecklistWidget)
    expect(insights).toHaveBeenCalledTimes(1)

    live.devicesById = {} // the last miner is removed: the request for the empty fleet is now pending
    await flushPromises()
    expect(insights).toHaveBeenCalledTimes(2)
    live.devicesById = { a: dev('a', 'Garage') } // the miner is re-added: the same fleet size as before the removal
    await flushPromises()
    expect(hashling.items).toEqual([])

    emptyFleet.resolve(NO_MINERS) // the late answer for the empty fleet: no reminders at all
    await flushPromises()
    expect(hashling.items).toEqual([])
    expect(spentMarker()).toBe(false)

    reAdded.resolve(FIRST_MINER_REMINDERS) // the answer for the fleet that is on screen now
    await flushPromises()
    expect(hashling.items).toEqual([])
    expect(spentMarker()).toBe(false)

    insights.mockResolvedValueOnce([]) // the user then really finishes the list
    live.network = { sources: [NODE, { ...NODE, id: 'src2' }] } as never
    await flushPromises()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M21'])
    expect(spentMarker()).toBe(true)
  })
})
