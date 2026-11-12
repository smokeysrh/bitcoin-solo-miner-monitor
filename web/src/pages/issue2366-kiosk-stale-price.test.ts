import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import KioskPage from '@/pages/KioskPage.vue'
import { api } from '@/lib/api'
import type { NetworkState, Settings } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSettings } from '@/stores/settings'

// Issue 2366: the wall display shows the bitcoin price from the network snapshot. When the price source stops
// answering, the snapshot keeps the last price and marks `field_sources.prices.stale`. From across a room an old
// price looks current, so the wall display says plainly, in words, that the price is not updating and how old it is.
// A fresh price looks as before, and an unavailable price still says "Unavailable" (never zero, never a stale note).

const PRICE = 82_000
const SECONDS_PER_HOUR = 3600
const STALE_PRICE_AGE_S = 2 * SECONDS_PER_HOUR + 30 // reads as "2h ago" however long the test takes
const STALE_NOTE_ID = 'kiosk-price-stale'

type PriceSource = 'mempool' | 'manual' | 'none'
type FieldSources = NonNullable<NetworkState['field_sources']>

const nowSeconds = (): number => Date.now() / 1000
const priceField = (stale: boolean): FieldSources => ({ prices: { source: 'mempool_space', ts: nowSeconds() - STALE_PRICE_AGE_S, stale } })

function network(over: Partial<NetworkState> = {}): NetworkState {
  return {
    updated_at: 1_700_000_000,
    available: true,
    source: 'demo',
    height: 926_544,
    tip_hash: null,
    tip_time: null,
    difficulty: 1.1e14,
    network_hashrate_hs: null,
    block_reward_btc: 3.125,
    subsidy_btc: 3.125,
    avg_fees_btc: null,
    epoch: null,
    halving: null,
    mempool_tx_count: null,
    mempool_vsize: null,
    fees_sat_vb: null,
    prices: { USD: PRICE },
    btc_price: PRICE,
    node: null,
    pools: [],
    sources: [],
    warnings: [],
    stale: false,
    node_behind_by: null,
    ...over,
  }
}

let pinia: Pinia
const wrappers: { unmount: () => void }[] = []

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.useRealTimers()
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

/** Mounts the real wall display on its network panel with the given live network state. */
async function networkPanel(net: NetworkState | null, priceSource: PriceSource = 'mempool') {
  useSettings().data = {
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, kiosk: { rotate_s: 600, panels: ['network'], show_clock: false } },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    network: { price_source: priceSource },
  } as unknown as Settings
  useLive().network = net
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:rest(.*)*', component: { template: '<div />' } }] })
  await router.push('/kiosk')
  await router.isReady()
  const wrapper = mount(KioskPage, { global: { plugins: [pinia, router], stubs: { HistoryChart: true, MinerTile: true, LiveBadge: true } } })
  wrappers.push(wrapper)
  await flushPromises()
  const section = wrapper.find('section[aria-label="network"]')
  expect(section.exists()).toBe(true)
  return section
}

