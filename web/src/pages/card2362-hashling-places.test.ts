import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { Component } from 'vue'
import { api } from '@/lib/api'
import { HASHLING_ART } from '@/lib/brand'
import { HASHLING_MOMENTS, HASHLING_UI, fill } from '@/lib/hashlingText'
import type { Channel, DeviceView, Settings } from '@/lib/types'
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
  it('celebrates once when the last step is done while watching', async () => {
    const { live, hashling } = boot()
    vi.spyOn(api, 'insights').mockResolvedValue([])
    live.devicesById = {}
    await mountWithRouter(ChecklistWidget)
    expect(hashling.items).toEqual([])
    live.devicesById = { a: dev('a', 'Garage') }
    await flushPromises()
    expect(hashling.items.map((i) => i.momentId)).toEqual(['M21'])
    expect(hashling.current).toMatchObject({ pose: 'thumbs-up', title: HASHLING_MOMENTS.M21.title, line: HASHLING_MOMENTS.M21.line })
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
    const { live, hashling } = boot()
    vi.spyOn(api, 'insights').mockResolvedValue([])
    live.devicesById = {}
    await mountWithRouter(ChecklistWidget)
    live.devicesById = { a: dev('a', 'Garage') }
    await flushPromises()
    hashling.dismiss()
    live.devicesById = {}
    await mountWithRouter(ChecklistWidget)
    live.devicesById = { a: dev('a', 'Garage') }
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

  it('has exactly one such spot on the Odds page, and none on the other pages that show numbers', () => {
    const read = (name: string): string => readFileSync(fileURLToPath(new URL(`./${name}`, import.meta.url)), 'utf8')
    const odds = read('OddsPage.vue')
    expect(odds.match(/<HashlingNote/g)).toHaveLength(1)
    expect(odds).toContain('moment="M25"')
    for (const page of ['BitcoinPage.vue', 'AnalyticsPage.vue', 'AlertsPage.vue', 'LoginPage.vue', 'NotFoundPage.vue', 'SoloBlocksPage.vue']) {
      expect(read(page), page).not.toMatch(/Hashling/)
    }
  })
})
