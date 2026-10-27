<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { ChartLine, Download } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import TimeSeriesChart, { type ChartSeries } from '@/components/charts/TimeSeriesChart.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import RangePicker from '@/components/ui/RangePicker.vue'
import Segmented from '@/components/ui/Segmented.vue'
import Select from '@/components/ui/Select.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useFmt } from '@/composables/useFmt'
import { api } from '@/lib/api'
import { downloadText, toCsv } from '@/lib/csv'
import { DEVICE_COLORS, METRIC_LIST, METRICS, formatMetric } from '@/lib/metrics'
import type { HistoryResult } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'

const live = useLive()
const fmt = useFmt()
const toasts = useToasts()

const range = useStorage('bsmm.analytics.range', '24h')
const metric = useStorage('bsmm.analytics.metric', 'hashrate_hs')
const second = useStorage('bsmm.analytics.second', '')
const mode = useStorage<'fleet' | 'miners'>('bsmm.analytics.mode', 'fleet')
const picked = ref<Set<string>>(new Set())

const data = ref<HistoryResult | null>(null)
const loading = ref(true)
const error = ref<unknown>(null)
let ctrl: AbortController | null = null

const choices = METRIC_LIST.filter((m) => m.key !== 'online').map((m) => ({ value: m.key, label: m.label }))
const secondChoices = computed(() => [{ value: '', label: 'None' }, ...choices.filter((c) => METRICS[c.value]?.kind !== METRICS[metric.value]?.kind)])
watch(metric, () => {
  if (second.value && METRICS[second.value]?.kind === METRICS[metric.value]?.kind) second.value = ''
})

async function load(): Promise<void> {
  ctrl?.abort()
  ctrl = new AbortController()
  loading.value = !data.value
  try {
    const metrics = mode.value === 'fleet' && second.value ? [metric.value, second.value] : [metric.value]
    data.value = await api.fleetHistory({ range: range.value, metrics, per_device: mode.value === 'miners' }, ctrl.signal)
    error.value = null
  } catch (e) {
    if (!ctrl?.signal.aborted) error.value = e
  } finally {
    loading.value = false
  }
}
watch([range, metric, second, mode], () => void load(), { immediate: true })
const timer = setInterval(() => document.visibilityState === 'visible' && void load(), 30_000)
onBeforeUnmount(() => {
  clearInterval(timer)
  ctrl?.abort()
})

const series = computed<ChartSeries[]>(() => {
  const d = data.value
  const meta = METRICS[metric.value]
  if (!d || !meta) return []
  if (mode.value === 'miners') {
    return Object.entries(d.devices ?? {})
      .filter(([id]) => !picked.value.size || picked.value.has(id))
      .map(([id, by], i) => ({ key: id, name: live.deviceName(id), data: by[metric.value] ?? [], color: DEVICE_COLORS[i % DEVICE_COLORS.length]!, kind: meta.kind, width: 1.8 }))
  }
  const out: ChartSeries[] = [{ key: metric.value, name: meta.label, data: d.series[metric.value] ?? [], color: meta.color, kind: meta.kind, area: true, axis: 0 }]
  const m2 = METRICS[second.value]
  if (m2) out.push({ key: second.value, name: m2.label, data: d.series[second.value] ?? [], color: m2.color, kind: m2.kind, axis: 1 })
  return out
})

const hasData = computed(() => series.value.some((s) => s.data.some((v) => typeof v === 'number')))

const stats = computed(() => {
  const s = series.value[0]
  const kind = METRICS[metric.value]?.kind
  if (!s || !kind || mode.value !== 'fleet') return null
  const nums = s.data.filter((v): v is number => typeof v === 'number')
  if (!nums.length) return null
  const f = (v: number) => formatMetric(kind, v, fmt)
  return [
    ['Latest', f(nums[nums.length - 1]!)],
    ['Average', f(nums.reduce((a, b) => a + b, 0) / nums.length)],
    ['Lowest', f(Math.min(...nums))],
    ['Highest', f(Math.max(...nums))],
  ] as const
})

function exportCsv(): void {
  if (!data.value || !hasData.value) return
  const cols = series.value.map((s) => ({ name: s.name, data: s.data }))
  downloadText(`bsmm-${metric.value}-${range.value}.csv`, toCsv(data.value.t, cols))
  toasts.success('Exported', `${data.value.t.length} rows`)
}

function togglePick(id: string): void {
  const next = new Set(picked.value)
  if (!next.delete(id)) next.add(id)
  picked.value = next
}
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 class="text-2xl font-semibold tracking-tight text-fg">Analytics</h2>
        <p class="mt-1 text-sm text-muted">Explore how your fleet has behaved. Everything is kept on this computer.</p>
      </div>
      <Button variant="secondary" size="sm" :disabled="!hasData" @click="exportCsv"><template #icon><Download class="size-4" /></template>Export CSV</Button>
    </header>

    <MetricCard title="History" :icon="ChartLine">
      <template #actions><RangePicker v-model="range" :ranges="['1h', '6h', '24h', '7d', '30d', '90d', '1y']" /></template>
      <div class="mb-4 flex flex-wrap items-end gap-3">
        <label class="block text-xs font-medium text-subtle">Show
          <Select v-model="metric" :options="choices" size="sm" class="mt-1 w-52" aria-label="Metric" data-testid="metric" />
        </label>
        <label v-if="mode === 'fleet'" class="block text-xs font-medium text-subtle">Compare with
          <Select v-model="second" :options="secondChoices" size="sm" class="mt-1 w-52" aria-label="Second metric" />
        </label>
        <Segmented v-model="mode" label="Scope" size="sm" :options="[{ value: 'fleet', label: 'Whole fleet' }, { value: 'miners', label: 'Each miner' }]" />
      </div>
      <div v-if="mode === 'miners' && live.devices.length > 1" class="mb-4 flex flex-wrap gap-1.5" role="group" aria-label="Choose miners">
        <button
          v-for="d in live.devices"
          :key="d.id"
          :class="['rounded-full border px-3 py-1 text-xs font-medium transition-colors', picked.has(d.id) ? 'border-accent-line bg-accent-soft text-accent-text' : 'border-line text-muted hover:border-line-strong hover:text-fg']"
          :aria-pressed="picked.has(d.id)"
          @click="togglePick(d.id)"
        >{{ d.name }}</button>
        <span v-if="!picked.size" class="self-center text-xs text-subtle">Showing all. Pick some to narrow it down.</span>
      </div>

      <Skeleton v-if="loading" class="h-[420px] w-full rounded-xl" />
      <ErrorState v-else-if="error && !data" compact :error="error" title="Could not load history" @retry="load" />
      <EmptyState v-else-if="!hasData" compact :icon="ChartLine" title="No data for this range yet" description="History builds up while the app runs. Try a shorter range." />
      <TimeSeriesChart v-else-if="data" :t="data.t" :series="series" :height="420" :legend="series.length > 1" :aria-label="`${METRICS[metric]?.label} over ${range}`" />

      <dl v-if="stats" class="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 sm:grid-cols-4">
        <div v-for="[k, v] in stats" :key="k"><dt class="text-xs text-subtle">{{ k }}</dt><dd class="tnum mt-1 text-lg font-semibold text-fg">{{ v }}</dd></div>
      </dl>
      <p v-if="data" class="mt-3 text-xs text-subtle">Each point is the average over {{ fmt.formatDuration(data.step) }}. Source: {{ data.source }}.</p>
    </MetricCard>
  </div>
</template>
