<script setup lang="ts">
// Wall display tile: name, status, hashrate and temperature at a size that reads from across a room.
// Text is sized from the screen's short side (vmin) times `--k`, which the wall display sets from the miner count.
// MinerTile stays as it is for the normal Miners page.
import { Thermometer } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { tempLevel } from '@/lib/format'
import type { DeviceStatus, DeviceView } from '@/lib/types'
import { useSettings } from '@/stores/settings'

const props = defineProps<{ device: DeviceView }>()
const fmt = useFmt()
const settings = useSettings()
const now = useNowSec()

// The status is always written as a word; the colour only backs it up.
const STATUS_LABEL: Record<DeviceStatus, string> = {
  online: 'Online',
  degraded: 'Degraded',
  offline: 'Offline',
  paused: 'Paused',
  unknown: 'Unknown',
  disabled: 'Disabled',
}
const STATUS_TONE: Record<DeviceStatus, string> = {
  online: 'text-ok',
  degraded: 'text-warn',
  offline: 'text-bad',
  paused: 'text-info',
  unknown: 'text-muted',
  disabled: 'text-muted',
}

const t = computed(() => props.device.telemetry)
const hash = computed(() => fmt.splitHash(props.device.hashrate_smooth_hs ?? t.value?.hashrate_hs))
const offline = computed(() => props.device.status === 'offline')
const level = computed(() => tempLevel(t.value?.temp_asic_c, settings.data?.alerts.temp_warn_c ?? 75, settings.data?.alerts.temp_crit_c ?? 85))
const tempTone = computed(() => ({ ok: 'text-fg', warn: 'text-warn', crit: 'text-bad', none: 'text-muted' })[level.value])
const down = computed(() => (props.device.status_since ? fmt.formatDuration(now.value - props.device.status_since) : null))
</script>

<template>
  <div class="card kiosk-tile" role="group" :aria-label="`${device.name}, ${device.status}`" :data-testid="`miner-tile-${device.id}`">
    <p class="kt-name font-semibold text-fg">{{ device.name }}</p>
    <p class="kt-status font-medium" :class="STATUS_TONE[device.status]">
      <span>{{ STATUS_LABEL[device.status] }}</span>
      <span v-if="offline && down" class="text-muted"> for {{ down }}</span>
    </p>
    <p v-if="device.status === 'degraded' && device.status_reason" class="kt-note text-warn">{{ device.status_reason }}</p>
    <p v-if="!offline" class="kt-hash tnum font-semibold text-fg">
      <span class="kt-hash-value">{{ hash.value }}</span>
      <span class="kt-hash-unit text-muted">{{ hash.unit }}</span>
    </p>
    <dl v-if="t && !offline" class="kt-temp tnum font-medium" :class="tempTone">
      <dt class="sr-only">Temperature</dt>
      <dd class="kt-temp-value"><Thermometer class="kt-icon" aria-hidden="true" />{{ fmt.temp(t.temp_asic_c) }}</dd>
    </dl>
  </div>
</template>

<style scoped>
.kiosk-tile {
  display: flex;
  flex-direction: column;
  gap: calc(1vmin * var(--k, 1));
  padding: max(0.75rem, calc(2vmin * var(--k, 1)));
}
.kt-name {
  font-size: max(1.125rem, calc(4vmin * var(--k, 1)));
  line-height: 1.2;
  overflow-wrap: anywhere;
}
.kt-status {
  font-size: max(0.875rem, calc(2.6vmin * var(--k, 1)));
  line-height: 1.3;
}
.kt-note {
  font-size: max(0.875rem, calc(2.2vmin * var(--k, 1)));
  line-height: 1.3;
}
.kt-hash {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  column-gap: 0.4rem;
  line-height: 1.2;
}
.kt-hash-value {
  font-size: max(1.75rem, calc(9vmin * var(--k, 1)));
}
.kt-hash-unit {
  font-size: max(0.875rem, calc(3.2vmin * var(--k, 1)));
}
.kt-temp {
  font-size: max(1rem, calc(3.6vmin * var(--k, 1)));
  line-height: 1.3;
}
.kt-temp-value {
  display: flex;
  align-items: center;
  gap: 0.3em;
}
.kt-icon {
  width: 0.9em;
  height: 0.9em;
  flex-shrink: 0;
}
</style>
