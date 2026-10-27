<script setup lang="ts">
import { Activity, Fan, Gauge, Network, Share2, SlidersHorizontal, Thermometer, Trophy, Wifi, Zap } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { tempLevel } from '@/lib/format'
import type { DeviceView } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSettings } from '@/stores/settings'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import RingGauge from '@/components/ui/RingGauge.vue'
import Sparkline from '@/components/ui/Sparkline.vue'
import Term from '@/components/ui/Term.vue'
import KeyValue from '@/components/ui/KeyValue.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

const props = defineProps<{ device: DeviceView }>()
const fmt = useFmt()
const live = useLive()
const settings = useSettings()

const t = computed(() => props.device.telemetry)
const hash = computed(() => fmt.splitHash(props.device.hashrate_smooth_hs ?? t.value?.hashrate_hs))
const perf = computed(() => {
  const exp = t.value?.hashrate_expected_hs
  const cur = props.device.hashrate_smooth_hs ?? t.value?.hashrate_hs
  return exp && cur ? (cur / exp) * 100 : null
})
const warn = computed(() => settings.data?.alerts.temp_warn_c ?? 75)
const crit = computed(() => settings.data?.alerts.temp_crit_c ?? 85)
const tl = computed(() => tempLevel(t.value?.temp_asic_c, warn.value, crit.value))
const tempTone = computed(() => (tl.value === 'crit' ? 'bad' : tl.value === 'warn' ? 'warn' : 'ok'))
const shares = computed(() => (t.value?.shares_accepted ?? 0) + (t.value?.shares_rejected ?? 0))
const netDiff = computed(() => live.network?.difficulty ?? t.value?.network_difficulty ?? null)
const bestProgress = computed(() => (t.value?.best_diff && netDiff.value ? t.value.best_diff / netDiff.value : null))
const pool = computed(() => t.value?.pools.find((p) => p.active) ?? t.value?.pools[0] ?? null)
const wifi = computed(() => {
  const r = t.value?.wifi_rssi_dbm
  if (r == null) return { label: '–', tone: undefined }
  if (r > -60) return { label: `${Math.round(r)} dBm · excellent`, tone: 'ok' as const }
  if (r > -70) return { label: `${Math.round(r)} dBm · good`, tone: 'ok' as const }
  if (r > -78) return { label: `${Math.round(r)} dBm · fair`, tone: 'warn' as const }
  return { label: `${Math.round(r)} dBm · weak`, tone: 'bad' as const }
})
const rejectReasons = computed(() => Object.entries(t.value?.rejected_reasons ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 4))
</script>

