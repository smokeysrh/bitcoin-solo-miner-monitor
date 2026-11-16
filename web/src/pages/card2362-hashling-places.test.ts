import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent, h, type Component } from 'vue'
import { api } from '@/lib/api'
import { HASHLING_ART } from '@/lib/brand'
import { HASHLING_MOMENTS, HASHLING_UI, fill } from '@/lib/hashlingText'
import type { Channel, DeviceView, Insight, Settings } from '@/lib/types'
import { poolChangeText } from '@/lib/poolChangeText'
import { useMinerMonitor } from '@/composables/useMinerMonitor'
import ChecklistWidget from '@/components/dashboard/widgets/ChecklistWidget.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import HashlingNote from '@/components/brand/HashlingNote.vue'
import MinersWidget from '@/components/dashboard/widgets/MinersWidget.vue'
import MinersPage from '@/pages/MinersPage.vue'
import NotificationsSettings from '@/pages/settings/NotificationsSettings.vue'
import SetupPage from '@/pages/SetupPage.vue'
import Switch from '@/components/ui/Switch.vue'
import { useHashling } from '@/stores/hashling'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

// Card #2362: the places where Hashling appears because of something the app itself decides: the setup page,
// the empty "No miners yet" screens, the finished getting-started checklist, notifications switched on and tested,
// an accepted pool change, and the one joke on the Odds page.

vi.mock('@/composables/useConfirm', () => ({ confirmDialog: vi.fn(async () => true), pendingConfirm: { value: null } }))

const dev = (id: string, name: string, over: Partial<DeviceView> = {}): DeviceView => ({ id, name, status: 'online', hashrate_smooth_hs: 1e12, telemetry: null, tags: [], ...over }) as unknown as DeviceView

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

