import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { useUi } from '@/stores/ui'
import LogoMark from '@/components/brand/LogoMark.vue'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { BRAND_ASSETS } from '@/lib/brand'

// Card #2390: the sidebar header and the logo mark show the supplied HashHurdr artwork.
// File-level checks (manifest, page head, service worker) are in issue2390-brand-files.test.ts.

vi.mock('@/components/ui/Tooltip.vue', async () => {
  const { defineComponent } = await import('vue')
  return { default: defineComponent({ props: ['text', 'side', 'delay'], setup: (_props, { slots }) => () => slots.default?.() }) }
})

const SYMBOL = '/brand/hashhurdr-symbol.svg'
const LOCKUP_DARK = '/brand/hashhurdr-lockup-horizontal-dark.svg'
const LOCKUP_LIGHT = '/brand/hashhurdr-lockup-horizontal-light.svg'

const wrappers: { unmount: () => void }[] = []
function mountSidebar(collapsed: boolean) {
  useUi().sidebarCollapsed = collapsed
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

describe('issue 2390: brand file URLs', () => {
  // The components and the tests spell the URLs independently, so a rename of either side fails here.
  // The URL must stay a plain path to the public file (never a data: URI), so the built app serves the kit file unchanged.
  // That each URL names an existing file is checked in issue2390-brand-files.test.ts, which runs in the node environment.
  it('are plain public paths', () => {
    expect(Object.values(BRAND_ASSETS).sort()).toEqual([LOCKUP_DARK, LOCKUP_LIGHT, SYMBOL].sort())
    for (const url of Object.values(BRAND_ASSETS)) {
      expect(url.startsWith('/brand/')).toBe(true)
    }
  })
})

describe('issue 2390: sidebar header', () => {
  it('shows the horizontal lockup, one file per background, both named HashHurdr', () => {
    const w = mountSidebar(false)
    const dark = w.get(`img[src="${LOCKUP_DARK}"]`)
    const light = w.get(`img[src="${LOCKUP_LIGHT}"]`)
    expect(dark.attributes('alt')).toBe('HashHurdr')
    expect(light.attributes('alt')).toBe('HashHurdr')
    expect(dark.classes()).toContain('light:hidden') // the dark-background file hides itself in the light theme
    expect(light.classes()).toEqual(expect.arrayContaining(['hidden', 'light:block'])) // the light-background file appears only there
    expect(w.text()).not.toContain('Solo Miner Monitor')
  })

  it('shows only the symbol when collapsed', () => {
    const w = mountSidebar(true)
    expect(w.get(`img[src="${SYMBOL}"]`).attributes('alt')).toBe('HashHurdr')
    expect(w.find(`img[src="${LOCKUP_DARK}"]`).exists()).toBe(false)
  })
})

describe('issue 2390: logo mark', () => {
  it('is the supplied symbol at the requested size, named unless the caller says it is decoration', () => {
    const named = mount(LogoMark, { props: { size: 64 } })
    wrappers.push(named)
    expect(named.get('img').attributes()).toMatchObject({ src: SYMBOL, alt: 'HashHurdr logo', width: '64', height: '64' })
    const decorative = mount(LogoMark, { props: { size: 32, alt: '' } })
    wrappers.push(decorative)
    expect(decorative.get('img').attributes('alt')).toBe('')
  })
})
