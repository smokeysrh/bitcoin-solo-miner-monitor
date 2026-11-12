<script setup lang="ts">
/**
 * One chart component for every time series in the app. Tree-shaken ECharts (canvas) so the whole
 * charting stack costs one lazy-loaded chunk.
 */
import { useWindowSize } from '@vueuse/core'
import { BarChart, LineChart } from 'echarts/charts'
import { AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, TooltipComponent } from 'echarts/components'
import { color as ecolor, graphic, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import { computed, useId } from 'vue'
import VChart from 'vue-echarts'
import { useFmt } from '@/composables/useFmt'
import { useThemeTick } from '@/composables/useThemeTick'
import { cssVar } from '@/lib/theme'
import { formatAxis, formatMetric, type MetricKind } from '@/lib/metrics'
import { useSettings } from '@/stores/settings'

use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, MarkAreaComponent, AxisPointerComponent, CanvasRenderer])

export interface ChartSeries {
  key: string
  name: string
  data: (number | null)[]
  /** CSS colour or var(--token) */
  color: string
  kind: MetricKind
  type?: 'line' | 'bar'
  area?: boolean
  axis?: 0 | 1
  step?: boolean
  width?: number
}

const props = withDefaults(
  defineProps<{
    t: number[]
    series: ChartSeries[]
    height?: number
    legend?: boolean
    zoom?: boolean
    ariaLabel?: string
    /** start the value axis at zero instead of fitting the data (better for counters and flags) */
    zeroBased?: boolean
    /** hero-style: no axes or grid, just the line and a tooltip */
    minimal?: boolean
    /**
     * wall display: fills the height its parent gives it, shows a large HTML legend with each series' current value,
     * and draws big axis numbers and lines that differ by style as well as colour. Fixed for the life of the component.
     */
    kiosk?: boolean
  }>(),
  { height: 260, legend: false, zoom: true },
)

const fmt = useFmt()
const settings = useSettings()
const tick = useThemeTick()

/** Wall display sizing: text follows the shorter screen side, so a portrait screen is as readable as a landscape one. */
const KIOSK_FALLBACK_SIDE = 720
const KIOSK_AXIS_FONT_DIVISOR = 40
const KIOSK_AXIS_FONT_MIN = 16
const KIOSK_AXIS_FONT_MAX = 96
const KIOSK_LINE_WIDTH_DIVISOR = 6
const KIOSK_LINE_WIDTH_MIN = 4
const DEFAULT_LINE_WIDTH = 2
const KIOSK_TOP_ROOM = 0.75 // of a label's height, so the top axis number is not cut off
const KIOSK_SWATCH_DASH = '12 8'
const windowSize = props.kiosk ? useWindowSize({ listenOrientation: false }) : null
const kioskFont = computed(() => {
  const side = Math.min(windowSize?.width.value ?? Infinity, windowSize?.height.value ?? Infinity)
  const base = Number.isFinite(side) ? side : KIOSK_FALLBACK_SIDE
  return Math.min(KIOSK_AXIS_FONT_MAX, Math.max(KIOSK_AXIS_FONT_MIN, Math.round(base / KIOSK_AXIS_FONT_DIVISOR)))
})
/** Lines alternate solid and dashed, so the two are told apart without colour. */
const kioskDashed = (index: number): boolean => index % 2 === 1

function resolve(c: string): string {
  const m = /^var\((--[\w-]+)\)$/.exec(c.trim())
  return m ? cssVar(m[1]!, '#f7931a') : c
}
const esc = (s: string): string => s.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]!)

/** Non-visual equivalent of the canvas: a text summary and a bounded table of the exact rendered data. */
const NO_DATA = 'no data'
const MAX_TABLE_ROWS = 200
const label = computed(() => props.ariaLabel ?? 'Chart')
const descriptionId = useId()
const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone

const description = computed(() => {
  const parts = props.series.map((s) => {
    let latest: number | null = null
    let lowest = Infinity
    let highest = -Infinity
    let missing = 0
    for (let i = 0; i < props.t.length; i++) {
      const v = s.data[i]
      if (typeof v !== 'number') {
        missing++
        continue
      }
      latest = v
      lowest = Math.min(lowest, v)
      highest = Math.max(highest, v)
    }
    if (latest === null) return `${s.name}: ${NO_DATA}.`
    const gaps = missing ? `, ${missing} missing` : ''
    return `${s.name}: latest ${formatMetric(s.kind, latest, fmt)}, lowest ${formatMetric(s.kind, lowest, fmt)}, highest ${formatMetric(s.kind, highest, fmt)}${gaps}.`
  })
  return [`${label.value}.`, ...parts].join(' ')
})

const shownFrom = computed(() => Math.max(0, props.t.length - MAX_TABLE_ROWS))

