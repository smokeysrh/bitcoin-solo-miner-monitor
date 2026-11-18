import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import type { Meta } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'

// The sidebar header: no instance-name line under the name, a bigger Hashling and name (the Hashling a whole multiple of
// his 32 x 32 grid so the blink frame is kept), and he blinks whenever the live stats refresh.

vi.mock('@/components/ui/Tooltip.vue', async () => {
  const { defineComponent } = await import('vue')
  return { default: defineComponent({ props: ['text', 'side', 'delay'], setup: (_props, { slots }) => () => slots.default?.() }) }
})

const INSTANCE_NAME = 'Fixture fleet name'
const SYMBOL_GRID = 32
const OLD_MARK_SIZE_PX = 32
const COLLAPSED_SIDEBAR_PX = 76
const FIRST_STATS_AT = 1_000
const NEXT_STATS_AT = 5_000
const MARK = '[data-testid="logo-mark"]'

const wrappers: { unmount: () => void }[] = []

function mountSidebar(collapsed: boolean) {
  useSession().meta = { version: '1.6.0', instance_name: INSTANCE_NAME } as Meta
  useUi().sidebarCollapsed = collapsed
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:rest(.*)*', component: { render: () => null } }] })
  const wrapper = mount(SidebarNav, { global: { plugins: [router] }, attachTo: document.body })
  wrappers.push(wrapper)
  return wrapper
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  document.documentElement.removeAttribute('data-reduce-motion')
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
  vi.useFakeTimers()
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('sidebar brand: the instance-name line is gone', () => {
  it('shows the name nowhere in the expanded sidebar', () => {
    const w = mountSidebar(false)
    expect(w.text()).not.toContain(INSTANCE_NAME)
  })

  it('shows it nowhere in the collapsed sidebar either', () => {
    expect(mountSidebar(true).text()).not.toContain(INSTANCE_NAME)
  })
})

describe('sidebar brand: bigger Hashling and name', () => {
  it.each([
    ['expanded', false],
    ['collapsed', true],
  ])('%s: the Hashling is bigger than before and a whole multiple of 32, so he can still blink', (_label, collapsed) => {
    const w = mountSidebar(collapsed)
    const size = Number(w.get(`${MARK} img`).attributes('width'))
    expect(size).toBeGreaterThan(OLD_MARK_SIZE_PX)
    expect(size % SYMBOL_GRID).toBe(0)
    expect(w.find('[data-testid="logo-blink-frame"]').exists()).toBe(true)
  })

  it('collapsed: the Hashling fits inside the collapsed sidebar width', () => {
    const w = mountSidebar(true)
    expect(Number(w.get(`${MARK} img`).attributes('width'))).toBeLessThanOrEqual(COLLAPSED_SIDEBAR_PX)
  })

  it('expanded: the name is bigger than the old 32 px high lockup, and the Hashling fills the header row', () => {
    const w = mountSidebar(false)
    const names = w.findAll('img[alt="HashHurdr"]')
    expect(names).toHaveLength(2) // dark and light file; the theme shows one
    for (const img of names) expect(Number(img.attributes('height'))).toBeGreaterThan(OLD_MARK_SIZE_PX)
    expect(w.find('[data-testid="sidebar-wordmark"]').exists()).toBe(true)
    // the Hashling beside the name is decoration (the name is written out), so he is not announced twice
    expect(w.get(`${MARK} img`).attributes('alt')).toBe('')
    // the header row is the 80 px one (h-20), tall enough for the 64 px Hashling with room around him
    expect(w.get(MARK).element.parentElement?.className).toContain('h-20')
  })
})

describe('sidebar brand: the Hashling blinks when the stats refresh', () => {
  it.each([
    ['expanded', false],
    ['collapsed', true],
  ])('%s: blinks when live.lastUpdate changes, not on the first load', async (_label, collapsed) => {
    const live = useLive()
    const w = mountSidebar(collapsed)
    live.lastUpdate = FIRST_STATS_AT // the first load
    await nextTick()
    expect(w.get(MARK).attributes('data-blinking')).toBe('false')
    live.lastUpdate = NEXT_STATS_AT // a refresh
    await nextTick()
    expect(w.get(MARK).attributes('data-blinking')).toBe('true')
  })
})
