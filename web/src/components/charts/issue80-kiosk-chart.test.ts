import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { api } from '@/lib/api'
import HistoryChart from './HistoryChart.vue'
import TimeSeriesChart, { type ChartSeries } from './TimeSeriesChart.vue'

// Issue #80 (and #81 for the chart panel): the wall display chart must be readable from across a room.
// The canvas is replaced by a stub that keeps the exact option the real chart would be drawn with.
vi.mock('vue-echarts', async () => {
  const { defineComponent, h } = await import('vue')
  return { default: defineComponent({ name: 'VChartStub', props: { option: { type: Object, default: null } }, setup: () => () => h('canvas') }) }
})

interface AxisOption {
  axisLabel: { show: boolean; fontSize: number }
}
interface ChartOption {
  legend: { show?: boolean }
  xAxis: AxisOption
  yAxis: AxisOption[]
  series: { lineStyle: { width: number; type?: string; color: string } }[]
}

const START = 1_700_000_000
const STEP = 60
const MIN_KIOSK_AXIS_FONT = 16
const DEFAULT_AXIS_FONT = 11
const DEFAULT_LINE_WIDTH = 2
const MIN_KIOSK_LINE_WIDTH = 4
const KIOSK_PROPS = { kiosk: true }

const t = [START, START + STEP, START + 2 * STEP]
const hashrate: ChartSeries = { key: 'hashrate_hs', name: 'Hashrate', data: [11e12, 12e12, 12.84e12], color: '#f7931a', kind: 'hashrate', axis: 0, area: true }
const power: ChartSeries = { key: 'power_w', name: 'Power', data: [210, 212, 215.4], color: '#38bdf8', kind: 'power', axis: 1 }

const wrappers: { unmount: () => void }[] = []
const originalSize = { width: window.innerWidth, height: window.innerHeight }

function mountChart(kiosk: boolean) {
  const wrapper = mount(TimeSeriesChart, { props: { t, series: [hashrate, power], legend: true, ariaLabel: 'Hashrate and power over 24h', ...(kiosk ? KIOSK_PROPS : {}) } })
  wrappers.push(wrapper)
  return wrapper
}

function optionOf(wrapper: ReturnType<typeof mountChart>): ChartOption {
  return wrapper.findComponent({ name: 'VChartStub' }).props('option') as unknown as ChartOption
}

async function setViewport(width: number, height: number): Promise<void> {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
  Object.defineProperty(window, 'innerHeight', { configurable: true, value: height })
  window.dispatchEvent(new Event('resize'))
  await nextTick()
}

beforeEach(() => {
  setActivePinia(createPinia())
})
afterEach(async () => {
  wrappers.splice(0).forEach((w) => w.unmount())
  await setViewport(originalSize.width, originalSize.height)
  vi.restoreAllMocks()
})

