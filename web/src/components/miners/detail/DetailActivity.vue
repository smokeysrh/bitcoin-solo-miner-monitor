<script setup lang="ts">
import { History } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { api } from '@/lib/api'
import type { AppEvent, DeviceView } from '@/lib/types'
import { useNowSec } from '@/composables/useNowSec'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EventIcon from '@/components/ui/EventIcon.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

const props = defineProps<{ device: DeviceView }>()
const fmt = useFmt()
const now = useNowSec()
const live = useLive()

const events = ref<AppEvent[]>([])
const loading = ref(true)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const e = await api.events({ device_id: props.device.id, limit: 40 })
    events.value = e.events
  } catch (err) {
    error.value = err
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => props.device.id, load)
// a new event for this miner arrives over the stream: pull it in without a full reload
watch(
  () => live.events[0]?.id,
  () => live.events[0]?.device_id === props.device.id && void load(),
)
</script>

<template>
  <div class="grid gap-[var(--gap-grid)]">
    <MetricCard title="Events" :icon="History">
      <div v-if="loading" class="space-y-2"><Skeleton v-for="i in 4" :key="i" class="h-11 rounded-xl" /></div>
      <ErrorState v-else-if="error" compact :error="error" @retry="load" />
      <EmptyState v-else-if="!events.length" compact title="No events yet" description="Restarts, outages and new best shares for this miner will be listed here." />
      <ul v-else class="-my-1 divide-y divide-line" data-testid="device-events">
        <li v-for="e in events" :key="e.id ?? e.ts" class="flex items-start gap-3 py-3">
          <EventIcon :type="e.type" :severity="e.severity" />
          <div class="min-w-0 flex-1">
            <p class="text-sm text-fg">{{ e.title }}</p>
            <p v-if="e.body" class="mt-0.5 text-xs text-subtle">{{ e.body }}</p>
          </div>
          <time class="shrink-0 pt-0.5 text-xs text-subtle" :title="fmt.formatDateTime(e.ts)">{{ fmt.formatAgo(e.ts, now) }}</time>
        </li>
      </ul>
    </MetricCard>
  </div>
</template>