function boot(popups: boolean | undefined = true) {
  setActivePinia(createPinia())
  const session = useSession()
  session.state = 'ready'
  session.me = { name: 'owner', scope: 'admin', via: 'token' }
  // Only what these pages read; no backend, credentials or private data.
  useSettings().data = {
    general: { onboarding_done: true },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    energy: { price_per_kwh: 0.12 },
    alerts: { quiet_hours: null, temp_warn_c: 75, temp_crit_c: 85 },
    ui: { view_miners: 'grid', ...(popups === undefined ? {} : { hashling_popups: popups }) },
  } as unknown as Settings
  const live = useLive()
  live.loaded = true
  return { live, hashling: useHashling(), toasts: useToasts() }
}
async function mountWithRouter(component: Component, stubs: Record<string, boolean | Component> = {}, props: Record<string, unknown> = {}): Promise<Wrapper> {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(component, { props: props as never, attachTo: document.body, global: { plugins: [router], stubs } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  document.body.innerHTML = ''
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('card 2362: the setup page (M18 welcome, M19 finished)', () => {
  const stubs = { DiscoveryPanel: true, Select: true }
  const press = async (w: Wrapper, text: string): Promise<void> => {
    const button = w.findAll('button').find((b) => b.text().includes(text))
    expect(button, `a "${text}" button`).toBeTruthy()
    await button!.trigger('click')
    await flushPromises()
  }

  it('welcomes with Hashling tinkering at his desk rig, in Becky\'s words', async () => {
    boot()
    const w = await mountWithRouter(SetupPage, stubs)
    const img = w.get(`img[src="${HASHLING_ART.tinkering}"]`)
    expect(img.attributes('alt')).toBe(HASHLING_UI.U01f)
    expect(w.text()).toContain(HASHLING_MOMENTS.M18.title)
    expect(w.text()).toContain(HASHLING_MOMENTS.M18.line)
  })

  it('says it is finished with a thumbs-up', async () => {
    boot()
    vi.spyOn(api, 'updateSettings').mockResolvedValue({ general: {}, units: {}, energy: {}, alerts: { quiet_hours: null }, ui: {} } as never)
    const w = await mountWithRouter(SetupPage, stubs)
    await w.get('[data-testid="setup-start"]').trigger('click')
    await press(w, 'I will add them later')
    await w.get('form').trigger('submit')
    await flushPromises()
    await press(w, 'Skip for now')
    expect(w.find(`img[src="${HASHLING_ART.tinkering}"]`).exists()).toBe(false)
    expect(w.get(`img[src="${HASHLING_ART['thumbs-up']}"]`).attributes('alt')).toBe(HASHLING_UI.U01e)
    expect(w.text()).toContain(HASHLING_MOMENTS.M19.title)
    expect(w.text()).toContain(HASHLING_MOMENTS.M19.line)
    expect(w.find('[data-testid="setup-finish"]').exists()).toBe(true)
  })

  it('keeps the setup art when pop-ups are off (it is page content, not a pop-up)', async () => {
    boot(false)
    const w = await mountWithRouter(SetupPage, stubs)
    expect(w.find(`img[src="${HASHLING_ART.tinkering}"]`).exists()).toBe(true)
  })
})

describe('card 2362: the empty "No miners yet" screens (M20), the only empty-state Hashling', () => {
  const stubs = { MinerTile: true, MinerTable: true, Select: true, Segmented: true }

  it('the dashboard miners widget shows Hashling tinkering and his line', async () => {
    const { live } = boot()
    live.devicesById = {}
    const w = await mountWithRouter(MinersWidget, stubs)
    expect(w.get(`img[src="${HASHLING_ART.tinkering}"]`).attributes('alt')).toBe(HASHLING_UI.U01f)
    expect(w.text()).toContain('No miners yet')
    expect(w.text()).toContain(HASHLING_MOMENTS.M20.line)
  })

  it('the Miners page shows the same', async () => {
    const { live } = boot()
    live.devicesById = {}
    const w = await mountWithRouter(MinersPage, stubs)
    expect(w.get(`img[src="${HASHLING_ART.tinkering}"]`).attributes('alt')).toBe(HASHLING_UI.U01f)
    expect(w.text()).toContain(HASHLING_MOMENTS.M20.line)
  })

  it('stays when pop-ups are off: it is static art', async () => {
    const { live } = boot(false)
    live.devicesById = {}
    const w = await mountWithRouter(MinersWidget, stubs)
    expect(w.find(`img[src="${HASHLING_ART.tinkering}"]`).exists()).toBe(true)
  })

  it('a healthy fleet has no Hashling in the widget', async () => {
    const { live } = boot()
    live.devicesById = { a: dev('a', 'Garage'), b: dev('b', 'Office') }
    const w = await mountWithRouter(MinersWidget, stubs)
    expect(w.find('img').exists()).toBe(false)
  })

  it('the shared empty state has no Hashling of its own, so every other empty widget stays Hashling-free', async () => {
    boot()
    const w = await mountWithRouter(EmptyState, {}, { title: 'Nothing yet', description: 'Events show up here.' })
    expect(w.find('img').exists()).toBe(false)
  })
})

describe('card 2362: the getting-started checklist is finished (M21)', () => {
  const insight = (id: string): Insight => ({ id, level: 'tip', title: id, body: '', action: null, device_id: null })
  // What the server answers: with no miners only "no-miners"; with a miner, a reminder for every step still open.
  const NO_MINERS = [insight('no-miners')]
  const FIRST_MINER_REMINDERS = ['no-node', 'energy-default', 'no-channel', 'no-password'].map(insight)
  const SOURCE = { id: 'src1', kind: 'bitcoin_core', name: 'My node', ok: true, error: null, implicit: false }
  const deferred = <T>() => {
    let resolve!: (value: T) => void
    let reject!: (reason: unknown) => void
    const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej })
    return { promise, resolve, reject }
  }
  const spentMarker = (): boolean => (localStorage.getItem('bsmm.hashlingSeen') ?? '').includes('checklist')

  /** An empty fleet with the checklist open, then the first miner added: the miner count changes at once, the answer later. */
  async function addFirstMiner() {
    const ctx = boot()
    const refreshed = deferred<Insight[]>()
    const insights = vi.spyOn(api, 'insights').mockResolvedValueOnce(NO_MINERS).mockReturnValueOnce(refreshed.promise)
    ctx.live.devicesById = {}
    const w = await mountWithRouter(ChecklistWidget)
    ctx.live.devicesById = { a: dev('a', 'Garage') }
    await flushPromises()
    return { ...ctx, w, insights, refreshed }
  }

  it('adding the first miner with the other steps still open shows nothing, while the refresh is pending and after it answers', async () => {
    const { hashling, w, insights, refreshed } = await addFirstMiner()
    expect(insights).toHaveBeenCalledTimes(2)
    // The page still holds the list for an empty fleet, which has no reminders: that is not "everything is done".
    expect(hashling.items).toEqual([])
    expect(spentMarker()).toBe(false)
    refreshed.resolve(FIRST_MINER_REMINDERS)
    await flushPromises()
    expect(w.text()).toContain('1/5')
    expect(hashling.items).toEqual([])
    expect(spentMarker()).toBe(false)
  })

  it('a refresh that fails is not news either', async () => {
    const { hashling, refreshed } = await addFirstMiner()
    refreshed.reject(new Error('insights unavailable'))
    await flushPromises()
    expect(hashling.items).toEqual([])
    expect(spentMarker()).toBe(false)
  })

  it('celebrates once, when the last step really is done while watching', async () => {
    const { live, hashling, insights, refreshed } = await addFirstMiner()
    refreshed.resolve(FIRST_MINER_REMINDERS)
    await flushPromises()
    expect(hashling.items).toEqual([])
    // The user connects a node and finishes the rest; the refresh that follows the change is what completes the list.
    const final = deferred<Insight[]>()
    insights.mockReturnValueOnce(final.promise)
    live.network = { sources: [SOURCE] } as never
    await flushPromises()
    expect(hashling.items).toEqual([])
    final.resolve([])
    await flushPromises()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M21'])
    expect(hashling.current).toMatchObject({ pose: 'thumbs-up', title: HASHLING_MOMENTS.M21.title, line: HASHLING_MOMENTS.M21.line })
    expect(spentMarker()).toBe(true)
  })

  it('does not celebrate a checklist that was already finished when the page loaded', async () => {
    const { live, hashling } = boot()
    vi.spyOn(api, 'insights').mockResolvedValue([])
    live.devicesById = { a: dev('a', 'Garage') }
    await mountWithRouter(ChecklistWidget)
    await flushPromises()
    expect(hashling.items).toEqual([])
  })

  it('does not celebrate again after it has been shown', async () => {
    const { live, hashling, insights, refreshed } = await addFirstMiner()
    refreshed.resolve(FIRST_MINER_REMINDERS)
    await flushPromises()
    insights.mockResolvedValueOnce([])
    live.network = { sources: [SOURCE] } as never
    await flushPromises()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M21'])
    hashling.dismiss()
    // a step is undone and done again
    insights.mockResolvedValueOnce(FIRST_MINER_REMINDERS)
    live.network = { sources: [] } as never
    await flushPromises()
    insights.mockResolvedValueOnce([])
    live.network = { sources: [SOURCE] } as never
    await flushPromises()
    expect(hashling.items).toEqual([])
  })
})

describe('card 2362: notifications switched on (M22) and a test that arrives (M23)', () => {
  const channel = (enabled: boolean): Channel => ({ id: 'c1', kind: 'ntfy', name: 'Phone', enabled, config: {}, min_severity: 'info' }) as unknown as Channel
  const stubs = { Select: true, ToggleRow: true, Dialog: true }

  async function open(enabled: boolean, popups = true) {
    const ctx = boot(popups)
    vi.spyOn(api, 'channelTypes').mockResolvedValue([])
    vi.spyOn(api, 'channels').mockResolvedValue([channel(enabled)])
    const w = await mountWithRouter(NotificationsSettings, stubs)
    return { ...ctx, w }
  }
  const sendTest = async (w: Wrapper): Promise<void> => {
    await w.findAll('button').find((b) => b.text().includes('Send test'))!.trigger('click')
    await flushPromises()
  }

  it('switching a channel on shows Hashling', async () => {
    vi.spyOn(api, 'updateChannel').mockResolvedValue(channel(true))
    const { w, hashling } = await open(false)
    w.findComponent(Switch).vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(hashling.current).toMatchObject({ momentId: 'M22', pose: 'thumbs-up', title: HASHLING_MOMENTS.M22.title, line: HASHLING_MOMENTS.M22.line })
  })

  it('switching a channel off does not', async () => {
    vi.spyOn(api, 'updateChannel').mockResolvedValue(channel(false))
    const { w, hashling } = await open(true)
    w.findComponent(Switch).vm.$emit('update:modelValue', false)
    await flushPromises()
    expect(hashling.items).toEqual([])
  })

  it('does not celebrate a switch that the server refused', async () => {
    vi.spyOn(api, 'updateChannel').mockRejectedValue(new Error('nope'))
    const { w, hashling } = await open(false)
    w.findComponent(Switch).vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(hashling.items).toEqual([])
  })

  it('a test that went through shows Hashling instead of the toast', async () => {
    vi.spyOn(api, 'testChannel').mockResolvedValue({ ok: true } as never)
    const { w, hashling, toasts } = await open(true)
    await sendTest(w)
    expect(hashling.current).toMatchObject({ momentId: 'M23', pose: 'thumbs-up', line: HASHLING_MOMENTS.M23.line })
    expect(toasts.items).toEqual([])
  })

  it('a test that failed is still a toast, never Hashling', async () => {
    vi.spyOn(api, 'testChannel').mockResolvedValue({ ok: false, error: 'refused' } as never)
    const { w, hashling, toasts } = await open(true)
    await sendTest(w)
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.kind)).toEqual(['error'])
  })

  it('with pop-ups off a test that went through is the toast it always was', async () => {
    vi.spyOn(api, 'testChannel').mockResolvedValue({ ok: true } as never)
    const { w, hashling, toasts } = await open(true, false)
    await sendTest(w)
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.title)).toEqual(['Test sent to Phone'])
  })
})

