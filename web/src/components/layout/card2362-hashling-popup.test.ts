import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { HASHLING_ART } from '@/lib/brand'
import { HASHLING_MOMENTS, HASHLING_UI, fill } from '@/lib/hashlingText'
import type { AppEvent, DeviceView, Settings } from '@/lib/types'
import HashlingPopup from '@/components/layout/HashlingPopup.vue'
import { HASHLING_TIMING, useHashling } from '@/stores/hashling'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'

// Card #2362: the pop-up itself. Polite live region, real alt text, keyboard dismissal that does not steal focus,
// still frame for reduced motion, and a bigger version for the wall display.

const NOW_S = 1_700_000_000
const GRID_W = 52
const GRID_H = 44
let nextId = 1

function ev(type: string, severity: AppEvent['severity'], over: Partial<AppEvent> = {}): AppEvent {
  return { id: nextId++, ts: NOW_S, type, severity, device_id: 'a', title: 'server title', body: null, data: {}, dedupe_key: null, ack_ts: null, ...over }
}

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

function reducedMotion(on: boolean): void {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: on && query.includes('prefers-reduced-motion'),
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }))
}

async function open(path = '/', ui: Record<string, unknown> = {}) {
  setActivePinia(createPinia())
  useSession().state = 'ready'
  useSettings().data = { ui: { hashling_popups: true, reduce_motion: false, ...ui } } as unknown as Settings
  const live = useLive()
  live.devicesById = { a: { id: 'a', name: 'Garage', status: 'online', hashrate_smooth_hs: 1e12 } as unknown as DeviceView, b: { id: 'b', name: 'Office', status: 'online', hashrate_smooth_hs: 1e12 } as unknown as DeviceView }
  live.loaded = true
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/kiosk', name: 'kiosk', component: { render: () => null } },
      { path: '/:rest(.*)*', component: { render: () => null } },
    ],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(HashlingPopup, { attachTo: document.body, global: { plugins: [router] } })
  wrappers.push(wrapper)
  return { wrapper, hashling: useHashling() }
}

