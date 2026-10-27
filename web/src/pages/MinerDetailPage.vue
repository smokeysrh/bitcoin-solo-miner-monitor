<script setup lang="ts">
import { Activity, Braces, ChevronLeft, ExternalLink, Flashlight, LineChart, Network, Pause, Play, RefreshCw, RotateCcw, Settings2, SlidersHorizontal, WifiOff, Cpu, LayoutDashboard } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNowSec } from '@/composables/useNowSec'
import { useFmt } from '@/composables/useFmt'
import { useMinerActions } from '@/composables/useMinerActions'
import { useLive } from '@/stores/live'
import { useUi } from '@/stores/ui'
import DetailActivity from '@/components/miners/detail/DetailActivity.vue'
import DetailCharts from '@/components/miners/detail/DetailCharts.vue'
import DetailOverview from '@/components/miners/detail/DetailOverview.vue'
import DetailPools from '@/components/miners/detail/DetailPools.vue'
import DetailRaw from '@/components/miners/detail/DetailRaw.vue'
import DetailSettings from '@/components/miners/detail/DetailSettings.vue'
import DetailTuning from '@/components/miners/detail/DetailTuning.vue'
import Badge, { type Tone } from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import Tabs, { type TabDef } from '@/components/ui/Tabs.vue'

const props = defineProps<{ id: string }>()
const live = useLive()
const route = useRoute()
const router = useRouter()
const ui = useUi()
const fmt = useFmt()
const now = useNowSec()
const actions = useMinerActions()

const device = computed(() => live.byId(props.id))
const busy = ref<string | null>(null)

const tab = computed({
  get: () => (typeof route.query.tab === 'string' ? route.query.tab : 'overview'),
  set: (v: string) => void router.replace({ query: { ...route.query, tab: v === 'overview' ? undefined : v } }),
})

const statusMeta: Record<string, { label: string; tone: Tone }> = {
  online: { label: 'Online', tone: 'ok' },
  degraded: { label: 'Needs attention', tone: 'warn' },
  offline: { label: 'Offline', tone: 'bad' },
  paused: { label: 'Paused', tone: 'info' },
  unknown: { label: 'Connecting', tone: 'neutral' },
  disabled: { label: 'Monitoring off', tone: 'neutral' },
}

const tabs = computed<TabDef[]>(() => {
  const d = device.value
  const list: TabDef[] = [
    { value: 'overview', label: 'Overview', icon: LayoutDashboard },
    { value: 'charts', label: 'Charts', icon: LineChart },
    { value: 'pools', label: 'Pools', icon: Network },
  ]
  if (d && (d.capabilities.includes('set_frequency') || d.capabilities.includes('set_fan'))) list.push({ value: 'tuning', label: 'Tuning', icon: SlidersHorizontal })
  list.push({ value: 'settings', label: 'Settings', icon: Settings2 }, { value: 'activity', label: 'Activity', icon: Activity }, { value: 'raw', label: 'Raw data', icon: Braces })
  return list
})

// the browser tab (and history) should say which miner this is, not just "Miner"
watch(
  () => device.value?.name,
  (name) => {
    if (name) document.title = `${name} · Solo Miner Monitor`
  },
  { immediate: true },
)

const webUrl = computed(() => {
  const d = device.value
  if (!d) return null
  return d.web_url ?? (d.family === 'avalon' || d.family === 'antminer' || d.family === 'cgminer' ? `http://${d.host}` : `http://${d.host}${d.port && d.port !== 80 ? ':' + d.port : ''}`)
})

