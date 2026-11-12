import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { Component } from 'vue'
import { api } from '@/lib/api'
import type { Me, Settings } from '@/lib/types'
import { mergeSettings, useSettings } from '@/stores/settings'
import { useSession } from '@/stores/session'
import { useLive } from '@/stores/live'
import AppearanceSettings from '@/pages/settings/AppearanceSettings.vue'
import CustomizablePage from '@/components/layout/CustomizablePage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'

// Card #2367: every layout write (`ui.dashboard`, `ui.bitcoin_page`, `ui.odds_page`) goes to PATCH /api/v1/settings,
// which only an admin may call. A public-read viewer would be sent to sign-in, a read or control token would get a
// 403. Those sessions must not be offered Customize / Reset for the layout. The real components run here; only the
// network call, the dashboard widgets and the drag library are replaced.

// Real widgets pull in charts and live data; the dashboard header is what is under test.
vi.mock('@/components/dashboard/registry', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/components/dashboard/registry')>()
  const { defineComponent } = await import('vue')
  const widgets = original.WIDGETS.map((w) => ({ ...w, component: defineComponent({ name: `Stub-${w.id}`, render: () => null }) }))
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

const PUBLIC_READ: Me = { name: 'tv', scope: 'read', via: 'public' }
const READ_TOKEN: Me = { name: 'viewer', scope: 'read', via: 'token' }
const CONTROL_TOKEN: Me = { name: 'operator', scope: 'control', via: 'token' }
const ADMIN: Me = { name: 'owner', scope: 'admin', via: 'token' }
const CANNOT_WRITE_LAYOUT: { who: string; me: Me }[] = [
  { who: 'public-read viewer', me: PUBLIC_READ },
  { who: 'read-only token', me: READ_TOKEN },
  { who: 'control token', me: CONTROL_TOKEN },
]

function config(): Settings {
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null },
  } as unknown as Settings
}

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

async function open(component: Component, me: Me, options: { slots?: Record<string, string>; props?: Record<string, unknown> } = {}): Promise<Wrapper> {
  const session = useSession()
  session.state = 'ready'
  session.me = me
  useSettings().data = config()
  useLive().loaded = true
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(component, { attachTo: document.body, global: { plugins: [router] }, ...options })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(api, 'updateSettings').mockImplementation(async (body) => mergeSettings(config(), body))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks()
})

describe('card 2367: Settings -> Appearance dashboard layout reset needs admin rights', () => {
  const resetButtons = (wrapper: Wrapper) => wrapper.findAll('button').filter((b) => b.text().includes('Reset dashboard layout'))
  const customizeLinks = (wrapper: Wrapper) => wrapper.findAll('a').filter((a) => a.text().includes('Customize the dashboard'))

  it.each(CANNOT_WRITE_LAYOUT)('does not offer a $who the reset or the customize link, says why, and sends no settings save', async ({ me }) => {
    const wrapper = await open(AppearanceSettings, me)
    const usable = resetButtons(wrapper).filter((b) => !(b.element as HTMLButtonElement).disabled)
    expect(usable, 'an enabled "Reset dashboard layout" button').toHaveLength(0)
    expect(customizeLinks(wrapper), 'a "Customize the dashboard" link to a page without the control').toHaveLength(0)
    expect(wrapper.text()).toMatch(/only an admin can rearrange or reset the dashboard/i)
    for (const button of resetButtons(wrapper)) await button.trigger('click')
    await flushPromises()
    expect(api.updateSettings).not.toHaveBeenCalled()
  })

  it('still lets an admin reset it and customize it (not over-gated)', async () => {
    const wrapper = await open(AppearanceSettings, ADMIN)
    expect(customizeLinks(wrapper)).toHaveLength(1)
    expect(wrapper.text()).not.toMatch(/only an admin can rearrange or reset the dashboard/i)
    const reset = resetButtons(wrapper)
    expect(reset).toHaveLength(1)
    expect((reset[0]!.element as HTMLButtonElement).disabled).toBe(false)
    await reset[0]!.trigger('click')
    await flushPromises()
    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.updateSettings).mock.calls[0]![0]).toEqual({ ui: { dashboard: null } })
  })
})

describe('card 2367: Dashboard Customize needs admin rights', () => {
  it.each(CANNOT_WRITE_LAYOUT)('shows a $who no Customize button', async ({ me }) => {
    const wrapper = await open(DashboardPage, me)
    expect(wrapper.find('[data-testid="customize"]').exists()).toBe(false)
    expect(api.updateSettings).not.toHaveBeenCalled()
  })

  it('still shows an admin the Customize button', async () => {
    const wrapper = await open(DashboardPage, ADMIN)
    expect(wrapper.find('[data-testid="customize"]').exists()).toBe(true)
  })
})

// The Bitcoin and Odds & costs pages are both thin wrappers around CustomizablePage, so it carries the rule for both.
describe.each(['bitcoin_page', 'odds_page'] as const)('card 2367: %s Customize needs admin rights', (pageKey) => {
  const props = { pageKey, cards: [{ id: 'one', title: 'One' }, { id: 'two', title: 'Two' }], gridClass: 'grid' }
  const slots = { heading: '<h2>Heading</h2>', one: '<p>First card</p>', two: '<p>Second card</p>' }

  it.each(CANNOT_WRITE_LAYOUT)('shows a $who no Customize button', async ({ me }) => {
    const wrapper = await open(CustomizablePage, me, { props, slots })
    expect(wrapper.find('[data-testid="customize"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('First card')
    expect(api.updateSettings).not.toHaveBeenCalled()
  })

  it('still shows an admin the Customize button', async () => {
    const wrapper = await open(CustomizablePage, ADMIN, { props, slots })
    expect(wrapper.find('[data-testid="customize"]').exists()).toBe(true)
  })
})
