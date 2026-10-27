<script setup lang="ts">
import { History, ShieldCheck } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { api } from '@/lib/api'
import type { AppEvent, AuditEntry, DeviceView } from '@/lib/types'
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
const audit = ref<AuditEntry[]>([])
const loading = ref(true)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [e, a] = await Promise.all([api.events({ device_id: props.device.id, limit: 40 }), api.deviceAudit(props.device.id, 30)])
    events.value = e.events
    audit.value = a
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

const actionLabel: Record<string, string> = { restart: 'Restarted', identify: 'Flashed', pause: 'Paused', resume: 'Resumed', set_pool: 'Changed pool', set_fan: 'Changed fan', set_tuning: 'Changed tuning' }
</script>

<template>
  <div class="grid gap-[var(--gap-grid)] xl:grid-cols-2">
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

    <MetricCard title="Changes made from this app" :icon="ShieldCheck">
      <div v-if="loading" class="space-y-2"><Skeleton v-for="i in 3" :key="i" class="h-11 rounded-xl" /></div>
      <EmptyState v-else-if="!audit.length" compact title="Nothing changed yet" description="Every restart, pool or tuning change made through the app, the API or an AI agent is recorded here." />
      <ul v-else class="-my-1 divide-y divide-line" data-testid="device-audit">
        <li v-for="a in audit" :key="a.id" class="flex items-start gap-3 py-3">
          <span class="mt-1.5 size-2 shrink-0 rounded-full" :class="a.result.ok === false ? 'bg-bad' : 'bg-ok'" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <p class="text-sm text-fg">{{ actionLabel[a.action] ?? a.action }} <span class="text-subtle">by {{ a.actor }}</span></p>
            <p v-if="a.result.error || a.result.message" class="mt-0.5 text-xs" :class="a.result.ok === false ? 'text-bad' : 'text-subtle'">{{ a.result.error ?? a.result.message }}</p>
          </div>
          <time class="shrink-0 pt-0.5 text-xs text-subtle" :title="fmt.formatDateTime(a.ts)">{{ fmt.formatAgo(a.ts, now) }}</time>
        </li>
      </ul>
    </MetricCard>
  </div>
</template>