describe('issue 80: wall display chart variant', () => {
  it('draws axis numbers larger than a normal chart', () => {
    const option = optionOf(mountChart(true))
    expect(option.xAxis.axisLabel.show).toBe(true)
    expect(option.xAxis.axisLabel.fontSize).toBeGreaterThanOrEqual(MIN_KIOSK_AXIS_FONT)
    expect(option.yAxis).toHaveLength(2)
    for (const axis of option.yAxis) {
      expect(axis.axisLabel.show).toBe(true)
      expect(axis.axisLabel.fontSize).toBeGreaterThanOrEqual(MIN_KIOSK_AXIS_FONT)
    }
  })

  it('grows the axis numbers with the screen: small, 1080p, 4K and portrait', async () => {
    const wrapper = mountChart(true)
    const sizes: Record<string, number> = {}
    for (const [name, w, h] of [['hd', 1280, 720], ['fullhd', 1920, 1080], ['4k', 3840, 2160], ['portrait', 1080, 1920]] as const) {
      await setViewport(w, h)
      sizes[name] = optionOf(wrapper).yAxis[0]!.axisLabel.fontSize
    }
    expect(sizes.hd).toBeGreaterThanOrEqual(MIN_KIOSK_AXIS_FONT)
    expect(sizes.fullhd).toBeGreaterThan(sizes.hd!)
    expect(sizes['4k']).toBeGreaterThan(sizes.fullhd!)
    // a portrait screen is as tall as a landscape one is wide: it must not shrink the numbers
    expect(sizes.portrait).toBeGreaterThanOrEqual(sizes.fullhd!)
  })

  it('tells the lines apart by style, not only colour', () => {
    const lines = optionOf(mountChart(true)).series.map((s) => s.lineStyle)
    expect(lines).toHaveLength(2)
    expect(new Set(lines.map((l) => l.type)).size).toBe(2)
    expect(new Set(lines.map((l) => l.color)).size).toBe(2)
    for (const line of lines) expect(line.width).toBeGreaterThanOrEqual(MIN_KIOSK_LINE_WIDTH)
  })

  it('names each series with its unit and shows its current value beside it', () => {
    const legend = mountChart(true).find('[data-testid="kiosk-chart-legend"]')
    expect(legend.exists()).toBe(true)
    const labels = legend.findAll('[data-testid="kiosk-series-label"]').map((n) => n.text())
    expect(labels).toEqual(['Hashrate (TH/s)', 'Power (W)'])
    const values = legend.findAll('[data-testid="kiosk-series-value"]').map((n) => n.text())
    expect(values).toEqual(['12.8', '215'])
    const swatches = legend.findAll('svg line').map((n) => n.attributes('stroke-dasharray') ?? 'solid')
    expect(new Set(swatches).size).toBe(2)
  })

  it('uses one legend, not the canvas legend as well', () => {
    expect(optionOf(mountChart(true)).legend.show).toBe(false)
  })

  it('keeps the text summary and the data table for screen readers', () => {
    const wrapper = mountChart(true)
    const describedBy = wrapper.find('[role="img"]').attributes('aria-describedby')
    expect(describedBy).toBeTruthy()
    expect(wrapper.find(`[id="${describedBy}"]`).text()).toContain('Hashrate: latest 12.8 TH/s')
    expect(wrapper.find('details table').exists()).toBe(true)
  })

  it('leaves a normal chart exactly as it was', () => {
    const wrapper = mountChart(false)
    const option = optionOf(wrapper)
    expect(wrapper.find('[data-testid="kiosk-chart-legend"]').exists()).toBe(false)
    expect(option.legend.show).not.toBe(false)
    expect(option.xAxis.axisLabel.fontSize).toBe(DEFAULT_AXIS_FONT)
    for (const axis of option.yAxis) expect(axis.axisLabel.fontSize).toBe(DEFAULT_AXIS_FONT)
    for (const s of option.series) {
      expect(s.lineStyle.width).toBe(DEFAULT_LINE_WIDTH)
      expect(s.lineStyle.type).toBeUndefined()
    }
  })

  it('does not change a normal chart when the screen gets bigger', async () => {
    const wrapper = mountChart(false)
    await setViewport(3840, 2160)
    expect(optionOf(wrapper).yAxis[0]!.axisLabel.fontSize).toBe(DEFAULT_AXIS_FONT)
  })
})

describe('issue 80: the history chart passes the wall display variant through', () => {
  function history() {
    return vi.spyOn(api, 'fleetHistory').mockResolvedValue({ step: STEP, source: 'raw', t, series: { hashrate_hs: hashrate.data, power_w: power.data } })
  }
  async function mountHistory(extra: { kiosk?: boolean }) {
    const wrapper = mount(HistoryChart, { props: { metrics: ['hashrate_hs', 'power_w'], range: '24h', ...extra } })
    wrappers.push(wrapper)
    await flushPromises()
    return wrapper
  }

  it('labels both lines with their units and current values when asked for the wall display', async () => {
    history()
    const wrapper = await mountHistory(KIOSK_PROPS)
    const legend = wrapper.find('[data-testid="kiosk-chart-legend"]')
    expect(legend.exists()).toBe(true)
    expect(legend.text()).toContain('Hashrate (TH/s)')
    expect(legend.text()).toContain('Power (W)')
    expect(legend.text()).toContain('12.8')
    expect(legend.text()).toContain('215')
  })

  it('is unchanged without the wall display flag', async () => {
    history()
    const wrapper = await mountHistory({})
    expect(wrapper.find('[data-testid="kiosk-chart-legend"]').exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'VChartStub' }).props('option')).toBeTruthy()
  })

  it('draws the power line in the accent blue on the wall display, and keeps the status blue everywhere else', async () => {
    history()
    const colours = async (extra: { kiosk?: boolean }) => ((await mountHistory(extra)).findComponent(TimeSeriesChart).props('series') as ChartSeries[]).map((s) => s.color)
    expect(await colours(KIOSK_PROPS)).toEqual(['var(--accent)', 'var(--accent-blue)'])
    expect(await colours({})).toEqual(['var(--accent)', 'var(--info)']) // the normal chart is untouched
  })

  it('hands the canvas the accent blue value, not the status blue', async () => {
    history()
    document.documentElement.style.setProperty('--accent-blue', '#2dbcff')
    document.documentElement.style.setProperty('--info', '#60a5fa')
    try {
      const wrapper = await mountHistory(KIOSK_PROPS)
      const option = wrapper.findComponent({ name: 'VChartStub' }).props('option') as unknown as ChartOption
      expect(option.series.map((s) => s.lineStyle.color)).toEqual(['#f7931a', '#2dbcff'])
    } finally {
      document.documentElement.style.removeProperty('--accent-blue')
      document.documentElement.style.removeProperty('--info')
    }
  })
})