/** One legend entry per series: its name with the unit, and its newest value on its own. */
const legendItems = computed(() =>
  props.series.map((s, index) => {
    let latest: number | null = null
    for (let i = props.t.length - 1; i >= 0 && latest === null; i--) {
      const v = s.data[i]
      if (typeof v === 'number') latest = v
    }
    const text = latest === null ? null : formatMetric(s.kind, latest, fmt)
    const cut = text === null ? -1 : text.indexOf(' ')
    const value = text === null ? '–' : cut < 0 ? text : text.slice(0, cut)
    const unit = text === null || cut < 0 ? '' : text.slice(cut + 1)
    return { key: s.key, color: s.color, dashed: kioskDashed(index), label: unit ? `${s.name} (${unit})` : s.name, value }
  }),
)
const rows = computed(() =>
  props.t.slice(shownFrom.value).map((ts, j) => {
    const index = shownFrom.value + j
    return {
      index,
      when: new Date(ts * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' }),
      cells: props.series.map((s) => {
        const v = s.data[index]
        return typeof v === 'number' ? formatMetric(s.kind, v, fmt) : null
      }),
    }
  }),
)

const option = computed<EChartsOption>(() => {
  void tick.value // recompute colours when the theme changes
  const text = cssVar('--fg', '#eceef4')
  const axis = cssVar('--chart-axis', '#7b8599')
  const grid = cssVar('--chart-grid', 'rgba(255,255,255,.06)')
  const surface = cssVar('--surface-2', '#151922')
  const line = cssVar('--line-strong', 'rgba(255,255,255,.15)')
  const motion = !settings.data?.ui.reduce_motion

  const axisKinds: [MetricKind | null, MetricKind | null] = [null, null]
  for (const s of props.series) {
    const a = s.axis ?? 0
    axisKinds[a] ??= s.kind
  }
  const dualAxis = axisKinds[1] !== null
  const times = props.t.map((x) => x * 1000)

  const kiosk = props.kiosk === true
  const font = kiosk ? kioskFont.value : 11
  const axisText = kiosk ? text : axis // from across a room the numbers get full-strength text

  const yAxes = ([0, 1] as const)
    .filter((i) => axisKinds[i] !== null)
    .map((i) => ({
      type: 'value' as const,
      position: i === 0 ? ('left' as const) : ('right' as const),
      scale: !props.zeroBased,
      min: props.zeroBased ? 0 : undefined,
      splitNumber: 4,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: i === 0 && !props.minimal, lineStyle: { color: grid } },
      axisLabel: {
        show: !props.minimal,
        color: axisText,
        fontSize: font,
        margin: kiosk ? Math.round(font / 2) : 8,
        formatter: (v: number) => formatAxis(axisKinds[i]!, v, fmt),
      },
    }))

  return {
    animation: motion,
    animationDuration: 350,
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'Inter Variable, system-ui, sans-serif' },
    grid: props.minimal
      ? { left: 0, right: 0, top: 6, bottom: 0, containLabel: false }
      : { left: 4, right: dualAxis ? 4 : 10, top: kiosk ? Math.ceil(font * KIOSK_TOP_ROOM) : props.legend ? 34 : 12, bottom: props.zoom ? 4 : 2, containLabel: true },
    legend: props.legend && !kiosk
      ? { top: 0, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10, itemGap: 16, textStyle: { color: axis, fontSize: 12 }, inactiveColor: line }
      : { show: false },
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: surface,
      borderColor: line,
      borderWidth: 1,
      padding: [8, 10],
      textStyle: { color: text, fontSize: 12 },
      extraCssText: 'border-radius:12px;box-shadow:0 12px 32px -8px rgba(0,0,0,.5);',
      axisPointer: { type: 'line', lineStyle: { color: line, type: 'dashed' } },
      formatter: (raw: unknown) => {
        const params = (Array.isArray(raw) ? raw : [raw]) as { axisValue: number; marker: string; seriesName: string; value: [number, number | null]; seriesIndex: number }[]
        if (!params.length) return ''
        const when = new Date(params[0]!.axisValue).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
        const rows = params
          .map((p) => {
            const s = props.series[p.seriesIndex]
            const v = p.value?.[1]
            const shown = v === null || v === undefined || !s ? '<span style="opacity:.6">no data</span>' : esc(formatMetric(s.kind, v, fmt))
            return `<div style="display:flex;justify-content:space-between;gap:18px;margin-top:3px"><span>${p.marker}${esc(p.seriesName)}</span><b style="font-variant-numeric:tabular-nums">${shown}</b></div>`
          })
          .join('')
        return `<div style="opacity:.7;font-size:11px">${esc(when)}</div>${rows}`
      },
    },
    xAxis: {
      type: 'time',
      min: times[0],
      max: times[times.length - 1],
      axisLine: { show: !props.minimal, lineStyle: { color: grid } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: !props.minimal, color: axisText, fontSize: font, hideOverlap: true },
    },
    yAxis: yAxes,
    dataZoom: props.zoom ? [{ type: 'inside', xAxisIndex: 0, filterMode: 'none', zoomOnMouseWheel: 'shift', moveOnMouseMove: true }] : [],
    series: props.series.map((s, index) => {
      const c = resolve(s.color)
      const base = {
        name: s.name,
        yAxisIndex: s.axis === 1 && dualAxis ? 1 : 0,
        data: times.map((ms, i) => [ms, s.data[i] ?? null]),
        connectNulls: false,
        showSymbol: false,
        emphasis: { focus: 'series' as const },
        itemStyle: { color: c },
      }
      if (s.type === 'bar') {
        return { ...base, type: 'bar' as const, barMaxWidth: 14, itemStyle: { color: c, borderRadius: [3, 3, 0, 0] } }
      }
      return {
        ...base,
        type: 'line' as const,
        step: s.step ? ('end' as const) : false,
        smooth: s.step ? false : 0.25,
        sampling: 'lttb' as const,
        lineStyle: {
          width: s.width ?? (kiosk ? Math.max(KIOSK_LINE_WIDTH_MIN, Math.round(font / KIOSK_LINE_WIDTH_DIVISOR)) : DEFAULT_LINE_WIDTH),
          color: c,
          ...(kiosk ? { type: kioskDashed(index) ? ('dashed' as const) : ('solid' as const) } : {}),
        },
        areaStyle: s.area
          ? { color: new graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: ecolor.modifyAlpha(c, 0.28) }, { offset: 1, color: ecolor.modifyAlpha(c, 0) }]) }
          : undefined,
      }
    }),
  }
})
</script>

