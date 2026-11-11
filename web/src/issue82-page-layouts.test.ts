import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { Component } from 'vue'
import { api } from '@/lib/api'
import type { NetworkState, Odds, Settings } from '@/lib/types'
import { mergeSettings, useSettings } from '@/stores/settings'
import { useSession } from '@/stores/session'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import BitcoinPage from '@/pages/BitcoinPage.vue'
import OddsPage from '@/pages/OddsPage.vue'

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

interface Card {
  title: string
  /** Finds the card's real content on the page, in edit mode (as a preview) and out of it. */
  selector: string
}
interface PageCase {
  name: string
  key: 'bitcoin_page' | 'odds_page'
  page: Component
  /** The default layout, in order. */
  cards: Card[]
  /** A link that lives inside one of the cards. */
  link: string
}

const byLabel = (title: string): Card => ({ title, selector: `[aria-label="${title}"]` })
const BITCOIN: PageCase = {
  name: 'Bitcoin',
  key: 'bitcoin_page',
  page: BitcoinPage,
  cards: ['Key numbers', 'Difficulty adjustment', 'Next halving', 'Your Bitcoin node', 'Your pool', 'Latest blocks', 'Blocks you found', 'Data sources'].map(byLabel),
  link: '/settings/sources',
}
const ODDS: PageCase = {
  name: 'Odds & costs',
  key: 'odds_page',
  page: OddsPage,
  cards: [
    { title: 'Your chance of finding a block', selector: '[data-testid="odds-hero"]' },
    byLabel('Chance over time'),
    byLabel('Electricity vs. payout'),
    byLabel('Work done so far'),
    byLabel('In plain English'),
  ],
  link: '/settings/energy',
}
const CASES: PageCase[] = [BITCOIN, ODDS]
const otherCase = (c: PageCase): PageCase => (c === BITCOIN ? ODDS : BITCOIN)

function config(): Settings {
  // Settings as an older release saved them: no page layouts at all. No backend, credentials or private data.
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null },
  } as Settings
}

const horizon = (probability: number) => ({ seconds: 600, probability, one_in: 1 / probability })
const NETWORK = {
  updated_at: 1,
  available: true,
  source: 'fixture',
  height: 900000,
  tip_hash: 'aa',
  tip_time: 1,
  difficulty: 1e14,
  network_hashrate_hs: 1e20,
  block_reward_btc: 3.125,
  subsidy_btc: 3.125,
  avg_fees_btc: null,
  epoch: { height: 900000, epoch_start_height: 897984, next_retarget_height: 900000, blocks_into_epoch: 1000, blocks_remaining: 1016, progress: 0.5, seconds_remaining: 600000, estimated_date: '2030-01-01', estimated_change_pct: 1.5 },
  halving: { height: 900000, next_halving_height: 1050000, blocks_remaining: 150000, seconds_remaining: 90000000, estimated_date: '2032-01-01', subsidy_now_btc: 3.125, subsidy_next_btc: 1.5625, progress: 0.2 },
  mempool_tx_count: null,
  mempool_vsize: null,
  fees_sat_vb: null,
  prices: null,
  btc_price: 60000,
  node: null,
  pools: [],
  sources: [],
  warnings: [],
  stale: false,
  node_behind_by: null,
} as unknown as NetworkState
const ODDS_DATA = {
  available: true,
  hashrate: 1e13,
  difficulty: 1e14,
  network_hashrate: 1e20,
  share_of_network: 1e-7,
  blocks_per_day: 144,
  expected_seconds: 1e9,
  median_seconds: 7e8,
  difficulty_growth_per_year: 0,
  horizons: {
    ten_minutes: horizon(1e-6), hour: horizon(1e-5), day: horizon(1e-4), week: horizon(1e-3),
    month: horizon(1e-3), year: horizon(1e-2), five_years: horizon(5e-2), ten_years: horizon(1e-1),
  },
  live: true,
  economics: {
    price_per_kwh: 0.12, btc_price: 60000, cost_per_day: 1, cost_per_month: 30, cost_per_year: 365, block_reward_btc: 3.125,
    expected_value_per_day: 0.5, expected_value_per_year: 180, ev_to_cost_ratio: 0.5, break_even_btc_price: 120000,
    power_w: 100, power_complete: true, cost_note: null, currency: 'USD',
  },
  work: { total_hashes: 1e18, expected_blocks_of_work: 1e-6, chance_found_by_now: 1e-6, blocks_found: 0 },
  best_share: { difficulty: 1e6, progress_to_block: 1e-5, device_id: null },
  plain_english: ['Solo mining is a lottery.'],
} as unknown as Odds

