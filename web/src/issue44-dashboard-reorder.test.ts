import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api } from '@/lib/api'
import type { Settings } from '@/lib/types'
import { mergeSettings, useSettings } from '@/stores/settings'
import { useSession } from '@/stores/session'
import { useLive } from '@/stores/live'
import { DEFAULT_LAYOUT, WIDGET_BY_ID } from '@/components/dashboard/registry'
import DashboardPage from '@/pages/DashboardPage.vue'

// Real widgets pull in charts and live data. Each one becomes a small stand-in with a focusable control, so the
// page's own editing behaviour (order, focus, inert preview) is what these tests exercise.
vi.mock('@/components/dashboard/registry', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/components/dashboard/registry')>()
  const { defineComponent, h } = await import('vue')
  const widgets = original.WIDGETS.map((w) => ({
    ...w,
    component: defineComponent({
      name: `Stub-${w.id}`,
      render: () => h('div', { 'data-stub-widget': w.id }, [h('button', { 'data-testid': 'stub-control' }, `inner ${w.id}`)]),
    }),
  }))
  return { ...original, WIDGETS: widgets, WIDGET_BY_ID: Object.fromEntries(widgets.map((w) => [w.id, w])) }
})

// Sortable needs real pointer geometry that happy-dom does not provide; dragging is not what is under test.
vi.mock('vue-draggable-plus', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    VueDraggable: defineComponent({
      name: 'VueDraggable',
      props: { modelValue: { type: Array, default: () => [] } },
      setup: (_props, { slots }) => () => h('div', slots.default?.()),
    }),
  }
})

function config(): Settings {
  // Only fields consumed by the dashboard; no backend, credentials or private fixture data.
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null },
  } as Settings
}

function mountPage(router: ReturnType<typeof createRouter>) {
  return mount(DashboardPage, { attachTo: document.body, global: { plugins: [router] } })
}
type Wrapper = ReturnType<typeof mountPage>
const wrappers: Wrapper[] = []

async function openEditor(): Promise<Wrapper> {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mountPage(router)
  wrappers.push(wrapper)
  await flushPromises()
  await wrapper.get('[data-testid="customize"]').trigger('click')
  await flushPromises()
  return wrapper
}

const order = (wrapper: Wrapper): string[] => wrapper.findAll('[data-stub-widget]').map((el) => el.attributes('data-stub-widget') ?? '')
const control = (title: string, direction: 'earlier' | 'later'): HTMLButtonElement | null =>
  document.querySelector<HTMLButtonElement>(`[aria-label="Move ${title} ${direction}"]`)

// An element is inert when it or an ancestor carries the inert attribute or property (browsers skip it in Tab order).
function isInert(el: HTMLElement): boolean {
  for (let node: HTMLElement | null = el; node; node = node.parentElement) {
    if (node.hasAttribute('inert') || node.inert === true) return true
  }
  return false
}

async function move(title: string, direction: 'earlier' | 'later'): Promise<void> {
  const button = control(title, direction)
  if (!button) throw new Error(`No "Move ${title} ${direction}" control in the editor`)
  button.click()
  await flushPromises()
}

beforeEach(() => {
  setActivePinia(createPinia())
  const session = useSession()
  session.state = 'ready'
  session.me = { name: 'tester', scope: 'admin', via: 'token' }
  useSettings().data = config()
  useLive().loaded = true
  vi.spyOn(api, 'updateSettings').mockImplementation(async (body) => mergeSettings(config(), body))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks()
})

describe('issue 44: dashboard layout without dragging', () => {
  it('can reorder every card with the keyboard-reachable controls and saves that order', async () => {
    const wrapper = await openEditor()
    const original = DEFAULT_LAYOUT.map((p) => p.id)
    expect(order(wrapper)).toEqual(original)

    // Reverse the whole dashboard: bring each card, in turn, to the front.
    for (let i = 1; i < original.length; i++) {
      const title = WIDGET_BY_ID[original[i]!]!.title
      for (let step = 0; step < i; step++) await move(title, 'earlier')
    }
    expect(order(wrapper)).toEqual([...original].reverse())

    await wrapper.get('[data-testid="customize-done"]').trigger('click')
    await flushPromises()
    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    const body = vi.mocked(api.updateSettings).mock.calls[0]![0] as { ui: { dashboard: { widgets: { id: string }[] } } }
    expect(body.ui.dashboard.widgets.map((p) => p.id)).toEqual([...original].reverse())
  })

  it('offers no move past either end of the layout', async () => {
    await openEditor()
    const first = WIDGET_BY_ID[DEFAULT_LAYOUT[0]!.id]!.title
    const last = WIDGET_BY_ID[DEFAULT_LAYOUT[DEFAULT_LAYOUT.length - 1]!.id]!.title
    expect(control(first, 'earlier')?.disabled).toBe(true)
    expect(control(first, 'later')?.disabled).toBe(false)
    expect(control(last, 'later')?.disabled).toBe(true)
    expect(control(last, 'earlier')?.disabled).toBe(false)
  })

  it('keeps focus on the moved card and announces its new position', async () => {
    const wrapper = await openEditor()
    await move('Fleet hashrate', 'later')
    expect(order(wrapper).indexOf('hero')).toBe(2)
    expect(document.activeElement).toBe(control('Fleet hashrate', 'later'))
    expect(wrapper.get('[data-testid="reorder-announcement"]').text()).toBe(`Fleet hashrate moved to position 3 of ${DEFAULT_LAYOUT.length}`)

    // Reaching the end disables the pressed control; focus must move to the card's other control, not vanish.
    const last = DEFAULT_LAYOUT.length - 1
    await move('Fees & price', 'later')
    expect(order(wrapper).indexOf('fees')).toBe(last)
    expect(control('Fees & price', 'later')?.disabled).toBe(true)
    expect(document.activeElement).toBe(control('Fees & price', 'earlier'))
  })

  it('makes the widget previews inert while editing, so Tab only reaches the editing controls', async () => {
    await openEditor()
    const controls = Array.from(document.querySelectorAll<HTMLElement>('[data-testid="stub-control"]'))
    expect(controls).toHaveLength(DEFAULT_LAYOUT.length)
    for (const el of controls) expect(isInert(el)).toBe(true)
  })
})
