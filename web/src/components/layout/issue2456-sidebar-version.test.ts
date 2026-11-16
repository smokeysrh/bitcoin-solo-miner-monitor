import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import type { Meta } from '@/lib/types'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'

// Card #2456: the running version ("v1.5.0") sits in the sidebar's bottom row, right of the Collapse button.
// It is data only (session.meta.version, already loaded at start-up): no request, no label, no placeholder.

vi.mock('@/components/ui/Tooltip.vue', async () => {
  const { defineComponent } = await import('vue')
  return { default: defineComponent({ props: ['text', 'side', 'delay'], setup: (_props, { slots }) => () => slots.default?.() }) }
})

const VERSION = '1.5.0'
const VERSION_TEST_ID = '[data-testid="sidebar-version"]'

const wrappers: { unmount: () => void }[] = []

function mountSidebar(opts: { collapsed: boolean; version?: string | null }) {
  const session = useSession()
  // Only the field under test is set; the rest of Meta is irrelevant to the sidebar.
  session.meta = opts.version === null ? null : ({ version: opts.version } as Meta)
  useUi().sidebarCollapsed = opts.collapsed
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:rest(.*)*', component: { render: () => null } }] })
  const wrapper = mount(SidebarNav, { global: { plugins: [router] } })
  wrappers.push(wrapper)
  return wrapper
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.unstubAllGlobals()
})

describe('issue 2456: version in the sidebar footer', () => {
  it('shows v + the store version as plain muted text on the Collapse row, right of the button', () => {
    const w = mountSidebar({ collapsed: false, version: VERSION })
    const version = w.get(VERSION_TEST_ID)
    const collapse = w.get('button[aria-label="Collapse sidebar"]')
    expect(version.text()).toBe(`v${VERSION}`)
    expect(version.element.parentElement).toBe(collapse.element.parentElement) // same row
    expect(collapse.element.nextElementSibling).toBe(version.element) // to its right
    expect(collapse.element.contains(version.element)).toBe(false) // the button keeps its own name
    expect(version.element.closest('a')).toBeNull() // plain text, no link
    expect(version.classes()).toEqual(expect.arrayContaining(['tnum', 'text-subtle', 'whitespace-nowrap', 'shrink-0']))
  })

  it('does not wrap or squeeze the Collapse button: the button is the flexible part of the row', () => {
    const w = mountSidebar({ collapsed: false, version: VERSION })
    const collapse = w.get('button[aria-label="Collapse sidebar"]')
    expect(collapse.element.parentElement?.classList.contains('flex')).toBe(true)
    expect(collapse.classes()).toEqual(expect.arrayContaining(['min-w-0', 'flex-1']))
  })

  it.each([
    ['no meta loaded yet', null],
    ['meta without a version', undefined],
    ['an empty version', ''],
    ['a blank version', '  '],
  ])('renders nothing for %s', (_name, version) => {
    const w = mountSidebar({ collapsed: false, version })
    expect(w.find(VERSION_TEST_ID).exists()).toBe(false)
    expect(w.text()).not.toMatch(/undefined|null|\bv\s*$/)
  })

  it('is hidden when the sidebar is collapsed to icons', () => {
    const w = mountSidebar({ collapsed: true, version: VERSION })
    expect(w.find(VERSION_TEST_ID).exists()).toBe(false)
    expect(w.text()).not.toContain(VERSION)
    expect(w.find('button[aria-label="Expand sidebar"]').exists()).toBe(true)
  })
})
