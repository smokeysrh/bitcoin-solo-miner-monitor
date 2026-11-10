import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { h, type Component } from 'vue'
import Button from '@/components/ui/Button.vue'
import MobileNav from '@/components/layout/MobileNav.vue'
import TopBar from '@/components/layout/TopBar.vue'

// Issue 76: the wall display must be a real control in the top bar (desktop) and in the bottom navigation (phones),
// not only an item inside a closed menu or a closed "More" sheet.
//
// The dropdown menu and the "More" sheet are replaced by stand-ins that render only their trigger / nothing, so any
// "Wall display" control found below is guaranteed to be reachable without opening a menu. TopBar and MobileNav are real.
vi.mock('@/components/ui/Menu.vue', async () => {
  const { defineComponent } = await import('vue')
  return { default: defineComponent({ props: ['items', 'align'], setup: (_props, { slots }) => () => slots.default?.() }) }
})
vi.mock('@/components/ui/Tooltip.vue', async () => {
  const { defineComponent } = await import('vue')
  return { default: defineComponent({ props: ['text', 'side', 'delay'], setup: (_props, { slots }) => () => slots.default?.() }) }
})
vi.mock('@/components/ui/Dialog.vue', async () => {
  const { defineComponent } = await import('vue')
  return { default: defineComponent({ inheritAttrs: false, props: ['open', 'title', 'side', 'size'], emits: ['update:open'], setup: () => () => null }) }
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

/** Links and buttons inside `root` whose accessible name is exactly `name`. */
function controlsNamed(root: Element, name: string): HTMLElement[] {
  return [...root.querySelectorAll<HTMLElement>('a, button')].filter((el) => accessibleName(el) === name)
}

async function mountWithRouter(component: Component) {
  const router = makeRouter()
  await router.push('/miners')
  await router.isReady()
  const wrapper = mount(component, { global: { plugins: [router] }, attachTo: document.body })
  wrappers.push(wrapper)
  return { router, wrapper }
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

describe('issue 76: wall display button in the desktop top bar', () => {
  it('is a focusable control named "Wall display" with its label shown, without opening any menu', async () => {
    const { wrapper } = await mountWithRouter(TopBar)
    const found = controlsNamed(wrapper.element, 'Wall display')
    expect(found).toHaveLength(1)
    const [control] = found
    expect(control!.getAttribute('tabindex')).not.toBe('-1')
    expect(control!.hasAttribute('disabled')).toBe(false)
    expect(control!.textContent).toContain('Wall display')
  })

  it('is a real link to /kiosk (an href makes it a link role and keyboard focusable)', async () => {
    const { wrapper } = await mountWithRouter(TopBar)
    const [control] = controlsNamed(wrapper.element, 'Wall display')
    expect(control!.tagName).toBe('A')
    expect(control!.getAttribute('href')).toBe('/kiosk')
  })

  it('opens /kiosk when activated', async () => {
    const { router, wrapper } = await mountWithRouter(TopBar)
    const [control] = controlsNamed(wrapper.element, 'Wall display')
    expect(control).toBeDefined()
    control!.click()
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/kiosk')
  })
})

describe('issue 76: wall display in the phone bottom navigation', () => {
  it('is one tap away inside the main navigation, not only in the "More" sheet', async () => {
    const { wrapper } = await mountWithRouter(MobileNav)
    const nav = wrapper.get('nav[aria-label="Main navigation"]').element
    const found = controlsNamed(nav, 'Wall display')
    expect(found).toHaveLength(1)
    expect(found[0]!.getAttribute('tabindex')).not.toBe('-1')
  })

  it('opens /kiosk from the first tap', async () => {
    const { router, wrapper } = await mountWithRouter(MobileNav)
    const nav = wrapper.get('nav[aria-label="Main navigation"]').element
    const [control] = controlsNamed(nav, 'Wall display')
    expect(control).toBeDefined()
    control!.click()
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/kiosk')
  })
})

describe('issue 76: Button renders a real link when given a target', () => {
  it('<Button to> is an <a> with the router href', async () => {
    const { wrapper } = await mountWithRouter({ render: () => h(Button, { to: '/x' }, () => 'Go') })
    const link = wrapper.get('a')
    expect(link.attributes('href')).toBe('/x')
  })

  it('<Button href> is an <a> with that href and no button type', () => {
    const wrapper = mount(Button, { props: { href: '/llms.txt' }, slots: { default: 'Read' } })
    wrappers.push(wrapper)
    expect(wrapper.element.tagName).toBe('A')
    expect(wrapper.element.getAttribute('href')).toBe('/llms.txt')
    expect(wrapper.element.hasAttribute('type')).toBe(false)
  })

  it('a plain <Button> stays a button of type "button" without link attributes', () => {
    const wrapper = mount(Button, { slots: { default: 'Save' } })
    wrappers.push(wrapper)
    expect(wrapper.element.tagName).toBe('BUTTON')
    expect(wrapper.element.getAttribute('type')).toBe('button')
    expect(wrapper.element.hasAttribute('href')).toBe(false)
  })
})