describe('card 2362: the channel dialog (M23 from "Send a test", M22 from adding a channel)', () => {
  const NTFY = { kind: 'ntfy', label: 'ntfy', help: '', fields: [] }
  const channel = (enabled: boolean): Channel => ({ id: 'c1', kind: 'ntfy', name: 'Phone', enabled, config: {}, has_secret: false, min_severity: 'info', created_at: 1 }) as Channel
  // The real dialog draws in a portal; this one draws its content in place so the test can reach the buttons.
  const InlineDialog = defineComponent({
    name: 'Dialog',
    props: { open: Boolean, title: { type: String, default: '' } },
    setup: (props, { slots }) => () => (props.open ? h('div', { role: 'dialog' }, [slots.default?.(), slots.footer?.()]) : null),
  })
  const stubs = { Select: true, ToggleRow: true, Dialog: InlineDialog }
  const deferred = <T>() => {
    let resolve!: (value: T) => void
    const promise = new Promise<T>((res) => { resolve = res })
    return { promise, resolve }
  }

  async function openDialog(mode: 'edit' | 'add', popups = true) {
    const ctx = boot(popups)
    vi.spyOn(api, 'channelTypes').mockResolvedValue([NTFY])
    vi.spyOn(api, 'channels').mockResolvedValue([channel(true)])
    const w = await mountWithRouter(NotificationsSettings, stubs)
    await w.get(mode === 'edit' ? 'button[aria-label="Edit Phone"]' : '[data-testid="add-channel"]').trigger('click')
    await flushPromises()
    expect(w.find('[role="dialog"]').exists()).toBe(true)
    return { ...ctx, w }
  }
  const dialogButton = (w: Wrapper, label: string) => {
    const found = w.findAll('[role="dialog"] button').find((b) => b.text().includes(label))
    expect(found, `a "${label}" button in the dialog`).toBeTruthy()
    return found!
  }
  const press = async (w: Wrapper, label: string): Promise<void> => {
    await dialogButton(w, label).trigger('click')
    await flushPromises()
  }
  const saveButton = (w: Wrapper) => w.get('[data-testid="channel-save"]')
  const inlineResult = (w: Wrapper) => w.find('[data-testid="channel-test-result"]')

  it('a test that went through from the edit dialog shows Hashling once and keeps the inline result', async () => {
    const test = vi.spyOn(api, 'testChannel').mockResolvedValue({ ok: true } as never)
    const { w, hashling, toasts } = await openDialog('edit')
    await press(w, 'Send a test')
    expect(test).toHaveBeenCalledTimes(1)
    expect(test).toHaveBeenCalledWith('c1')
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M23'])
    expect(hashling.current).toMatchObject({ pose: 'thumbs-up', title: HASHLING_MOMENTS.M23.title, line: HASHLING_MOMENTS.M23.line })
    expect(inlineResult(w).text()).toContain('Delivered')
    expect(toasts.items).toEqual([])
  })

  it('a test of a new, unsaved channel shows Hashling once too', async () => {
    const inline = vi.spyOn(api, 'testChannelInline').mockResolvedValue({ ok: true } as never)
    const { w, hashling } = await openDialog('add')
    await press(w, 'Send a test')
    expect(inline).toHaveBeenCalledTimes(1)
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M23'])
    expect(inlineResult(w).text()).toContain('Delivered')
  })

  it('a test the channel refused shows no Hashling, only the inline failure', async () => {
    vi.spyOn(api, 'testChannel').mockResolvedValue({ ok: false, error: 'refused' } as never)
    const { w, hashling } = await openDialog('edit')
    await press(w, 'Send a test')
    expect(hashling.items).toEqual([])
    expect(inlineResult(w).text()).toContain('refused')
  })

  it('a test that could not even be sent shows no Hashling', async () => {
    vi.spyOn(api, 'testChannelInline').mockRejectedValue(new Error('network down'))
    const { w, hashling } = await openDialog('add')
    await press(w, 'Send a test')
    expect(hashling.items).toEqual([])
    expect(inlineResult(w).text()).toContain('network down')
  })

  it('a test whose draft was edited while it ran is superseded: no Hashling and no result', async () => {
    const pending = deferred<{ ok: boolean }>()
    vi.spyOn(api, 'testChannel').mockReturnValue(pending.promise as never)
    const { w, hashling } = await openDialog('edit')
    void dialogButton(w, 'Send a test').trigger('click')
    await flushPromises()
    await w.get('[role="dialog"] input').setValue('Phone, renamed')
    pending.resolve({ ok: true })
    await flushPromises()
    expect(hashling.items).toEqual([])
    expect(inlineResult(w).exists()).toBe(false)
  })

  it('with pop-ups off the inline result is all there is', async () => {
    vi.spyOn(api, 'testChannel').mockResolvedValue({ ok: true } as never)
    const { w, hashling, toasts } = await openDialog('edit', false)
    await press(w, 'Send a test')
    expect(hashling.items).toEqual([])
    expect(toasts.items).toEqual([])
    expect(inlineResult(w).text()).toContain('Delivered')
  })

  it('adding a channel (created switched on) shows Hashling instead of the toast', async () => {
    const create = vi.spyOn(api, 'createChannel').mockResolvedValue(channel(true))
    const { w, hashling, toasts } = await openDialog('add')
    await saveButton(w).trigger('click')
    await flushPromises()
    expect(create).toHaveBeenCalledTimes(1)
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M22'])
    expect(hashling.current).toMatchObject({ pose: 'thumbs-up', title: HASHLING_MOMENTS.M22.title, line: HASHLING_MOMENTS.M22.line })
    expect(toasts.items).toEqual([])
    expect(w.find('[role="dialog"]').exists()).toBe(false)
  })

  it('with pop-ups off adding a channel keeps the toast it always had', async () => {
    vi.spyOn(api, 'createChannel').mockResolvedValue(channel(true))
    const { w, hashling, toasts } = await openDialog('add', false)
    await saveButton(w).trigger('click')
    await flushPromises()
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.title)).toEqual(['Channel added'])
  })

  it('a channel the server refused to create shows no Hashling and keeps the dialog open with the error', async () => {
    vi.spyOn(api, 'createChannel').mockRejectedValue(new Error('refused to create'))
    const { w, hashling, toasts } = await openDialog('add')
    await saveButton(w).trigger('click')
    await flushPromises()
    expect(hashling.items).toEqual([])
    expect(toasts.items).toEqual([])
    expect(w.get('[role="dialog"]').text()).toContain('refused to create')
  })

  it('a channel that came back switched off is not "switched on": no Hashling, the toast stays', async () => {
    vi.spyOn(api, 'createChannel').mockResolvedValue(channel(false))
    const { w, hashling, toasts } = await openDialog('add')
    await saveButton(w).trigger('click')
    await flushPromises()
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.title)).toEqual(['Channel added'])
  })

  it('saving changes to an existing channel is not switching one on', async () => {
    const update = vi.spyOn(api, 'updateChannel').mockResolvedValue(channel(true))
    const { w, hashling, toasts } = await openDialog('edit')
    await saveButton(w).trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledTimes(1)
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.title)).toEqual(['Saved'])
  })
})

