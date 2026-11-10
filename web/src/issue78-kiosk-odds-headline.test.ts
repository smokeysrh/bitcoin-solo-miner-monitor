import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api } from '@/lib/api'
import type { Odds, Settings } from '@/lib/types'
import { mergeSettings, useSettings } from '@/stores/settings'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import AppearanceSettings from '@/pages/settings/AppearanceSettings.vue'
import KioskPage from '@/pages/KioskPage.vue'

// The charts, miner tiles and live badge need canvas, a data stream or a tooltip provider. The odds panel does not use
// them, so each becomes an empty stand-in and the real KioskPage / AppearanceSettings code is what runs.
vi.mock('@/components/charts/HistoryChart.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return { default: defineComponent({ name: 'HistoryChartStub', render: () => h('div') }) }
})
vi.mock('@/components/miners/MinerTile.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return { default: defineComponent({ name: 'MinerTileStub', render: () => h('div') }) }
})
vi.mock('@/components/layout/LiveBadge.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return { default: defineComponent({ name: 'LiveBadgeStub', render: () => h('div') }) }
})

type Choice = 'ten_minutes' | 'day' | 'month' | 'year' | 'five_years' | 'ten_years'
const ORDER: Choice[] = ['ten_minutes', 'day', 'month', 'year', 'five_years', 'ten_years']
const SHORT: Record<Choice, string> = {
  ten_minutes: 'Next 10 minutes',
  day: 'Today',
  month: 'This month',
  year: 'This year',
  five_years: '5 years',
  ten_years: '10 years',
}
const SENTENCE: Record<Choice, string> = {
  ten_minutes: 'Chance of a block in the next 10 minutes',
  day: 'Chance of a block today',
  month: 'Chance of a block this month',
  year: 'Chance of a block this year',
  five_years: 'Chance of a block in the next 5 years',
  ten_years: 'Chance of a block in the next 10 years',
}
// Probabilities picked so every horizon formats differently ("1 in N", see lib/format.ts).
const PROBABILITY: Record<Choice, number> = { ten_minutes: 0.0005, day: 0.0025, month: 0.0125, year: 0.025, five_years: 0.125, ten_years: 0.25 }
const TEXT: Record<Choice, string> = {
  ten_minutes: '1 in 2,000',
  day: '1 in 400',
  month: '1 in 80.0',
  year: '1 in 40.0',
  five_years: '1 in 8.0',
  ten_years: '1 in 4.0',
}

function oddsFixture(overrides: Partial<Record<Choice, number | null>> = {}): Odds {
  const horizons: Record<string, { seconds: number; probability: number | null; one_in: number | null }> = {}
  for (const key of ORDER) {
    const probability = key in overrides ? overrides[key]! : PROBABILITY[key]
    horizons[key] = { seconds: key === 'ten_minutes' ? 600 : 3600, probability, one_in: null }
  }
  return { available: true, horizons } as unknown as Odds
}

function config(kiosk: Record<string, unknown> | null): Settings {
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null, kiosk },
  } as unknown as Settings
}

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

async function router() {
  const r = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await r.push('/')
  await r.isReady()
  return r
}

