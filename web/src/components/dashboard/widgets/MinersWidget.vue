<script setup lang="ts">
import { Cpu, Plus, Radar } from 'lucide-vue-next'
import { computed } from 'vue'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import MinerTile from '@/components/miners/MinerTile.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import WidgetFrame from '../WidgetFrame.vue'

const MAX = 12
const live = useLive()
const ui = useUi()
const session = useSession()

const rank: Record<string, number> = { offline: 0, degraded: 1, paused: 2, unknown: 3, online: 4, disabled: 5 }
const sorted = computed(() => [...live.devices].sort((a, b) => (rank[a.status] ?? 9) - (rank[b.status] ?? 9) || a.name.localeCompare(b.name, undefined, { numeric: true })))
const shown = computed(() => sorted.value.slice(0, MAX))
</script>

<template>
  <WidgetFrame title="Miners" :subtitle="live.deviceCount ? `${live.deviceCount} monitored · problems first` : undefined" to="/miners" link-label="All miners">
    <div v-if="shown.length" class="grid gap-[var(--gap-grid)] sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4" data-testid="widget-miners">
      <MinerTile v-for="d in shown" :key="d.id" :device="d" />
    </div>
    <EmptyState v-else compact :icon="Cpu" title="No miners yet" description="Scan your network and we will find them for you. It takes about twenty seconds.">
      <Button v-if="session.canControl" variant="primary" @click="ui.addMinerOpen = true">
        <template #icon><Radar class="size-4" /></template>
        Scan my network
      </Button>
      <Button v-if="session.canControl" variant="ghost" @click="ui.addMinerOpen = true">
        <template #icon><Plus class="size-4" /></template>
        Add by address
      </Button>
    </EmptyState>
    <p v-if="live.deviceCount > MAX" class="mt-3 text-center text-xs text-subtle">Showing {{ MAX }} of {{ live.deviceCount }}. <RouterLink to="/miners" class="text-accent-text underline underline-offset-2 hover:no-underline">See all</RouterLink></p>
  </WidgetFrame>
</template>
