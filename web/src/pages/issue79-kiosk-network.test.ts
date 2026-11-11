import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import KioskPage from '@/pages/KioskPage.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import type { EpochInfo, HalvingInfo, NetworkState, Settings } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSettings } from '@/stores/settings'

// Issue 79: on the wall display the next halving leads the network panel, the next difficulty change follows, and
// height, difficulty and price are secondary. Missing or out-of-date data says "Unavailable", never zero.
// Type sizes need real CSS, so the halving-is-largest check lives in web/e2e/issue79-kiosk-network.spec.ts.

const halving: HalvingInfo = {
  height: 926_544,
  next_halving_height: 1_050_000,
  blocks_remaining: 123_456,
  seconds_remaining: 74_073_600,
  estimated_date: '2028-04-15T12:00:00+00:00',
  subsidy_now_btc: 3.125,
  subsidy_next_btc: 1.5625,
  progress: 0.41,
}
const epoch: EpochInfo = {
  height: 926_544,
  epoch_start_height: 925_755,
  next_retarget_height: 927_333,
  blocks_into_epoch: 1_227,
  blocks_remaining: 789,
  progress: 0.61,
  seconds_remaining: 473_400,
  estimated_date: '2026-11-21T12:00:00+00:00',
  estimated_change_pct: 1.5,
}

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
    epoch,
    halving,
    mempool_tx_count: null,
    mempool_vsize: null,
    fees_sat_vb: null,
    prices: null,
    btc_price: 82_000,
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
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

/** Mounts the real wall display on its network panel with the given live network state. */
async function networkPanel(net: NetworkState | null) {
  useSettings().data = {
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, kiosk: { rotate_s: 600, panels: ['network'], show_clock: false } },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
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
const unavailableCount = (text: string): number => text.match(/Unavailable/g)?.length ?? 0

describe('issue 79: wall display Bitcoin network panel', () => {
  it('leads with the halving, then the difficulty change, then height, difficulty and price', async () => {
    const section = await networkPanel(network())
    const text = section.text()
    const order = ['Next halving', 'Next difficulty change', 'Block height'].map((label) => text.indexOf(label))
    expect(order.every((i) => i >= 0)).toBe(true)
    expect(order).toEqual([...order].sort((a, b) => a - b))
    expect(text).toContain('123,456')
    expect(text).toContain('789')
    // the app already computes an estimated date for the halving, so the countdown shows it
    expect(text).toContain('Estimated')
    expect(text).toContain('2028')
  })

  it('keeps both progress bars and their accessible names', async () => {
    const section = await networkPanel(network())
    const bars = section.findAll('[role="progressbar"]')
    const named = Object.fromEntries(bars.map((b): [string, string] => [b.attributes('aria-label') ?? '', b.attributes('aria-valuenow') ?? '']))
    expect(named).toEqual({ 'Progress to the next halving': '41', 'Progress to the next adjustment': '61' })
  })

  it('says Unavailable, not zero, when the halving and difficulty-change data are missing', async () => {
    const section = await networkPanel(network({ halving: null, epoch: null }))
    const text = section.text()
    expect(text).toContain('Next halving')
    expect(text).toContain('Next difficulty change')
    expect(unavailableCount(text)).toBeGreaterThanOrEqual(2)
    expect(text).not.toMatch(/\b0 blocks/)
    // an empty bar would read as 0% progress
    expect(section.findAll('[role="progressbar"]')).toHaveLength(0)
    expect(text).toContain('926,544')
  })

  it('says Unavailable instead of showing out-of-date numbers', async () => {
    const section = await networkPanel(network({ stale: true }))
    const text = section.text()
    expect(text).not.toContain('123,456')
    expect(text).not.toContain('789')
    expect(text).not.toContain('926,544')
    expect(unavailableCount(text)).toBeGreaterThanOrEqual(4)
    expect(section.findAll('[role="progressbar"]')).toHaveLength(0)
  })

  it('says Unavailable for every value while no network data has arrived', async () => {
    const section = await networkPanel(null)
    const text = section.text()
    expect(text).toContain('Next halving')
    expect(unavailableCount(text)).toBeGreaterThanOrEqual(5)
    expect(section.findAll('[role="progressbar"]')).toHaveLength(0)
  })

  it('shows the halving and difficulty-change numbers in orange and the rest in white', async () => {
    const section = await networkPanel(network())
    const halvingValue = section.get('[data-testid="kiosk-halving-value"]')
    const epochValue = section.get('[data-testid="kiosk-epoch-value"]')
    expect(halvingValue.classes()).toContain('text-accent-text')
    expect(epochValue.classes()).toContain('text-accent-text')
    expect(epochValue.classes()).not.toContain('text-fg')
    // height, difficulty and price stay white (foreground), not orange
    for (const id of ['kiosk-height-value', 'kiosk-difficulty-value', 'kiosk-price-value']) {
      const value = section.get(`[data-testid="${id}"]`)
      expect(value.classes(), id).toContain('text-fg')
      expect(value.classes(), id).not.toContain('text-accent-text')
    }
  })

  it('keeps Unavailable muted for height, difficulty and price', async () => {
    const section = await networkPanel(null)
    for (const id of ['kiosk-height-value', 'kiosk-difficulty-value', 'kiosk-price-value']) {
      const value = section.get(`[data-testid="${id}"]`)
      expect(value.text(), id).toBe('Unavailable')
      expect(value.classes(), id).toContain('text-muted')
      expect(value.classes(), id).not.toContain('text-accent-text')
    }
  })

  it('draws the two bars in the accent companion tones, not the status blue and violet', async () => {
    const section = await networkPanel(network())
    const tones = Object.fromEntries(section.findAllComponents(ProgressBar).map((bar: VueWrapper): [string, string] => {
      const { label, tone } = bar.props() as { label: string; tone: string }
      return [label, tone]
    }))
    expect(tones).toEqual({ 'Progress to the next halving': 'accent-violet', 'Progress to the next adjustment': 'accent-blue' })
  })

  it('keeps Unavailable muted, not orange, for the difficulty change', async () => {
    const section = await networkPanel(network({ epoch: null }))
    const epochValue = section.get('[data-testid="kiosk-epoch-value"]')
    expect(epochValue.text()).toBe('Unavailable')
    expect(epochValue.classes()).toContain('text-muted')
    expect(epochValue.classes()).not.toContain('text-accent-text')
  })
})
