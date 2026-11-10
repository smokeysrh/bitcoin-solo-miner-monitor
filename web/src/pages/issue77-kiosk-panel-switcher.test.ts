import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { Settings } from '@/lib/types'
import { useSettings } from '@/stores/settings'
import KioskPage from '@/pages/KioskPage.vue'

// Issue 77: the wall display needs large labelled panel buttons and one lock button (grey = rotating, orange = locked).
// The page runs on fake timers so rotation is driven by the real component code, not a copy of it.

const ROTATE_S = 10
const ROTATE_MS = ROTATE_S * 1000
const LOCK = 'button[aria-label="Lock on this panel"]'

function config(): Settings {
  // Only the fields the wall display reads; no backend, credentials or private data.
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: {
      theme: 'dark',
      accent: '#F7931A',
      density: 'comfortable',
      reduce_motion: false,
      simple_mode: false,
      dashboard: null,
      kiosk: { rotate_s: ROTATE_S, panels: ['overview', 'miners', 'odds'], show_clock: false },
    },
  } as Settings
}

async function mountKiosk() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/kiosk')
  await router.isReady()
  const wrapper = mount(KioskPage, {
    attachTo: document.body,
    // charts, tiles and badges need live data and canvas; the controls and timers are what is under test
    global: { plugins: [router], stubs: { HistoryChart: true, MinerTile: true, LiveBadge: true, ProgressBar: true } },
  })
  await nextTick()
  return wrapper
}
type Wrapper = Awaited<ReturnType<typeof mountKiosk>>

let current: Wrapper | null = null
const spyOnTimers = () => ({ set: vi.spyOn(globalThis, 'setInterval'), clear: vi.spyOn(globalThis, 'clearInterval') })
let timers!: ReturnType<typeof spyOnTimers>

async function open(): Promise<Wrapper> {
  current = await mountKiosk()
  return current
}
async function advance(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms)
  await nextTick()
}
const shown = (w: Wrapper): string | undefined => w.get('main section').attributes('aria-label')
const lockButton = (w: Wrapper) => w.get<HTMLButtonElement>(LOCK)
const isLocked = (w: Wrapper): string | undefined => lockButton(w).attributes('aria-pressed')
async function press(w: Wrapper, selector: string): Promise<void> {
  await w.get<HTMLButtonElement>(selector).trigger('click')
}

/** Rotation intervals (the only ones with the rotate period) that were started and never cleared. */
function activeRotations(): number {
  const cleared = new Set<unknown>(timers.clear.mock.calls.map((call) => call[0] as unknown))
  return timers.set.mock.calls.filter((call, i) => (call[1] as unknown) === ROTATE_MS && !cleared.has(timers.set.mock.results[i]?.value)).length
}