async function wrap(key: string, fn: () => Promise<unknown>): Promise<void> {
  busy.value = key
  try {
    await fn()
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <div class="space-y-5">
    <RouterLink to="/miners" class="inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-fg"><ChevronLeft class="size-4" aria-hidden="true" /> All miners</RouterLink>

    <div v-if="!live.loaded" class="space-y-4" aria-busy="true"><Skeleton class="h-12 w-72 rounded-xl" /><Skeleton class="h-64 rounded-2xl" /></div>

    <EmptyState v-else-if="!device" :icon="Cpu" title="This miner is not being monitored" description="It may have been removed, or the link is old.">
      <Button variant="primary" to="/miners">See my miners</Button>
    </EmptyState>

    <template v-else>
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <h2 class="flex flex-wrap items-center gap-3 text-2xl font-semibold tracking-tight text-fg">
            <StatusDot :status="device.status" size="lg" />
            <span class="truncate" data-testid="device-title">{{ device.name }}</span>
            <Badge :tone="statusMeta[device.status]?.tone ?? 'neutral'" data-testid="device-status">{{ statusMeta[device.status]?.label ?? device.status }}</Badge>
          </h2>
          <p class="mt-1.5 text-sm text-muted">
            {{ device.model_override ?? device.model }} · <span class="font-mono">{{ device.host }}</span>
            <template v-if="device.firmware"> · firmware {{ device.firmware }}</template>
            <template v-if="device.last_seen_at"> · seen {{ fmt.formatAgo(device.last_seen_at, now) }}</template>
          </p>
          <p v-if="device.status === 'degraded' && device.status_reason" class="mt-2 text-sm text-warn">{{ device.status_reason }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="secondary" :loading="busy === 'poll'" @click="wrap('poll', () => actions.pollNow(device!))">
            <template #icon><RefreshCw class="size-4" /></template>Refresh
          </Button>
          <Button v-if="actions.can(device, 'identify')" size="sm" variant="secondary" :loading="busy === 'identify'" @click="wrap('identify', () => actions.identify(device!))">
            <template #icon><Flashlight class="size-4" /></template>Flash
          </Button>
          <Button v-if="actions.can(device, 'pause') && device.status === 'paused'" size="sm" variant="secondary" :loading="busy === 'resume'" @click="wrap('resume', () => actions.resume(device!))">
            <template #icon><Play class="size-4" /></template>Resume
          </Button>
          <Button v-else-if="actions.can(device, 'pause')" size="sm" variant="secondary" :loading="busy === 'pause'" @click="wrap('pause', () => actions.pause(device!))">
            <template #icon><Pause class="size-4" /></template>Pause
          </Button>
          <Button v-if="actions.can(device, 'restart')" size="sm" variant="secondary" :loading="busy === 'restart'" data-testid="restart" @click="wrap('restart', () => actions.restart(device!))">
            <template #icon><RotateCcw class="size-4" /></template>Restart
          </Button>
          <Button v-if="webUrl" size="sm" variant="ghost" :href="webUrl" target="_blank" rel="noopener noreferrer">
            <template #icon><ExternalLink class="size-4" /></template>Its own page
          </Button>
        </div>
      </header>

      <div v-if="device.status === 'offline'" class="flex gap-3 rounded-2xl border border-bad/30 bg-bad-soft p-4" role="alert">
        <WifiOff class="mt-0.5 size-5 shrink-0 text-bad" aria-hidden="true" />
        <div class="min-w-0 text-sm">
          <p class="font-medium text-fg">Not answering{{ device.status_since ? ` for ${fmt.formatDuration(now - device.status_since)}` : '' }}</p>
          <p v-if="device.last_error" class="mt-0.5 text-muted">Last error: {{ device.last_error }}</p>
          <ul class="mt-2 list-disc space-y-0.5 pl-5 text-[13px] text-muted">
            <li>Is it powered, and is the WiFi or cable connected?</li>
            <li>Did its address change? Open the Settings tab to update it, or scan the network again.</li>
          </ul>
          <div class="mt-3 flex gap-2">
            <Button size="sm" variant="secondary" @click="actions.pollNow(device)">Check again now</Button>
            <Button size="sm" variant="ghost" @click="ui.addMinerOpen = true">Scan the network</Button>
          </div>
        </div>
      </div>

      <Tabs v-model="tab" :tabs="tabs" label="Miner sections">
        <template #overview><DetailOverview :device="device" /></template>
        <template #charts><DetailCharts :device="device" /></template>
        <template #pools><DetailPools :device="device" /></template>
        <template #tuning><DetailTuning :device="device" /></template>
        <template #settings><DetailSettings :device="device" /></template>
        <template #activity><DetailActivity :device="device" /></template>
        <template #raw><DetailRaw :device="device" /></template>
      </Tabs>
    </template>
  </div>
</template>
