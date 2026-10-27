<script setup lang="ts">
import { Activity, Gauge, Share2, Thermometer, Zap } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { tempLevel } from '@/lib/format'
import { useLive } from '@/stores/live'
import { useSettings } from '@/stores/settings'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import Badge from '@/components/ui/Badge.vue'
import Stat from '@/components/ui/Stat.vue'
import Term from '@/components/ui/Term.vue'

const live = useLive()
const fmt = useFmt()
const settings = useSettings()

const s = computed(() => live.summary)
const hash = computed(() => fmt.splitHash(s.value?.hashrate_hs))
const perf = computed(() => s.value?.performance_pct ?? null)
const perfTone = computed(() => (perf.value === null ? '' : perf.value >= 95 ? 'text-ok' : perf.value >= 80 ? 'text-warn' : 'text-bad'))
const shares = computed(() => (s.value?.shares_accepted ?? 0) + (s.value?.shares_rejected ?? 0))
// a reject rate off a handful of shares is noise, so wait for a meaningful sample
const rejectKnown = computed(() => shares.value >= 100 && s.value?.reject_rate_pct != null)
const health = computed(() => {
  const x = s.value
  if (!x || !x.devices_total) return { tone: 'neutral' as const, text: 'No miners yet' }
  if (x.devices_offline) return { tone: 'bad' as const, text: `${x.devices_offline} offline` }
  if (x.devices_degraded) return { tone: 'warn' as const, text: `${x.devices_degraded} need attention` }
  if (x.devices_paused) return { tone: 'info' as const, text: `${x.devices_paused} paused` }
  return { tone: 'ok' as const, text: x.devices_total === 1 ? 'Online' : `All ${x.devices_total} online` }
})
const tempTone = computed(() => {
  const l = tempLevel(s.value?.temp_max_c, settings.data?.alerts.temp_warn_c ?? 75, settings.data?.alerts.temp_crit_c ?? 85)
  return l === 'crit' ? 'bad' : l === 'warn' ? 'warn' : 'default'
})
</script>

<template>
  <section class="card relative h-full overflow-hidden" aria-label="Fleet hashrate" data-testid="widget-hero">
    <div class="pointer-events-none absolute -top-24 -left-16 size-72 rounded-full bg-accent/10 blur-3xl" aria-hidden="true" />
    <div class="relative flex h-full flex-col p-[var(--pad-card)]">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <p class="eyebrow"><Term k="hashrate">Fleet hashrate</Term></p>
          <p class="mt-2 flex items-baseline gap-2.5" data-testid="hero-hashrate">
            <span class="text-gradient-accent tnum text-5xl leading-none font-bold tracking-tight sm:text-6xl">{{ hash.value }}</span>
            <span class="text-xl font-medium text-subtle">{{ hash.unit }}</span>
          </p>
          <p v-if="perf !== null && s?.expected_hashrate_hs" class="mt-2.5 text-sm text-muted">
            <span :class="['font-semibold', perfTone]">{{ perf.toFixed(0) }}%</span> of the {{ fmt.hashrate(s.expected_hashrate_hs) }} your settings should deliver
          </p>
        </div>
        <Badge :tone="health.tone" dot data-testid="hero-health">{{ health.text }}</Badge>
      </div>

      <div class="-mx-[var(--pad-card)] mt-4 min-h-[120px] flex-1">
        <HistoryChart :metrics="['hashrate_hs']" range="6h" :height="130" minimal aria-label="Fleet hashrate over the last six hours" />
      </div>

      <div class="mt-3 grid grid-cols-2 gap-x-4 gap-y-4 border-t border-line pt-4 sm:grid-cols-4">
        <Stat label="Power" :icon="Zap" :value="fmt.splitPower(s?.power_wall_w ?? s?.power_w).value" :unit="fmt.splitPower(s?.power_wall_w ?? s?.power_w).unit" size="sm" />
        <Stat :label="'Efficiency'" :icon="Gauge" :value="s?.efficiency_j_th ? s.efficiency_j_th.toFixed(1) : '–'" unit="J/TH" size="sm">
          <template #label><Term k="efficiency">Efficiency</Term></template>
        </Stat>
        <Stat label="Temperature" :icon="Thermometer" :value="fmt.tempValue(s?.temp_avg_c)" :unit="fmt.tempSymbol()" :tone="tempTone" :sub="s?.temp_max_c != null ? `hottest ${fmt.temp(s.temp_max_c)}` : undefined" size="sm" />
        <Stat
          label="Shares"
          :icon="rejectKnown ? Share2 : Activity"
          :value="fmt.formatNumber(s?.shares_accepted ?? 0)"
          :sub="rejectKnown ? `${fmt.formatPercent(s!.reject_rate_pct, 2)} rejected` : 'accepted so far'"
          size="sm"
        />
      </div>
    </div>
  </section>
</template>