beforeEach(() => {
  vi.useFakeTimers()
  setActivePinia(createPinia())
  useSettings().data = config()
  timers = spyOnTimers()
})
afterEach(() => {
  current?.unmount()
  current = null
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('issue 77: wall display panel buttons', () => {
  it('shows a large labelled button for each enabled panel and previous/next, and no others', async () => {
    const w = await open()
    const labels = w.findAll('footer button').map((b) => b.text())
    expect(labels).toEqual(expect.arrayContaining(['Overview', 'Miners', 'Odds', 'Previous', 'Next']))
    expect(labels).not.toContain('Network')
    expect(labels).not.toContain('Chart')
  })

  it('marks exactly the current panel for screen readers and follows manual choices', async () => {
    const w = await open()
    expect(w.findAll('footer button[aria-current="true"]').map((b) => b.text())).toEqual(['Overview'])
    await press(w, 'button[aria-label="Show odds"]')
    expect(shown(w)).toBe('odds')
    expect(w.findAll('footer button[aria-current="true"]').map((b) => b.text())).toEqual(['Odds'])
  })

  it('previous and next buttons move one panel and wrap around', async () => {
    const w = await open()
    await press(w, 'button[aria-label="Previous panel"]')
    expect(shown(w)).toBe('odds')
    await press(w, 'button[aria-label="Next panel"]')
    expect(shown(w)).toBe('overview')
    await press(w, 'button[aria-label="Next panel"]')
    expect(shown(w)).toBe('miners')
  })
})

describe('issue 77: lock button', () => {
  it('starts unlocked with an accessible name and pressed state, and the display rotates', async () => {
    const w = await open()
    expect(isLocked(w)).toBe('false')
    expect(shown(w)).toBe('overview')
    await advance(ROTATE_MS)
    expect(shown(w)).toBe('miners')
    await advance(ROTATE_MS)
    expect(shown(w)).toBe('odds')
    expect(activeRotations()).toBe(1)
  })

  it('lock on: stays on the panel however long it waits and holds no rotation timer', async () => {
    const w = await open()
    await advance(ROTATE_MS)
    expect(shown(w)).toBe('miners')
    await lockButton(w).trigger('click')
    expect(isLocked(w)).toBe('true')
    await advance(ROTATE_MS * 6)
    expect(shown(w)).toBe('miners')
    expect(activeRotations()).toBe(0)
  })

  it('lock off: rotation resumes after one full period, with a single timer', async () => {
    const w = await open()
    await lockButton(w).trigger('click')
    await advance(ROTATE_MS * 3)
    expect(shown(w)).toBe('overview')
    await lockButton(w).trigger('click')
    expect(isLocked(w)).toBe('false')
    await advance(ROTATE_MS - 1)
    expect(shown(w)).toBe('overview')
    await advance(1)
    expect(shown(w)).toBe('miners')
    expect(activeRotations()).toBe(1)
    await advance(ROTATE_MS)
    expect(shown(w)).toBe('odds')
  })

  it('toggling again and again never leaves a second rotation timer running', async () => {
    const w = await open()
    for (let i = 0; i < 4; i++) await lockButton(w).trigger('click')
    expect(isLocked(w)).toBe('false')
    expect(activeRotations()).toBe(1)
    await advance(ROTATE_MS)
    expect(shown(w)).toBe('miners')
  })

  it('manual panel change while locked moves the panel, keeps the lock and starts no timer', async () => {
    const w = await open()
    await lockButton(w).trigger('click')
    await press(w, 'button[aria-label="Show odds"]')
    expect(shown(w)).toBe('odds')
    expect(isLocked(w)).toBe('true')
    await press(w, 'button[aria-label="Previous panel"]')
    expect(shown(w)).toBe('miners')
    expect(isLocked(w)).toBe('true')
    await advance(ROTATE_MS * 6)
    expect(shown(w)).toBe('miners')
    expect(activeRotations()).toBe(0)
  })

  it('manual panel change while rotating restarts the full period and keeps one timer', async () => {
    const w = await open()
    await advance(6000)
    await press(w, 'button[aria-label="Show miners"]')
    expect(shown(w)).toBe('miners')
    expect(isLocked(w)).toBe('false')
    await advance(ROTATE_MS - 1) // the old timer would have fired 4 seconds after the click
    expect(shown(w)).toBe('miners')
    await advance(1)
    expect(shown(w)).toBe('odds')
    expect(activeRotations()).toBe(1)
  })

  it('announces choices in a polite live region but not every automatic rotation', async () => {
    const w = await open()
    const region = w.get('[role="status"]')
    expect(region.attributes('aria-live')).toBe('polite')
    await advance(ROTATE_MS)
    expect(shown(w)).toBe('miners')
    expect(region.text()).toBe('')
    await lockButton(w).trigger('click')
    expect(region.text()).toMatch(/locked/i)
    expect(region.text()).toMatch(/miners/i)
    await lockButton(w).trigger('click')
    expect(region.text()).toMatch(/resumed/i)
  })
})

describe('issue 77: keyboard', () => {
  const key = (name: string, target: EventTarget = window): void => {
    target.dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true }))
  }

  it('ArrowRight and ArrowLeft change panel, and stay locked when locked', async () => {
    const w = await open()
    key('ArrowRight')
    await nextTick()
    expect(shown(w)).toBe('miners')
    key('ArrowLeft')
    key('ArrowLeft')
    await nextTick()
    expect(shown(w)).toBe('odds')
    await lockButton(w).trigger('click')
    key('ArrowRight')
    await nextTick()
    expect(shown(w)).toBe('overview')
    expect(isLocked(w)).toBe('true')
    expect(activeRotations()).toBe(0)
  })

  it('space advances the panel from the page, but on a focused button it only activates that button', async () => {
    const w = await open()
    key(' ', document.body)
    await nextTick()
    expect(shown(w)).toBe('miners') // control: space with nothing focused still advances
    key(' ', w.get<HTMLButtonElement>('button[aria-label="Show overview"]').element)
    await nextTick()
    expect(shown(w)).toBe('miners') // the browser's own button click handles it; the page must not also advance
  })
})

describe('issue 77: rotation timer ownership', () => {
  it('unmounting while rotating cancels the rotation timer', async () => {
    const w = await open()
    await advance(ROTATE_MS)
    await press(w, 'button[aria-label="Show odds"]')
    expect(activeRotations()).toBe(1)
    w.unmount()
    current = null
    expect(activeRotations()).toBe(0)
    await expect(advance(ROTATE_MS * 3)).resolves.toBeUndefined()
  })

  it('unmounting while locked leaves no timer and a lock-then-unmount does not restart one', async () => {
    const w = await open()
    await lockButton(w).trigger('click')
    w.unmount()
    current = null
    expect(activeRotations()).toBe(0)
    await advance(ROTATE_MS * 3)
    expect(activeRotations()).toBe(0)
  })
})
