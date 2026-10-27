<script setup lang="ts">
import { LineChart as ChartIcon } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { api, ApiError } from '@/lib/api'
import { DEVICE_COLORS, metricMeta, type MetricKind } from '@/lib/metrics'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import TimeSeriesChart, { type ChartSeries } from './TimeSeriesChart.vue'

const props = withDefaults(
  defineProps<{
    /** omit for fleet-wide totals */
    deviceId?: string
    metrics: string[]
    range: string
    height?: number
    legend?: boolean
    /** fleet only: draw one line per miner for the first metric */
    perDevice?: boolean
    refreshMs?: number
    zeroBased?: boolean
    minimal?: boolean
    ariaLabel?: string
  }>(),
  { height: 260, refreshMs: 30_000 },
)

const live = useLive()
const t = ref<number[]>([])
const raw = ref<Record<string, (number | null)[]>>({})
const perDev = ref<Record<string, Record<string, (number | null)[]>>>({})
const loading = ref(true)
const error = ref<unknown>(null)
let ctrl: AbortController | null = null
let timer: ReturnType<typeof setInterval> | null = null

async function load(initial = false): Promise<void> {
  ctrl?.abort()
  ctrl = new AbortController()
  if (initial) loading.value = true
  try {
    if (props.deviceId) {
      const r = await api.deviceHistory(props.deviceId, { range: props.range, metrics: props.metrics }, ctrl.signal)
      t.value = r.t
      raw.value = r.series
      perDev.value = {}
    } else {
      const r = await api.fleetHistory({ range: props.range, metrics: props.metrics, per_device: props.perDevice }, ctrl.signal)
      t.value = r.t
      raw.value = r.series
      perDev.value = r.devices ?? {}
    }
    error.value = null
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    if (ctrl?.signal.aborted) return
    error.value = e
    if (e instanceof ApiError && e.isAuth) return
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.deviceId, props.metrics.join(','), props.range, props.perDevice] as const,
  () => void load(true),
  { immediate: true },
)
timer = setInterval(() => {
  if (document.visibilityState === 'visible') void load()
}, props.refreshMs)
onBeforeUnmount(() => {
  ctrl?.abort()
  if (timer) clearInterval(timer)
})

const FLEET_LABELS: Record<string, string> = {
  temp_asic_c: 'Hottest ASIC',
  temp_vr_c: 'Hottest regulator',
  online: 'Miners online',
}

const series = computed<ChartSeries[]>(() => {
  const out: ChartSeries[] = []
  const kinds: MetricKind[] = []
  const axisFor = (k: MetricKind): 0 | 1 => {
    let i = kinds.indexOf(k)
    if (i === -1) {
      kinds.push(k)
      i = kinds.length - 1
    }
    return i === 0 ? 0 : 1
  }
  if (props.perDevice && !props.deviceId) {
    const spec = props.metrics[0]!
    const meta = metricMeta(spec)
    if (!meta) return []
    Object.entries(perDev.value).forEach(([id, byMetric], i) => {
      const data = byMetric[spec] ?? byMetric[spec.split(':')[0]!] ?? []
      out.push({ key: id, name: live.deviceName(id), data, color: DEVICE_COLORS[i % DEVICE_COLORS.length]!, kind: meta.kind, axis: 0, area: false, width: 1.8 })
    })
    return out
  }
  props.metrics.forEach((spec, i) => {
    const meta = metricMeta(spec)
    if (!meta) return
    const base = spec.split(':')[0]!
    out.push({
      key: spec,
      name: !props.deviceId && FLEET_LABELS[base] ? FLEET_LABELS[base]! : meta.label,
      data: raw.value[spec] ?? raw.value[base] ?? [],
      color: meta.color,
      kind: meta.kind,
      axis: axisFor(meta.kind),
      area: i === 0,
      step: meta.kind === 'flag',
    })
  })
  return out
})

const hasData = computed(() => series.value.some((s) => s.data.some((v) => typeof v === 'number')))
</script>

<template>
  <div :style="{ minHeight: `${height}px` }">
    <Skeleton v-if="loading" class="w-full" :style="{ height: `${height}px` }" />
    <ErrorState v-else-if="error && !t.length" compact :error="error" title="Could not load the chart" @retry="load(true)" />
    <EmptyState
      v-else-if="!hasData"
      compact
      :icon="ChartIcon"
      title="Charts fill in as your miners report"
      description="Leave the app running for a few minutes and a line will appear here."
    />
    <TimeSeriesChart
      v-else
      :t="t"
      :series="series"
      :height="height"
      :legend="legend ?? (series.length > 1 && !minimal)"
      :zero-based="zeroBased"
      :minimal="minimal"
      :zoom="!minimal"
      :aria-label="ariaLabel"
    />
  </div>
</template>