describe('issue 2366: wall display price freshness', () => {
  it('says in words that a stale price is not updating, and how old it is, next to the price', async () => {
    const section = await networkPanel(network({ field_sources: priceField(true) }))
    const note = section.find(`[data-testid="${STALE_NOTE_ID}"]`)
    expect(note.exists()).toBe(true)
    expect(note.text()).toBe('Price not updating (last updated 2h ago)')
    // the old price stays visible, it is labelled rather than hidden
    expect(section.get('[data-testid="kiosk-price-value"]').text()).toContain('82,000')
    // same cell as the price, so it reads as part of it
    expect(section.get('[data-testid="kiosk-price-value"]').element.parentElement?.contains(note.element)).toBe(true)
  })

  it('keeps the wall display list valid while the note shows (only dt/dd inside the dl and its groups)', async () => {
    const section = await networkPanel(network({ field_sources: priceField(true) }))
    expect(section.find(`[data-testid="${STALE_NOTE_ID}"]`).exists()).toBe(true)
    const group = section.get('[data-testid="kiosk-price-value"]').element.parentElement
    const list = group?.parentElement
    expect(list?.tagName).toBe('DL')
    const childrenOf = (parent: Element | null | undefined): Element[] => (parent ? Array.from(parent.children) : [])
    const tagNames = (parent: Element | null | undefined): string[] => childrenOf(parent).map((child) => child.tagName)
    const allowed = ['DT', 'DD']
    expect(tagNames(group).length).toBeGreaterThan(0)
    expect(tagNames(group).filter((tag) => !allowed.includes(tag))).toEqual([])
    const groups = childrenOf(list)
    expect(groups.length).toBeGreaterThan(0)
    for (const child of groups) {
      if (child.tagName === 'DIV') expect(tagNames(child).filter((tag) => !allowed.includes(tag))).toEqual([])
      else expect(allowed).toContain(child.tagName)
    }
  })

  it('sizes the note for the wall (the panel note size, not small print)', async () => {
    const section = await networkPanel(network({ field_sources: priceField(true) }))
    const note = section.get(`[data-testid="${STALE_NOTE_ID}"]`)
    expect(note.classes()).toContain('k-note')
    expect(note.classes()).not.toContain('text-xs')
    expect(note.classes()).not.toContain('text-sm')
  })

  it('looks as before when the price is fresh', async () => {
    const section = await networkPanel(network({ field_sources: priceField(false) }))
    expect(section.find(`[data-testid="${STALE_NOTE_ID}"]`).exists()).toBe(false)
    expect(section.text()).not.toContain('not updating')
    expect(section.get('[data-testid="kiosk-price-value"]').text()).toContain('82,000')
  })

  it('adds no note when the snapshot carries no price freshness at all', async () => {
    const section = await networkPanel(network())
    expect(section.find(`[data-testid="${STALE_NOTE_ID}"]`).exists()).toBe(false)
    expect(section.get('[data-testid="kiosk-price-value"]').text()).toContain('82,000')
  })

  it('keeps Unavailable (and no stale note) when there is no price, even if its source is marked stale', async () => {
    const section = await networkPanel(network({ btc_price: null, prices: null, field_sources: priceField(true) }))
    const value = section.get('[data-testid="kiosk-price-value"]')
    expect(value.text()).toBe('Unavailable')
    expect(value.classes()).toContain('text-muted')
    expect(section.find(`[data-testid="${STALE_NOTE_ID}"]`).exists()).toBe(false)
  })

  it('treats a zero price as unavailable, not as a stale zero', async () => {
    const section = await networkPanel(network({ btc_price: 0, field_sources: priceField(true) }))
    expect(section.get('[data-testid="kiosk-price-value"]').text()).toBe('Unavailable')
    expect(section.find(`[data-testid="${STALE_NOTE_ID}"]`).exists()).toBe(false)
  })

  it('does not call a price you typed in yourself stale, even if the mempool.space price behind it is', async () => {
    const section = await networkPanel(network({ field_sources: priceField(true) }), 'manual')
    expect(section.find(`[data-testid="${STALE_NOTE_ID}"]`).exists()).toBe(false)
    expect(section.get('[data-testid="kiosk-price-value"]').text()).toContain('82,000')
  })
})

describe('issue 2366: wall display chart stale notice', () => {
  it('is large enough to read from across a room, and unchanged on a normal chart', async () => {
    vi.useFakeTimers()
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    const history = vi.spyOn(api, 'fleetHistory').mockResolvedValue({ step: 1, source: 'fixture', t: [1, 2], series: { hashrate_hs: [1, 2] } })
    const stubs = { TimeSeriesChart: { props: ['t', 'series'], template: '<div data-testid="chart" />' } }
    const wall = mount(HistoryChart, { props: { metrics: ['hashrate_hs'], range: '24h', refreshMs: 1000, kiosk: true }, global: { plugins: [pinia], stubs } })
    const normal = mount(HistoryChart, { props: { metrics: ['hashrate_hs'], range: '24h', refreshMs: 1000 }, global: { plugins: [pinia], stubs } })
    wrappers.push(wall, normal)
    await flushPromises()
    history.mockRejectedValue(new Error('refresh failed'))
    await vi.advanceTimersByTimeAsync(1000)
    await flushPromises()
    const wallNotice = wall.get('[role="status"]')
    expect(wallNotice.text()).toContain('Chart is stale')
    expect(wallNotice.classes()).toContain('text-xl')
    expect(wallNotice.classes()).not.toContain('text-sm')
    const normalNotice = normal.get('[role="status"]')
    expect(normalNotice.classes()).toContain('text-sm')
    expect(normalNotice.classes()).not.toContain('text-xl')
  })
})
