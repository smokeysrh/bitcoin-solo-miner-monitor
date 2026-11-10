import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import TimeSeriesChart, { type ChartSeries } from './TimeSeriesChart.vue'

// The canvas renderer is irrelevant here: the issue is what a non-visual user can reach beside it.
vi.mock('vue-echarts', async () => {
  const { defineComponent, h } = await import('vue')
  return { default: defineComponent({ name: 'VChartStub', props: { option: { type: Object, default: null } }, setup: () => () => h('canvas') }) }
})

const MAX_ROWS = 200
const START = 1_700_000_000
const STEP = 60
const wrappers: { unmount: () => void }[] = []

function times(n: number): number[] {
  return Array.from({ length: n }, (_, i) => START + i * STEP)
}

function mountChart(t: number[], series: ChartSeries[], extra: { minimal?: boolean; zoom?: boolean } = {}) {
  const wrapper = mount(TimeSeriesChart, { props: { t, series, ariaLabel: 'Power over 1h', ...extra } })
  wrappers.push(wrapper)
  return wrapper
}

const watts: ChartSeries[] = [
  { key: 'a', name: 'Garage', data: [100, null, 120], color: '#f7931a', kind: 'power' },
  { key: 'b', name: 'Shed', data: [50, 60, 70], color: '#22d3ee', kind: 'power' },
]

beforeEach(() => {
  setActivePinia(createPinia())
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

describe('issue 43: chart data is reachable without the canvas or a pointer', () => {
  it('offers a keyboard-operable data view as a native disclosure', () => {
    const wrapper = mountChart(times(3), watts)
    const details = wrapper.find('details')
    expect(details.exists()).toBe(true)
    const summary = details.find('summary')
    expect(summary.exists()).toBe(true)
    expect(summary.text()).toMatch(/view data/i)
    // The image role hides its children from assistive tech, so the data must live outside it.
    expect(wrapper.find('[role="img"]').find('table').exists()).toBe(false)
    expect(wrapper.find('[role="img"]').attributes('aria-label')).toBe('Power over 1h')
  })

  it('renders every series as a labelled column with formatted values and an explicit gap', () => {
    const wrapper = mountChart(times(3), watts)
    const table = wrapper.find('table')
    expect(table.exists()).toBe(true)
    expect(table.find('caption').text()).toContain('Power over 1h')
    expect(table.findAll('thead th').map((th) => th.text())).toEqual(['Time', 'Garage', 'Shed'])
    const rows = table.findAll('tbody tr')
    expect(rows).toHaveLength(3)
    const cells = rows.map((r) => r.findAll('td, th').map((c) => c.text()))
    expect(cells.map((r) => r.slice(1))).toEqual([
      ['100 W', '50.0 W'],
      ['no data', '60.0 W'],
      ['120 W', '70.0 W'],
    ])
    expect(new Set(cells.map((r) => r[0])).size).toBe(3)
    expect(table.findAll('tbody th[scope="row"]')).toHaveLength(3)
    expect(wrapper.text()).toContain(Intl.DateTimeFormat().resolvedOptions().timeZone)
  })

  it('describes the chart as text: latest, range and missing samples per series', () => {
    const wrapper = mountChart(times(3), watts)
    const describedBy = wrapper.find('[role="img"]').attributes('aria-describedby')
    expect(describedBy).toBeTruthy()
    const description = wrapper.find(`[id="${describedBy}"]`)
    expect(description.exists()).toBe(true)
    const text = description.text()
    expect(text).toContain('Garage')
    expect(text).toContain('latest 120 W')
    expect(text).toContain('lowest 100 W')
    expect(text).toContain('highest 120 W')
    expect(text).toContain('1 missing')
    expect(text).toContain('Shed')
    expect(text).toContain('latest 70.0 W')
  })

  it('says so when a series has no samples at all', () => {
    const wrapper = mountChart(times(2), [{ key: 'a', name: 'Garage', data: [null, null], color: '#f7931a', kind: 'power' }])
    const describedBy = wrapper.find('[role="img"]').attributes('aria-describedby')
    expect(describedBy).toBeTruthy()
    expect(wrapper.find(`[id="${describedBy}"]`).text()).toMatch(/Garage.*no data/)
  })

  it('bounds the table for long histories and keeps the newest points', () => {
    const count = 1000
    const data = Array.from({ length: count }, (_, i) => i)
    const wrapper = mountChart(times(count), [{ key: 'a', name: 'Garage', data, color: '#f7931a', kind: 'count' }])
    const rows = wrapper.findAll('table tbody tr')
    expect(rows.length).toBeGreaterThan(0)
    expect(rows.length).toBeLessThanOrEqual(MAX_ROWS)
    expect(rows[rows.length - 1]!.findAll('td').pop()!.text()).toBe('999')
    expect(wrapper.find('details').text()).toContain('1,000')
  })

  it('renders series names as text, not markup', () => {
    const wrapper = mountChart(times(1), [{ key: 'a', name: '<img src=x onerror=alert(1)>', data: [1], color: '#f7931a', kind: 'count' }])
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('thead').text()).toContain('<img src=x onerror=alert(1)>')
  })

  it('keeps the small minimal graph uncluttered but still described as text', () => {
    const wrapper = mountChart(times(3), watts, { minimal: true, zoom: false })
    expect(wrapper.find('details').exists()).toBe(false)
    const describedBy = wrapper.find('[role="img"]').attributes('aria-describedby')
    expect(describedBy).toBeTruthy()
    expect(wrapper.find(`[id="${describedBy}"]`).text()).toContain('latest 120 W')
  })
})
