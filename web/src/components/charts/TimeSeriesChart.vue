<script setup lang="ts">
/**
 * One chart component for every time series in the app. Tree-shaken ECharts (canvas) so the whole
 * charting stack costs one lazy-loaded chunk.
 */
import { BarChart, LineChart } from 'echarts/charts'
import { AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, TooltipComponent } from 'echarts/components'
import { color as ecolor, graphic, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'
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
  }>(),
  { height: 260, legend: false, zoom: true },
)

const fmt = useFmt()
const settings = useSettings()
const tick = useThemeTick()

function resolve(c: string): string {
  const m = /^var\((--[\w-]+)\)$/.exec(c.trim())
  return m ? cssVar(m[1]!, '#f7931a') : c
}
const esc = (s: string): string => s.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]!)

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
        color: axis,
        fontSize: 11,
        margin: 8,
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
      : { left: 4, right: dualAxis ? 4 : 10, top: props.legend ? 34 : 12, bottom: props.zoom ? 4 : 2, containLabel: true },
    legend: props.legend
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
      axisLabel: { show: !props.minimal, color: axis, fontSize: 11, hideOverlap: true },
    },
    yAxis: yAxes,
    dataZoom: props.zoom ? [{ type: 'inside', xAxisIndex: 0, filterMode: 'none', zoomOnMouseWheel: 'shift', moveOnMouseMove: true }] : [],
    series: props.series.map((s) => {
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
        lineStyle: { width: s.width ?? 2, color: c },
        areaStyle: s.area
          ? { color: new graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: ecolor.modifyAlpha(c, 0.28) }, { offset: 1, color: ecolor.modifyAlpha(c, 0) }]) }
          : undefined,
      }
    }),
  }
})
</script>

<template>
  <div :style="{ height: `${height}px` }" role="img" :aria-label="ariaLabel ?? 'Chart'">
    <VChart class="chart-host" :option="option" autoresize :init-options="{ renderer: 'canvas' }" />
  </div>
</template>
