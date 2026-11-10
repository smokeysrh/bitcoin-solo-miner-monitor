import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { NAV } from '@/lib/nav'
import { useLive } from '@/stores/live'
import { useUi } from '@/stores/ui'
import CommandPalette from '@/components/layout/CommandPalette.vue'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import RangePicker from '@/components/ui/RangePicker.vue'

// happy-dom has no portal focus trap or tooltip provider: render the dialog and tooltip content inline.
// The palette, sidebar and range picker themselves are the real components.
vi.mock('reka-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('reka-ui')>()
  const { defineComponent, h } = await import('vue')
  const inline = defineComponent({ setup: (_props, { slots }) => () => h('div', slots.default?.()) })
  return { ...actual, DialogRoot: inline, DialogPortal: inline, DialogOverlay: inline, DialogContent: inline, DialogTitle: inline, DialogDescription: inline }
})
vi.mock('@/components/ui/Tooltip.vue', async () => {
  const { defineComponent } = await import('vue')
  return { default: defineComponent({ props: ['text', 'side', 'delay'], setup: (_props, { slots }) => () => slots.default?.() }) }
})

const wrappers: { unmount: () => void }[] = []
function makeRouter() {
  return createRouter({ history: createMemoryHistory(), routes: [{ path: '/:rest(.*)*', component: { render: () => null } }] })
}

/** Accessible name by the content rule: aria-label wins, aria-hidden is skipped, otherwise the text of the children. */
function accessibleName(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? ''
  if (!(node instanceof Element) || node.getAttribute('aria-hidden') === 'true') return ''
  const label = node.getAttribute('aria-label')
  if (label) return label
  return [...node.childNodes].map(accessibleName).join(' ').replace(/\s+/g, ' ').trim()
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { value: vi.fn(), configurable: true })
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

describe('issue 42: collapsed sidebar keeps its link names', () => {
  function mountSidebar(collapsed: boolean) {
    const ui = useUi(); ui.sidebarCollapsed = collapsed
    useLive().alerts = [{}, {}] as never
    const wrapper = mount(SidebarNav, { global: { plugins: [makeRouter()] } }); wrappers.push(wrapper)
    return wrapper
  }

  it('every collapsed link is named by its page and points at its page', () => {
    const wrapper = mountSidebar(true)
    for (const item of NAV) {
      const link = wrapper.get(`[data-testid="nav-${item.name}"]`)
      expect(link.attributes('href')).toBe(item.to)
      expect(accessibleName(link.element), item.name).toContain(item.label)
    }
  })

  it('expanded links stay named by their page', () => {
    const wrapper = mountSidebar(false)
    for (const item of NAV) expect(accessibleName(wrapper.get(`[data-testid="nav-${item.name}"]`).element), item.name).toContain(item.label)
  })
})

describe('issue 42: command palette arrows follow the displayed order', () => {
  // "dash" ranks Pages/Dashboard and Miners/Dash Rig first, then Pages/Wall display: the ranking interleaves Pages and Miners.
  async function openWithInterleavedMatches() {
    const live = useLive()
    live.devicesById = { d1: { id: 'd1', name: 'Dash Rig', model: 'bitaxe gamma', model_override: null, host: '10.0.0.9', tags: [], status: 'online' } as never }
    const router = makeRouter()
    const push = vi.spyOn(router, 'push').mockResolvedValue(undefined)
    const wrapper = mount(CommandPalette, { global: { plugins: [router] } }); wrappers.push(wrapper)
    const input = wrapper.get('[data-testid="palette-input"]')
    await input.setValue('dash')
    const shown = (): string[] => wrapper.findAll('[role="option"]').map((o) => o.attributes('id') ?? '')
    const selected = (): string | undefined => wrapper.find('[role="option"][aria-selected="true"]').attributes('id')
    const press = async (key: string): Promise<void> => { await input.trigger('keydown', { key }) }
    return { input, push, shown, selected, press }
  }

  it('Down and Up move to the next and previous visible row', async () => {
    const { shown, selected, press } = await openWithInterleavedMatches()
    const ids = shown()
    expect(ids).toEqual(expect.arrayContaining(['cmd-nav-dashboard', 'cmd-nav-kiosk', 'cmd-dev-d1']))
    expect(selected()).toBe(ids[0])
    for (let i = 1; i < ids.length; i++) {
      await press('ArrowDown')
      expect(selected(), `Down to row ${i}`).toBe(ids[i])
    }
    await press('ArrowDown')
    expect(selected(), 'Down wraps to the first row').toBe(ids[0])
    await press('ArrowUp')
    expect(selected(), 'Up wraps to the last row').toBe(ids[ids.length - 1])
    await press('ArrowUp')
    expect(selected(), 'Up to the previous row').toBe(ids[ids.length - 2])
  })

  it('Enter runs the row that is highlighted on screen', async () => {
    const { push, shown, press } = await openWithInterleavedMatches()
    const destination: Record<string, string> = { 'cmd-nav-dashboard': '/', 'cmd-nav-kiosk': '/kiosk', 'cmd-dev-d1': '/miners/d1' }
    const second = shown()[1] ?? ''
    expect(destination[second], `second visible row ${second}`).toBeDefined()
    await press('ArrowDown')
    await press('Enter')
    expect(push).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledWith(destination[second])
  })
})

describe('issue 42: long range selector fits a narrow card', () => {
  it('keeps all seven choices reachable inside a width-limited, scrollable group', () => {
    const ranges = ['1h', '6h', '24h', '7d', '30d', '90d', '1y']
    const wrapper = mount(RangePicker, { props: { modelValue: '24h', ranges } }); wrappers.push(wrapper)
    const group = wrapper.get('[role="radiogroup"]')
    expect(group.findAll('[role="radio"]').map((r) => r.text())).toEqual(ranges)
    // happy-dom does no layout, so the containment contract is checked on the element that must provide it.
    expect(group.classes()).toContain('max-w-full')
    expect(group.classes()).toContain('overflow-x-auto')
  })
})