async function openKiosk(kiosk: Record<string, unknown> | null, odds: Odds): Promise<Wrapper> {
  useSettings().data = config(kiosk)
  useLive().odds = odds
  const wrapper = mount(KioskPage, { attachTo: document.body, global: { plugins: [await router()] } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

const ONLY_ODDS = { rotate_s: 15, panels: ['odds'], show_clock: false }
const text = (wrapper: Wrapper, id: string): string => wrapper.get(`[data-testid="${id}"]`).text()
const smallLabels = (wrapper: Wrapper): string[] => wrapper.get('[data-testid="kiosk-odds-others"]').findAll('dt').map((n) => n.text())
const smallValues = (wrapper: Wrapper): string[] => wrapper.get('[data-testid="kiosk-odds-others"]').findAll('dd').map((n) => n.text())

beforeEach(() => {
  setActivePinia(createPinia())
  const session = useSession()
  session.state = 'ready'
  session.me = { name: 'tester', scope: 'admin', via: 'token' }
  useLive().loaded = true
  vi.spyOn(api, 'updateSettings').mockImplementation(async (body) => mergeSettings(config(null), body))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks()
})

describe('issue 78: wall display odds headline', () => {
  it.each(ORDER)('headline %s shows its own value and a plain-words label', async (choice) => {
    const wrapper = await openKiosk({ ...ONLY_ODDS, odds_headline: choice }, oddsFixture())
    expect(text(wrapper, 'kiosk-odds-headline')).toBe(TEXT[choice])
    expect(text(wrapper, 'kiosk-odds-headline-label')).toBe(SENTENCE[choice])

    // The other five horizons stay below, in the usual order, and the chosen one is not repeated.
    const others = ORDER.filter((k) => k !== choice)
    expect(smallLabels(wrapper)).toEqual(others.map((k) => SHORT[k]))
    expect(smallValues(wrapper)).toEqual(others.map((k) => TEXT[k]))
  })

  it('keeps the yearly headline for an old record without the field', async () => {
    const wrapper = await openKiosk(ONLY_ODDS, oddsFixture())
    expect(text(wrapper, 'kiosk-odds-headline')).toBe(TEXT.year)
    expect(text(wrapper, 'kiosk-odds-headline-label')).toBe(SENTENCE.year)
    expect(smallLabels(wrapper)).toEqual(['Next 10 minutes', 'Today', 'This month', '5 years', '10 years'])
  })

  it('falls back to the yearly headline for an unknown saved value', async () => {
    const wrapper = await openKiosk({ ...ONLY_ODDS, odds_headline: 'fortnight' }, oddsFixture())
    expect(text(wrapper, 'kiosk-odds-headline')).toBe(TEXT.year)
    expect(text(wrapper, 'kiosk-odds-headline-label')).toBe(SENTENCE.year)
  })

  it('keeps zero as zero, in the headline and in the small list', async () => {
    const wrapper = await openKiosk({ ...ONLY_ODDS, odds_headline: 'ten_minutes' }, oddsFixture({ ten_minutes: 0, day: 0 }))
    expect(text(wrapper, 'kiosk-odds-headline')).toBe('0%')
    expect(smallValues(wrapper)[0]).toBe('0%')
  })

  it('says unavailable, not zero, when the chosen horizon has no value', async () => {
    const wrapper = await openKiosk({ ...ONLY_ODDS, odds_headline: 'day' }, oddsFixture({ day: null, month: null }))
    expect(text(wrapper, 'kiosk-odds-headline')).toBe('Unavailable')
    expect(text(wrapper, 'kiosk-odds-headline-label')).toBe(SENTENCE.day)
    // a missing small value reads the same way and is never shown as 0%
    expect(smallValues(wrapper)[1]).toBe('Unavailable')
  })

  it('does not invent odds while the network data is missing', async () => {
    const wrapper = await openKiosk({ ...ONLY_ODDS, odds_headline: 'ten_minutes' }, { available: false, reason: 'Connect a node' })
    expect(wrapper.find('[data-testid="kiosk-odds-headline"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Waiting for network data')
  })
})

describe('issue 78: Settings -> Appearance control', () => {
  async function openSettings(kiosk: Record<string, unknown> | null): Promise<Wrapper> {
    useSettings().data = config(kiosk)
    const wrapper = mount(AppearanceSettings, { attachTo: document.body, global: { plugins: [await router()] } })
    wrappers.push(wrapper)
    await flushPromises()
    return wrapper
  }
  const select = (wrapper: Wrapper): HTMLSelectElement => wrapper.get('[data-testid="kiosk-odds-headline-setting"]').element as HTMLSelectElement

  it('offers the six time frames, defaults to this year and has a label', async () => {
    const wrapper = await openSettings(ONLY_ODDS)
    expect(Array.from(select(wrapper).options).map((o) => o.text)).toEqual(ORDER.map((k) => SHORT[k]))
    expect(select(wrapper).value).toBe('year')
    const label = wrapper.find(`label[for="${select(wrapper).id}"]`)
    expect(select(wrapper).id).not.toBe('')
    expect(label.exists()).toBe(true)
  })

  it('saves the choice inside the existing ui.kiosk object and keeps its other fields', async () => {
    const wrapper = await openSettings({ rotate_s: 20, panels: ['odds', 'network'], show_clock: false })
    await wrapper.get('[data-testid="kiosk-odds-headline-setting"]').setValue('ten_minutes')
    await flushPromises()
    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.updateSettings).mock.calls[0]![0]).toEqual({
      ui: { kiosk: { rotate_s: 20, panels: ['odds', 'network'], show_clock: false, odds_headline: 'ten_minutes' } },
    })
    expect(select(wrapper).value).toBe('ten_minutes')
  })

  it('starts from the wall display defaults when nothing was saved yet', async () => {
    const wrapper = await openSettings(null)
    await wrapper.get('[data-testid="kiosk-odds-headline-setting"]').setValue('day')
    await flushPromises()
    expect(vi.mocked(api.updateSettings).mock.calls[0]![0]).toEqual({
      ui: { kiosk: { rotate_s: 15, panels: ['overview', 'miners', 'odds', 'network', 'chart'], show_clock: true, odds_headline: 'day' } },
    })
  })
})
