<script setup lang="ts">
import { computed } from 'vue'
import { useNowSec } from '@/composables/useNowSec'
import { formatAgo } from '@/lib/format'
import { useLive } from '@/stores/live'
import StatusDot from '@/components/ui/StatusDot.vue'
import Tooltip from '@/components/ui/Tooltip.vue'

defineProps<{ compact?: boolean; large?: boolean }>()
// `large` is the regular pill scaled by 1.35: text 12px to 16.2px, padding 10x4px to 13.5x5.4px, gap 8px to 10.8px, dot 6px to 8px.
const REGULAR = 'gap-2 px-2.5 py-1 text-xs'
const LARGE = 'gap-[0.675rem] px-[0.84375rem] py-[0.3375rem] text-[1.0125rem]'
const live = useLive()
const now = useNowSec()

const view = computed(() => {
  switch (live.status) {
    case 'live':
      return { dot: 'live' as const, text: 'Live', tone: 'text-ok' }
    case 'reconnecting':
      return { dot: 'reconnecting' as const, text: 'Reconnecting', tone: 'text-warn' }
    case 'connecting':
      return { dot: 'unknown' as const, text: 'Connecting', tone: 'text-muted' }
    default:
      return { dot: 'offline' as const, text: 'Offline', tone: 'text-bad' }
  }
})
const detail = computed(() => (live.lastUpdate ? `Last update ${formatAgo(live.lastUpdate / 1000, now.value)}` : 'Waiting for data'))
</script>

<template>
  <Tooltip :text="detail">
    <span class="inline-flex items-center rounded-full border border-line bg-surface-2 font-medium" :class="[large ? LARGE : REGULAR, view.tone]" role="status" data-testid="live-badge">
      <StatusDot :status="view.dot" :size="large ? 'md' : 'sm'" />
      <span v-if="!compact">{{ view.text }}</span>
      <span v-else class="sr-only">{{ view.text }}</span>
    </span>
  </Tooltip>
</template>