describe('card 2362: accepting a pool change (M24)', () => {
  const changed = dev('a', 'Garage', { pool_change: { event_id: 5, since_ts: 1, changes: [] } } as Partial<DeviceView>)

  it('shows Hashling, naming the miner, instead of the toast', async () => {
    const { hashling, toasts } = boot()
    vi.spyOn(api, 'acceptPoolChange').mockResolvedValue({ device: dev('a', 'Garage') } as never)
    expect(await useMinerMonitor().acceptPoolChange(changed)).toBe(true)
    expect(hashling.current).toMatchObject({ momentId: 'M24', pose: 'thumbs-up', line: fill(HASHLING_MOMENTS.M24.line, { miner: 'Garage' }) })
    expect(toasts.items).toEqual([])
  })

  it('with pop-ups off it is the toast it always was', async () => {
    const { hashling, toasts } = boot(false)
    vi.spyOn(api, 'acceptPoolChange').mockResolvedValue({ device: dev('a', 'Garage') } as never)
    await useMinerMonitor().acceptPoolChange(changed)
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.title)).toEqual([poolChangeText.acceptedToast('Garage')])
  })

  it('a refused accept shows the error and no Hashling', async () => {
    const { hashling, toasts } = boot()
    vi.spyOn(api, 'acceptPoolChange').mockRejectedValue(new Error('refused'))
    expect(await useMinerMonitor().acceptPoolChange(changed)).toBe(false)
    expect(hashling.items).toEqual([])
    expect(toasts.items.map((t) => t.kind)).toEqual(['error'])
  })
})

describe('card 2362: the one joke on the Odds page (M25)', () => {
  it('is a small, static lottery-ticket Hashling with his line', async () => {
    boot()
    const w = await mountWithRouter(HashlingNote, {}, { moment: 'M25', scale: 1 })
    const img = w.get('img')
    expect(img.attributes('src')).toBe(HASHLING_ART['lottery-ticket'])
    expect(img.attributes('alt')).toBe(HASHLING_UI.U01g)
    expect(img.attributes('width')).toBe('52')
    expect(w.text()).toContain(HASHLING_MOMENTS.M25.line)
    expect(img.classes()).not.toContain('hashling-hop')
  })
})