beforeEach(() => {
  nextId = 1
  localStorage.clear()
  reducedMotion(false)
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
  vi.setSystemTime(new Date(NOW_S * 1000))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  document.body.innerHTML = ''
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

const card = (w: Wrapper) => w.find('[data-testid="hashling-popup"]')
const poseImg = (w: Wrapper) => w.get('[data-testid="hashling-popup"] img')

describe('card 2362: the pop-up on the dashboard', () => {
  it('is a polite live region that is empty until something happens', async () => {
    const { wrapper } = await open()
    expect(wrapper.get('[data-testid="hashling-popups"]').attributes('aria-live')).toBe('polite')
    expect(card(wrapper).exists()).toBe(false)
  })

  it('shows the pose with real alt text, the title and the line, at a whole-number scale with crisp pixels', async () => {
    const { wrapper, hashling } = await open()
    hashling.show('M23')
    await nextTick()
    const img = poseImg(wrapper)
    expect(img.attributes('src')).toBe(HASHLING_ART['thumbs-up'])
    expect(img.attributes('alt')).toBe(HASHLING_UI.U01e)
    const width = Number(img.attributes('width'))
    const height = Number(img.attributes('height'))
    expect(width % GRID_W).toBe(0)
    expect(height % GRID_H).toBe(0)
    expect(width / GRID_W).toBe(height / GRID_H)
    expect(img.classes()).toContain('hashling-art') // main.css keeps .hashling-art pixelated (see the art test)
    expect(card(wrapper).text()).toContain(HASHLING_MOMENTS.M23.title)
    expect(card(wrapper).text()).toContain(HASHLING_MOMENTS.M23.line)
  })

  it('uses the toaster roles: assertive only for a critical pop-up', async () => {
    const { wrapper, hashling } = await open()
    hashling.offer(ev('device_offline', 'critical'))
    vi.advanceTimersByTime(HASHLING_TIMING.coalesceMs + 1)
    await nextTick()
    expect(card(wrapper).attributes('role')).toBe('alert')
    expect(poseImg(wrapper).attributes('alt')).toBe(HASHLING_UI.U01a)
    hashling.dismiss()
    hashling.show('M22')
    await nextTick()
    expect(card(wrapper).attributes('role')).toBe('status')
  })

  it('names the miner in the line', async () => {
    const { wrapper, hashling } = await open()
    hashling.offer(ev('new_best_share', 'success', { device_id: 'b' }))
    vi.advanceTimersByTime(HASHLING_TIMING.coalesceMs + 1)
    await nextTick()
    expect(card(wrapper).text()).toContain(fill(HASHLING_MOMENTS.M14.line, { miner: 'Office' }))
  })

  it('has a focusable Dismiss button that closes it', async () => {
    const { wrapper, hashling } = await open()
    hashling.show('M22')
    await nextTick()
    const button = wrapper.get('[data-testid="hashling-popup"] button')
    expect(button.attributes('aria-label')).toBe(HASHLING_UI.U04)
    expect(button.attributes('type')).toBe('button')
    expect(button.attributes('tabindex')).not.toBe('-1')
    await button.trigger('click')
    expect(card(wrapper).exists()).toBe(false)
    expect(hashling.items).toEqual([])
  })

  it('closes with Escape', async () => {
    const { wrapper, hashling } = await open()
    hashling.show('M22')
    await nextTick()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(card(wrapper).exists()).toBe(false)
  })

  it('leaves Escape to an open dialog, so one key press never closes both', async () => {
    const { wrapper, hashling } = await open()
    const dialog = document.createElement('div')
    dialog.setAttribute('role', 'dialog')
    document.body.append(dialog)
    hashling.show('M22')
    await nextTick()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(card(wrapper).exists()).toBe(true)
  })

  it('does not take the focus when it appears', async () => {
    const { hashling } = await open()
    const input = document.createElement('input')
    document.body.append(input)
    input.focus()
    hashling.show('M22')
    await nextTick()
    expect(document.activeElement).toBe(input)
  })

  it('tells how many more are waiting, with the "{count} more" wording', async () => {
    const { wrapper, hashling } = await open()
    hashling.show('M22')
    hashling.show('M23')
    hashling.show('M24', { miner: 'Garage' })
    await nextTick()
    expect(wrapper.get('[data-testid="hashling-more"]').text()).toBe(fill(HASHLING_UI.U05, { count: 2 }))
    hashling.dismiss()
    hashling.dismiss()
    await nextTick()
    expect(wrapper.find('[data-testid="hashling-more"]').exists()).toBe(false)
  })

  it('goes away by itself', async () => {
    const { wrapper, hashling } = await open()
    hashling.show('M22')
    await nextTick()
    vi.advanceTimersByTime(HASHLING_TIMING.popupMs + 500)
    await nextTick()
    expect(card(wrapper).exists()).toBe(false)
  })

  it('shows nothing for a healthy fleet: info and healthy events leave the region empty', async () => {
    const { wrapper, hashling } = await open()
    hashling.offer(ev('device_restarted', 'info'))
    hashling.offer(ev('device_recovered', 'success'))
    hashling.offer(ev('difficulty_adjusted', 'info', { device_id: null }))
    vi.advanceTimersByTime(HASHLING_TIMING.maxWaitMs + 1)
    await nextTick()
    expect(card(wrapper).exists()).toBe(false)
  })
})

describe('card 2362: reduced motion shows a still frame', () => {
  const HOP = 'hashling-hop'

  it('hops once on arrival when motion is welcome', async () => {
    const { wrapper, hashling } = await open()
    hashling.show('M22')
    await nextTick()
    expect(poseImg(wrapper).classes()).toContain(HOP)
  })

  it('does not hop when the device asks for reduced motion', async () => {
    reducedMotion(true)
    const { wrapper, hashling } = await open()
    hashling.show('M22')
    await nextTick()
    expect(poseImg(wrapper).classes()).not.toContain(HOP)
  })

  it('does not hop when the in-app Reduce motion switch is on', async () => {
    const { wrapper, hashling } = await open('/', { reduce_motion: true })
    hashling.show('M22')
    await nextTick()
    expect(poseImg(wrapper).classes()).not.toContain(HOP)
  })

  it('never hops while asleep', async () => {
    const { wrapper, hashling } = await open()
    hashling.offer(ev('device_degraded', 'warning', { body: 'Not hashing' }))
    vi.advanceTimersByTime(HASHLING_TIMING.coalesceMs + 1)
    await nextTick()
    expect(poseImg(wrapper).attributes('alt')).toBe(HASHLING_UI.U01b)
    expect(poseImg(wrapper).classes()).not.toContain(HOP)
  })
})

describe('card 2362: the wall display', () => {
  it('shows the same pop-up larger, at a whole-number scale, and tells the store it is the wall', async () => {
    const dash = await open('/')
    dash.hashling.show('M22')
    await nextTick()
    const dashWidth = Number(poseImg(dash.wrapper).attributes('width'))

    const wall = await open('/kiosk')
    expect(wall.hashling.surface).toBe('wall')
    wall.hashling.show('M22')
    await nextTick()
    const wallImg = poseImg(wall.wrapper)
    const wallWidth = Number(wallImg.attributes('width'))
    expect(wallWidth).toBeGreaterThan(dashWidth)
    expect(wallWidth % GRID_W).toBe(0)
    expect(Number(wallImg.attributes('height')) % GRID_H).toBe(0)
    expect(wallImg.attributes('alt')).toBe(HASHLING_UI.U01e)
    expect(wall.wrapper.get('[data-testid="hashling-popups"]').attributes('aria-live')).toBe('polite')
  })

  it('needs no click: it dismisses itself', async () => {
    const { wrapper, hashling } = await open('/kiosk')
    hashling.show('M22')
    await nextTick()
    vi.advanceTimersByTime(HASHLING_TIMING.popupMs + 500)
    await nextTick()
    expect(card(wrapper).exists()).toBe(false)
  })

  it('does not take Escape, which leaves the wall display', async () => {
    const { wrapper, hashling } = await open('/kiosk')
    hashling.show('M22')
    await nextTick()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(card(wrapper).exists()).toBe(true)
  })

  it('shows a found block for about a minute', async () => {
    const { wrapper, hashling } = await open('/kiosk')
    hashling.offer(ev('block_found', 'success', { device_id: null, data: { height: 900_001, hash: 'cd'.repeat(32), source: 'chain' } }))
    vi.advanceTimersByTime(HASHLING_TIMING.coalesceMs + 1)
    await nextTick()
    expect(poseImg(wrapper).attributes('alt')).toBe(HASHLING_UI.U01c)
    vi.advanceTimersByTime(HASHLING_TIMING.popupMs + 500)
    await nextTick()
    expect(card(wrapper).exists()).toBe(true)
    vi.advanceTimersByTime(HASHLING_TIMING.blockMs)
    await nextTick()
    expect(card(wrapper).exists()).toBe(false)
  })
})