<template>
  <div class="grid gap-[var(--gap-grid)] md:grid-cols-2 xl:grid-cols-4" data-testid="detail-overview">
    <div class="md:col-span-2">
      <MetricCard title="Hashrate" :icon="Gauge">
        <div class="flex items-end justify-between gap-4">
          <div>
            <p class="flex items-baseline gap-2">
              <span class="text-gradient-accent tnum text-5xl leading-none font-bold tracking-tight" data-testid="detail-hashrate">{{ hash.value }}</span>
              <span class="text-lg font-medium text-subtle">{{ hash.unit }}</span>
            </p>
            <p v-if="perf !== null" class="mt-2 text-sm text-muted">
              <b :class="perf >= 95 ? 'text-ok' : perf >= 80 ? 'text-warn' : 'text-bad'">{{ perf.toFixed(0) }}%</b> of the {{ fmt.hashrate(t?.hashrate_expected_hs) }} it should deliver
            </p>
          </div>
          <Sparkline :values="device.spark_hashrate_hs" :width="150" :height="56" label="Recent hashrate" />
        </div>
        <dl class="mt-5 grid grid-cols-4 gap-3 border-t border-line pt-4 text-xs">
          <div v-for="[label, v] in [['1 min', t?.hashrate_1m_hs], ['10 min', t?.hashrate_10m_hs], ['1 hour', t?.hashrate_1h_hs], ['1 day', t?.hashrate_1d_hs ?? t?.hashrate_avg_hs]] as const" :key="label">
            <dt class="text-subtle">{{ label }}</dt>
            <dd class="tnum mt-1 text-sm font-medium text-fg">{{ v ? fmt.hashrate(v) : '–' }}</dd>
          </div>
        </dl>
      </MetricCard>
    </div>

    <MetricCard title="Temperature" :icon="Thermometer">
      <div class="flex items-center gap-4">
        <RingGauge :value="t?.temp_asic_c != null ? Math.min(1, t.temp_asic_c / (crit + 10)) : null" :size="84" :stroke="8" :tone="tempTone" label="ASIC temperature">
          <span class="tnum text-lg font-semibold text-fg">{{ fmt.tempValue(t?.temp_asic_c) }}<span class="text-xs text-subtle">{{ fmt.tempSymbol() }}</span></span>
        </RingGauge>
        <KeyValue
          class="min-w-0 flex-1"
          :rows="[
            { label: 'Chip', value: fmt.temp(t?.temp_asic_c, 1), tone: tl === 'crit' ? 'bad' : tl === 'warn' ? 'warn' : undefined },
            { label: 'Regulator', value: fmt.temp(t?.temp_vr_c, 1) },
            ...(t?.temp_board_c != null ? [{ label: 'Board', value: fmt.temp(t.temp_board_c, 1) }] : []),
          ]"
        />
      </div>
    </MetricCard>

    <MetricCard title="Power" :icon="Zap">
      <p class="tnum text-3xl leading-none font-semibold text-fg">{{ fmt.splitPower(t?.power_w).value }}<span class="ml-1 text-base text-subtle">{{ fmt.splitPower(t?.power_w).unit }}</span></p>
      <div class="mt-4">
        <KeyValue
          :rows="[
            { label: 'Efficiency', value: fmt.formatEfficiency(t?.efficiency_j_th) },
            { label: 'Input', value: t?.voltage_in_v != null ? `${t.voltage_in_v.toFixed(2)} V${t.current_a != null ? ` · ${t.current_a.toFixed(2)} A` : ''}` : '–' },
            ...(t?.power_source === 'manual' ? [{ label: 'Source', value: 'entered by you', tone: 'muted' as const }] : []),
          ]"
        />
      </div>
    </MetricCard>

    <MetricCard title="Shares" :icon="Share2">
      <p class="tnum text-3xl leading-none font-semibold text-fg">{{ fmt.formatNumber(t?.shares_accepted) }}</p>
      <p class="mt-1 text-xs text-subtle">accepted by the pool</p>
      <div class="mt-4">
        <KeyValue
          :rows="[
            { label: 'Rejected', value: fmt.formatNumber(t?.shares_rejected) },
            { label: 'Reject rate', value: shares >= 100 && t?.reject_rate_pct != null ? fmt.formatPercent(t.reject_rate_pct, 2) : 'too few to tell', tone: shares >= 100 && (t?.reject_rate_pct ?? 0) > 5 ? 'warn' : undefined },
            { label: 'Hardware errors', value: t?.hw_error_pct != null ? fmt.formatPercent(t.hw_error_pct, 3) : '–', tone: (t?.hw_error_pct ?? 0) > 2 ? 'warn' : undefined },
          ]"
        />
        <ul v-if="rejectReasons.length" class="mt-2 space-y-1 text-xs text-subtle">
          <li v-for="[why, n] in rejectReasons" :key="why" class="flex justify-between gap-3"><span class="truncate">{{ why }}</span><span class="tnum">{{ n }}</span></li>
        </ul>
      </div>
    </MetricCard>

    <MetricCard title="Best share" :icon="Trophy">
      <p class="text-gradient-accent tnum text-3xl leading-none font-bold">{{ fmt.formatDifficulty(t?.best_diff) }}</p>
      <p class="mt-1 text-xs text-subtle">since this miner was reset · <Term k="bestshare">what is this?</Term></p>
      <div class="mt-4 space-y-3">
        <KeyValue :rows="[{ label: 'This session', value: fmt.formatDifficulty(t?.best_session_diff) }]" />
        <div v-if="bestProgress !== null">
          <ProgressBar :value="Math.min(1, Math.log10(Math.max(1, t!.best_diff!)) / Math.log10(netDiff!))" :height="6" label="Best share on a log scale" />
          <p class="mt-1.5 text-[11px] text-subtle">{{ fmt.formatFraction(bestProgress, 4) }} of the way to a block</p>
        </div>
      </div>
    </MetricCard>

    <MetricCard title="Tuning" :icon="SlidersHorizontal">
      <KeyValue
        :rows="[
          { label: 'Frequency', value: t?.frequency_mhz != null ? `${Math.round(t.frequency_mhz)} MHz${t.frequency_actual_mhz != null && Math.abs(t.frequency_actual_mhz - t.frequency_mhz) > 2 ? ` (running ${Math.round(t.frequency_actual_mhz)})` : ''}` : '–' },
          { label: 'Core voltage', value: t?.core_voltage_mv != null ? `${Math.round(t.core_voltage_mv)} mV${t.core_voltage_actual_mv != null && Math.abs(t.core_voltage_actual_mv - t.core_voltage_mv) > 5 ? ` (actual ${Math.round(t.core_voltage_actual_mv)})` : ''}` : '–' },
          { label: 'ASIC', value: device.asic_model ? `${device.asic_model}${device.asic_count && device.asic_count > 1 ? ` × ${device.asic_count}` : ''}` : '–' },
        ]"
      />
    </MetricCard>

    <MetricCard title="Fan" :icon="Fan">
      <p class="tnum text-3xl leading-none font-semibold text-fg">{{ t?.fan_pct != null ? `${Math.round(t.fan_pct)}%` : t?.fan_rpm != null ? `${Math.round(t.fan_rpm)}` : '–' }}<span v-if="t?.fan_pct == null && t?.fan_rpm != null" class="ml-1 text-base text-subtle">rpm</span></p>
      <div class="mt-4">
        <KeyValue :rows="[{ label: 'Speed', value: t?.fan_rpm != null ? `${Math.round(t.fan_rpm).toLocaleString('en-US')} rpm` : '–', tone: t?.fan_rpm === 0 && (t?.temp_asic_c ?? 0) > 50 ? 'bad' : undefined }, ...(t?.fan2_rpm != null ? [{ label: 'Second fan', value: `${Math.round(t.fan2_rpm).toLocaleString('en-US')} rpm` }] : [])]" />
      </div>
    </MetricCard>

    <MetricCard title="Health" :icon="Activity">
      <KeyValue
        :rows="[
          { label: 'Uptime', value: fmt.formatUptime(t?.uptime_s) },
          { label: 'Firmware', value: device.firmware ?? t?.firmware ?? '–' },
          { label: 'WiFi', value: wifi.label, tone: wifi.tone },
          ...(t?.free_heap_bytes != null ? [{ label: 'Free memory', value: fmt.formatBytes(t.free_heap_bytes) }] : []),
          ...(t?.cpu_usage_pct != null ? [{ label: 'Processor', value: `${Math.round(t.cpu_usage_pct)}%` }] : []),
          { label: 'Answered in', value: device.last_poll_ms != null ? `${Math.round(device.last_poll_ms)} ms` : '–' },
        ]"
      />
    </MetricCard>

    <div class="md:col-span-2">
      <MetricCard title="Pool" :icon="Network">
        <template v-if="pool">
          <KeyValue
            :rows="[
              { label: 'Connected to', value: `${pool.url ?? '?'}${pool.port ? ':' + pool.port : ''}`, mono: true },
              { label: 'Role', value: t?.using_fallback ? 'Fallback (the primary is not answering)' : (pool.role === 'fallback' ? 'Fallback' : 'Primary'), tone: t?.using_fallback ? 'warn' : undefined },
              { label: 'Payout address', value: fmt.shortAddress(pool.address), title: pool.address ?? undefined, mono: true },
              { label: 'Worker', value: pool.worker ?? '–' },
              { label: 'Share difficulty', value: pool.difficulty ? fmt.formatDifficulty(pool.difficulty) : fmt.formatDifficulty(t?.pool_difficulty) },
              { label: 'Latency', value: (pool.ping_ms ?? t?.pool_ping_ms) != null ? `${Math.round((pool.ping_ms ?? t?.pool_ping_ms)!)} ms` : '–' },
            ]"
          />
        </template>
        <p v-else class="text-sm text-muted">This miner does not report its pool.</p>
      </MetricCard>
    </div>

    <div class="md:col-span-2 xl:col-span-4">
      <MetricCard title="Last 6 hours" :icon="Wifi">
        <HistoryChart :device-id="device.id" :metrics="['hashrate_hs', 'temp_asic_c']" range="6h" :height="240" aria-label="Hashrate and temperature, last six hours" />
      </MetricCard>
    </div>
  </div>
</template>
