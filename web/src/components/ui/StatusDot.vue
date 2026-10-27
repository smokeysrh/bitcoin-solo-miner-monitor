<script setup lang="ts">
import { computed } from 'vue'
import type { DeviceStatus } from '@/lib/types'

const props = withDefaults(defineProps<{ status: DeviceStatus | 'live' | 'reconnecting'; size?: 'sm' | 'md' | 'lg'; pulse?: boolean }>(), {
  size: 'md',
  pulse: true,
})

const color = computed(() => {
  switch (props.status) {
    case 'online':
    case 'live':
      return 'bg-ok'
    case 'degraded':
    case 'reconnecting':
      return 'bg-warn'
    case 'offline':
      return 'bg-bad'
    case 'paused':
      return 'bg-info'
    default:
      return 'bg-subtle'
  }
})
const label = computed(() => props.status)
const animate = computed(() => props.pulse && (props.status === 'online' || props.status === 'live'))
const dim = computed(() => ({ sm: 'size-1.5', md: 'size-2', lg: 'size-2.5' })[props.size])
</script>

<template>
  <span class="relative inline-flex shrink-0 items-center justify-center" role="img" :aria-label="label">
    <span v-if="animate" :class="[dim, color, 'absolute rounded-full animate-ping-soft']" aria-hidden="true" />
    <span :class="[dim, color, 'relative rounded-full']" aria-hidden="true" />
  </span>
</template>