const wrappers: { unmount: () => void }[] = []
let server: Settings

async function mountPage(c: PageCase) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(c.page, { attachTo: document.body, global: { plugins: [router] } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
async function openEditor(c: PageCase) {
  const wrapper = await mountPage(c)
  await wrapper.get('[data-testid="customize"]').trigger('click')
  await flushPromises()
  return wrapper
}

function order(c: PageCase): string[] {
  const found = Array.from(document.querySelectorAll(c.cards.map((card) => card.selector).join(',')))
  return found.map((el) => c.cards.find((card) => el.matches(card.selector))!.title)
}
const titles = (c: PageCase): string[] => c.cards.map((card) => card.title)
const control = (title: string, direction: 'earlier' | 'later'): HTMLButtonElement | null =>
  document.querySelector<HTMLButtonElement>(`[aria-label="Move ${title} ${direction}"]`)
const hideControl = (title: string): HTMLButtonElement | null => document.querySelector<HTMLButtonElement>(`[aria-label="Hide ${title}"]`)
const showControl = (title: string): HTMLButtonElement | null => document.querySelector<HTMLButtonElement>(`[aria-label="Show ${title}"]`)
const buttonNamed = (name: string): HTMLButtonElement | undefined => Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.trim() === name)

async function press(button: HTMLButtonElement | null | undefined, what: string): Promise<void> {
  if (!button) throw new Error(`No "${what}" control on the page`)
  button.click()
  await flushPromises()
}
async function move(title: string, direction: 'earlier' | 'later'): Promise<void> {
  await press(control(title, direction), `Move ${title} ${direction}`)
}
const done = (): Promise<void> => press(document.querySelector<HTMLButtonElement>('[data-testid="customize-done"]'), 'Done')

/** Bring the last card to the front, one keyboard step at a time. Returns the layout that gives. */
async function lastToFront(c: PageCase): Promise<string[]> {
  const all = titles(c)
  const last = all[all.length - 1]!
  for (let step = 0; step < all.length - 1; step++) await move(last, 'earlier')
  return [last, ...all.slice(0, -1)]
}

function isInert(el: HTMLElement): boolean {
  for (let node: HTMLElement | null = el; node; node = node.parentElement) {
    if (node.hasAttribute('inert') || node.inert === true) return true
  }
  return false
}

function lastSaved(): { ui: Record<string, unknown> } {
  const calls = vi.mocked(api.updateSettings).mock.calls
  return calls[calls.length - 1]![0] as { ui: Record<string, unknown> }
}

beforeEach(() => {
  setActivePinia(createPinia())
  const session = useSession()
  session.state = 'ready'
  session.me = { name: 'tester', scope: 'admin', via: 'token' }
  server = config()
  useSettings().data = config()
  const live = useLive()
  live.loaded = true
  live.network = NETWORK
  live.odds = ODDS_DATA
  vi.spyOn(api, 'updateSettings').mockImplementation(async (body) => {
    server = mergeSettings(server, body)
    return server
  })
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks()
})

describe.each(CASES)('issue 82: $name page can be customized like the Dashboard', (c) => {
  it('shows the cards in the default order when the saved settings have no layout for it', async () => {
    await mountPage(c)
    expect(order(c)).toEqual(titles(c))
  })

  it('offers Customize to people who can change settings, and not to read-only viewers', async () => {
    useSession().me = { name: 'viewer', scope: 'read', via: 'public' }
    const wrapper = await mountPage(c)
    expect(wrapper.find('[data-testid="customize"]').exists()).toBe(false)
    wrappers.splice(0).forEach((w) => w.unmount())
    useSession().me = { name: 'tester', scope: 'admin', via: 'token' }
    const admin = await mountPage(c)
    expect(admin.find('[data-testid="customize"]').exists()).toBe(true)
  })

  it('moves cards with the keyboard-reachable controls, keeps focus and announces the position', async () => {
    const wrapper = await openEditor(c)
    expect(order(c)).toEqual(titles(c))
    const first = titles(c)[0]!
    expect(control(first, 'earlier')?.disabled).toBe(true)
    expect(control(first, 'later')?.disabled).toBe(false)

    await move(first, 'later')
    expect(order(c).indexOf(first)).toBe(1)
    expect(document.activeElement).toBe(control(first, 'later'))
    expect(wrapper.get('[data-testid="reorder-announcement"]').text()).toBe(`${first} moved to position 2 of ${c.cards.length}`)

    const last = titles(c)[c.cards.length - 1]!
    expect(control(last, 'later')?.disabled).toBe(true)
  })

  it('makes the card previews inert while editing, so Tab only reaches the editing controls', async () => {
    const wrapper = await mountPage(c)
    const links = (): HTMLElement[] => Array.from(document.querySelectorAll<HTMLElement>(`a[href="${c.link}"]`))
    expect(links().length).toBeGreaterThan(0)
    for (const el of links()) expect(isInert(el)).toBe(false)
    await wrapper.get('[data-testid="customize"]').trigger('click')
    await flushPromises()
    expect(links().length).toBeGreaterThan(0)
    for (const el of links()) expect(isInert(el)).toBe(true)
  })

  it('saves a reordered layout for this page only, and shows it again on the next visit', async () => {
    await openEditor(c)
    const expected = await lastToFront(c)
    expect(order(c)).toEqual(expected)
    expect(vi.mocked(api.updateSettings)).not.toHaveBeenCalled()
    await done()

    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(Object.keys(lastSaved().ui)).toEqual([c.key])
    expect(document.querySelector('[data-testid="customize-done"]')).toBeNull()
    expect(order(c)).toEqual(expected)

    // A later visit reads the layout from the saved settings.
    wrappers.splice(0).forEach((w) => w.unmount())
    await mountPage(c)
    expect(order(c)).toEqual(expected)
    // The other page, and the saved copy of its layout, are untouched.
    wrappers.splice(0).forEach((w) => w.unmount())
    await mountPage(otherCase(c))
    expect(order(otherCase(c))).toEqual(titles(otherCase(c)))
  })

  it('hides a card, offers it back while editing, and keeps it hidden once saved', async () => {
    await openEditor(c)
    const gone = titles(c)[1]!
    await press(hideControl(gone), `Hide ${gone}`)
    expect(order(c)).toEqual(titles(c).filter((t) => t !== gone))

    await press(showControl(gone), `Show ${gone}`)
    expect(order(c)).toEqual([...titles(c).filter((t) => t !== gone), gone])
    await press(hideControl(gone), `Hide ${gone}`)
    await done()

    wrappers.splice(0).forEach((w) => w.unmount())
    await mountPage(c)
    expect(order(c)).toEqual(titles(c).filter((t) => t !== gone))
  })

  it('resets this page to its default and leaves the other pages and their saved layouts alone', async () => {
    const other = otherCase(c)
    await openEditor(other)
    const otherLayout = await lastToFront(other)
    await done()
    wrappers.splice(0).forEach((w) => w.unmount())

    await openEditor(c)
    await lastToFront(c)
    await done()
    wrappers.splice(0).forEach((w) => w.unmount())

    await openEditor(c)
    await press(buttonNamed('Reset'), 'Reset')
    expect(lastSaved()).toEqual({ ui: { [c.key]: null } })
    expect(order(c)).toEqual(titles(c))
    await done()
    wrappers.splice(0).forEach((w) => w.unmount())

    await mountPage(c)
    expect(order(c)).toEqual(titles(c))
    wrappers.splice(0).forEach((w) => w.unmount())
    await mountPage(other)
    expect(order(other)).toEqual(otherLayout)
  })

  it('shows an error and keeps the draft when saving fails', async () => {
    await openEditor(c)
    const expected = await lastToFront(c)
    vi.mocked(api.updateSettings).mockRejectedValueOnce(new Error('disk is full'))
    await done()

    expect(useToasts().items.some((t) => t.kind === 'error')).toBe(true)
    expect(document.querySelector('[data-testid="customize-done"]')).not.toBeNull()
    expect(order(c)).toEqual(expected)

    // Trying again with the same draft works.
    await done()
    expect(document.querySelector('[data-testid="customize-done"]')).toBeNull()
    expect(order(c)).toEqual(expected)
  })
})
