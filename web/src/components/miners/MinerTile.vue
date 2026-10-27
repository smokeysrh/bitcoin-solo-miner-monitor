<script setup lang="ts">
import { Flame, Thermometer, WifiOff, Zap } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { tempLevel } from '@/lib/format'
import type { DeviceView } from '@/lib/types'
import { useSettings } from '@/stores/settings'
import Sparkline from '@/components/ui/Sparkline.vue'
import StatusDot from '@/components/ui/StatusDot.vue'

const props = defineProps<{ device: DeviceView; dense?: boolean }>()
const fmt = useFmt()
const settings = useSettings()
const now = useNowSec()

const t = computed(() => props.device.telemetry)
const hash = computed(() => fmt.splitHash(props.device.hashrate_smooth_hs ?? t.value?.hashrate_hs))
const offline = computed(() => props.device.status === 'offline')
const level = computed(() => tempLevel(t.value?.temp_asic_c, settings.data?.alerts.temp_warn_c ?? 75, settings.data?.alerts.temp_crit_c ?? 85))
const tempTone = computed(() => ({ ok: 'text-muted', warn: 'text-warn', crit: 'text-bad', none: 'text-subtle' })[level.value])
const sparkColor = computed(() => (offline.value ? 'var(--fg-subtle)' : props.device.status === 'degraded' ? 'var(--warn)' : 'var(--accent)'))
const down = computed(() => (props.device.status_since ? fmt.formatDuration(now.value - props.device.status_since) : null))
</script>

<template>
  <RouterLink
    :to="`/miners/${device.id}`"
    :class="[
      'card card-hover group relative block overflow-hidden p-[var(--pad-card)] outline-none focus-visible:ring-2 focus-visible:ring-accent',
    ]"
    :data-testid="`miner-tile-${device.id}`"
    :aria-label="`${device.name}, ${device.status}`"
  >
    <span
      v-if="device.status === 'degraded' || offline"
      :class="['absolute inset-x-0 top-0 h-0.5', offline ? 'bg-bad' : 'bg-warn']"
      aria-hidden="true"
    />
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="flex items-center gap-2 text-sm font-semibold text-fg">
          <StatusDot :status="device.status" />
          <span class="truncate">{{ device.name }}</span>
        </p>
        <p class="mt-0.5 truncate text-xs text-subtle">{{ device.model_override ?? device.model }}<template v-if="device.tags.length"> · {{ device.tags.join(', ') }}</template></p>
      </div>
      <Sparkline v-if="!dense" :values="device.spark_hashrate_hs" :width="84" :height="30" :color="sparkColor" label="Recent hashrate" />
    </div>

    <div v-if="!offline" class="mt-4 flex items-end justify-between gap-3">
      <p class="tnum leading-none font-semibold tracking-tight text-fg">
        <span class="text-[28px]">{{ hash.value }}</span> <span class="text-sm font-medium text-subtle">{{ hash.unit }}</span>
      </p>
    </div>
    <div v-else class="mt-4 flex items-center gap-2 text-sm text-bad">
      <WifiOff class="size-4 shrink-0" aria-hidden="true" />
      <span class="truncate">Offline<template v-if="down"> for {{ down }}</template></span>
    </div>

    <p v-if="device.status === 'degraded' && device.status_reason" class="mt-2 flex items-center gap-1.5 truncate text-xs text-warn">
      <Flame class="size-3.5 shrink-0" aria-hidden="true" />{{ device.status_reason }}
    </p>
    <p v-else-if="offline && device.last_error" class="mt-2 truncate text-xs text-subtle">{{ device.last_error }}</p>

    <dl v-if="t && !offline" class="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-line pt-3 text-xs">
      <div class="flex items-center gap-1.5" :class="tempTone" title="ASIC temperature">
        <Thermometer class="size-3.5" aria-hidden="true" /><dt class="sr-only">Temperature</dt><dd class="tnum font-medium">{{ fmt.temp(t.temp_asic_c) }}</dd>
      </div>
      <div class="flex items-center gap-1.5 text-muted" title="Power">
        <Zap class="size-3.5" aria-hidden="true" /><dt class="sr-only">Power</dt><dd class="tnum font-medium">{{ fmt.formatPower(t.power_w) }}</dd>
      </div>
      <div class="ml-auto text-muted" title="Efficiency, lower is better">
        <dt class="sr-only">Efficiency</dt><dd class="tnum font-medium">{{ fmt.formatEfficiency(t.efficiency_j_th) }}</dd>
      </div>
    </dl>
  </RouterLink>
</template>
