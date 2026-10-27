<script setup lang="ts">
import { Bitcoin, CircleCheck, Info, OctagonAlert, RefreshCw, Trophy, TriangleAlert, Wifi, WifiOff } from 'lucide-vue-next'
import { computed } from 'vue'
import type { Severity } from '@/lib/types'

const props = defineProps<{ type: string; severity: Severity }>()

const icon = computed(() => {
  switch (props.type) {
    case 'new_best_share':
      return Trophy
    case 'block_found':
      return Bitcoin
    case 'device_offline':
      return WifiOff
    case 'device_online':
      return Wifi
    case 'device_restarted':
      return RefreshCw
  }
  return { info: Info, success: CircleCheck, warning: TriangleAlert, critical: OctagonAlert }[props.severity]
})
const tone = computed(() => ({ info: 'bg-info-soft text-info', success: 'bg-ok-soft text-ok', warning: 'bg-warn-soft text-warn', critical: 'bg-bad-soft text-bad' })[props.severity])
</script>

<template>
  <span :class="['grid size-8 shrink-0 place-items-center rounded-full', tone]"><component :is="icon" class="size-4" aria-hidden="true" /></span>
</template>