<template>
  <div :class="kiosk ? 'flex min-h-0 flex-1 flex-col' : undefined">
    <ul
      v-if="kiosk"
      data-testid="kiosk-chart-legend"
      class="mb-4 flex flex-wrap items-center justify-center gap-x-[2em] gap-y-[0.5em] text-[clamp(1.125rem,2.8vmin,6rem)] text-fg"
    >
      <li v-for="item in legendItems" :key="item.key" data-testid="kiosk-series-item" class="flex items-center gap-[0.5em]">
        <svg class="h-[0.5em] w-[3em] shrink-0" viewBox="0 0 48 8" aria-hidden="true">
          <line x1="0" y1="4" x2="48" y2="4" stroke-width="5" :style="{ stroke: item.color }" :stroke-dasharray="item.dashed ? KIOSK_SWATCH_DASH : undefined" />
        </svg>
        <span data-testid="kiosk-series-label" class="font-medium">{{ item.label }}</span>
        <span data-testid="kiosk-series-value" class="tnum text-[1.8em] leading-none font-bold">{{ item.value }}</span>
      </li>
    </ul>
    <div
      :class="kiosk ? 'relative flex-1' : undefined"
      :style="kiosk ? { minHeight: `${height}px` } : { height: `${height}px` }"
      role="img"
      :aria-label="label"
      :aria-describedby="descriptionId"
    >
      <VChart :class="kiosk ? 'chart-host absolute inset-0' : 'chart-host'" :option="option" autoresize :init-options="{ renderer: 'canvas' }" />
    </div>
    <p :id="descriptionId" class="sr-only">{{ description }}</p>
    <details v-if="!minimal" class="mt-2 text-sm">
      <summary class="w-fit cursor-pointer rounded-sm text-muted outline-none hover:text-fg focus-visible:ring-2 focus-visible:ring-accent">
        View data ({{ fmt.formatNumber(t.length) }} points)
      </summary>
      <p v-if="shownFrom > 0" class="mt-2 text-xs text-subtle">Showing the latest {{ fmt.formatNumber(rows.length) }} of {{ fmt.formatNumber(t.length) }} points.</p>
      <div class="mt-2 max-h-64 overflow-auto rounded-md border border-line outline-none focus-visible:ring-2 focus-visible:ring-accent" role="region" tabindex="0" :aria-label="`${label}: data table`">
        <table class="w-full border-collapse text-left">
          <caption class="px-2 py-1 text-left text-xs text-subtle">{{ label }}. Times are in {{ timeZone }}.</caption>
          <thead class="sticky top-0 bg-surface-2 text-xs text-muted">
            <tr>
              <th scope="col" class="px-2 py-1 font-medium">Time</th>
              <th v-for="s in series" :key="s.key" scope="col" class="px-2 py-1 font-medium">{{ s.name }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.index" class="border-t border-line">
              <th scope="row" class="tnum whitespace-nowrap px-2 py-1 font-normal text-muted">{{ row.when }}</th>
              <td v-for="(cell, i) in row.cells" :key="i" class="tnum px-2 py-1 text-fg">
                <span v-if="cell === null" class="text-subtle">{{ NO_DATA }}</span>
                <template v-else>{{ cell }}</template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </div>
</template>
