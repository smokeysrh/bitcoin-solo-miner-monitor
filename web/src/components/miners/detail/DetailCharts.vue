<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { computed } from 'vue'
import { METRICS, METRIC_LIST } from '@/lib/metrics'
import type { DeviceView } from '@/lib/types'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import RangePicker from '@/components/ui/RangePicker.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

defineProps<{ device: DeviceView }>()

const range = useStorage('bsmm.detail.range', '24h')
const selected = useStorage<string[]>('bsmm.detail.metrics', ['hashrate_hs', 'temp_asic_c'])
const choices = METRIC_LIST.filter((m) => m.key !== 'online')

// a chart reads cleanly with at most two different units (left and right axis), so a third unit replaces the oldest
function toggle(key: string): void {
  if (selected.value.includes(key)) {
    if (selected.value.length > 1) selected.value = selected.value.filter((k) => k !== key)
    return
  }
  const next = [...selected.value, key]
  const kinds = [...new Set(next.map((k) => METRICS[k]?.kind))]
  if (kinds.length > 2) {
    const dropKind = kinds[0]
    selected.value = next.filter((k) => METRICS[k]?.kind !== dropKind)
  } else {
    selected.value = next.slice(-4)
  }
}

const metrics = computed(() => [...selected.value])
</script>

<template>
  <MetricCard title="Charts">
    <template #actions><RangePicker v-model="range" :ranges="['1h', '6h', '24h', '7d', '30d', '90d', '1y']" /></template>
    <div class="mb-4 flex flex-wrap gap-1.5" role="group" aria-label="Choose what to chart">
      <button
        v-for="m in choices"
        :key="m.key"
        :class="['rounded-full border px-3 py-1 text-xs font-medium transition-colors', selected.includes(m.key) ? 'border-accent-line bg-accent-soft text-accent-text' : 'border-line text-muted hover:border-line-strong hover:text-fg']"
        :aria-pressed="selected.includes(m.key)"
        :title="m.help"
        @click="toggle(m.key)"
      >
        {{ m.label }}
      </button>
    </div>
    <p class="mb-3 text-xs text-subtle">Pick up to two kinds of measurement to compare on one chart. Drag to pan, hold Shift and scroll to zoom.</p>
    <HistoryChart :device-id="device.id" :metrics="metrics" :range="range" :height="380" legend :aria-label="`History for ${device.name}`" />
  </MetricCard>
</template>
