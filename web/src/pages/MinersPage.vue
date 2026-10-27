<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { CheckSquare, Cpu, Flashlight, LayoutGrid, Pause, Play, Plus, Radar, RotateCcw, Rows3, Search, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useUi } from '@/stores/ui'
import BulkActionDialog from '@/components/miners/BulkActionDialog.vue'
import MinerTable, { type SortKey } from '@/components/miners/MinerTable.vue'
import MinerTile from '@/components/miners/MinerTile.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Input from '@/components/ui/Input.vue'
import Segmented from '@/components/ui/Segmented.vue'
import Select from '@/components/ui/Select.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import type { DeviceView } from '@/lib/types'

type StatusFilter = 'all' | 'online' | 'attention' | 'offline' | 'paused'
type GroupBy = 'none' | 'group' | 'model' | 'status'

const live = useLive()
const settings = useSettings()
const session = useSession()
const ui = useUi()
const fmt = useFmt()

const q = ref('')
const status = ref<StatusFilter>('all')
const tag = ref<string>('')
const groupBy = useStorage<GroupBy>('bsmm.miners.groupBy', 'none')
const sortKey = useStorage<SortKey>('bsmm.miners.sortKey', 'name')
const sortDir = useStorage<'asc' | 'desc'>('bsmm.miners.sortDir', 'asc')
const selecting = ref(false)
const selected = ref<Set<string>>(new Set())
const bulk = ref<{ open: boolean; action: string }>({ open: false, action: 'restart' })

const view = computed({
  get: () => settings.data?.ui.view_miners ?? 'grid',
  set: (v: 'grid' | 'table') => void settings.patch({ ui: { view_miners: v } }).catch(() => undefined),
})

const STATUS_RANK: Record<string, number> = { offline: 0, degraded: 1, paused: 2, unknown: 3, online: 4, disabled: 5 }
const matchesStatus = (d: DeviceView, f: StatusFilter): boolean =>
  f === 'all' || (f === 'attention' ? d.status === 'degraded' : f === 'online' ? d.status === 'online' : d.status === f)

const counts = computed(() => {
  const c = { all: live.devices.length, online: 0, attention: 0, offline: 0, paused: 0 }
  for (const d of live.devices) {
    if (d.status === 'online') c.online++
    else if (d.status === 'degraded') c.attention++
    else if (d.status === 'offline') c.offline++
    else if (d.status === 'paused') c.paused++
  }
  return c
})
const allTags = computed(() => [...new Set(live.devices.flatMap((d) => d.tags))].sort())

function sortValue(d: DeviceView, key: SortKey): number | string {
  const t = d.telemetry
  switch (key) {
    case 'name':
      return d.name
    case 'status':
      return STATUS_RANK[d.status] ?? 9
    case 'hashrate':
      return d.hashrate_smooth_hs ?? t?.hashrate_hs ?? -1
    case 'temp':
      return t?.temp_asic_c ?? -1
    case 'power':
      return t?.power_w ?? -1
    case 'efficiency':
      return t?.efficiency_j_th ?? Number.POSITIVE_INFINITY
    case 'shares':
      return t?.shares_accepted ?? -1
    case 'best':
      return t?.best_diff ?? -1
    case 'uptime':
      return t?.uptime_s ?? -1
  }
}

const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase()
  return live.devices.filter((d) => {
    if (!matchesStatus(d, status.value)) return false
    if (tag.value && !d.tags.includes(tag.value)) return false
    if (!needle) return true
    return [d.name, d.model, d.model_override, d.host, d.mac, d.group, d.hostname, ...d.tags].some((s) => s?.toLowerCase().includes(needle))
  })
})

const sorted = computed(() => {
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...filtered.value].sort((a, b) => {
    const x = sortValue(a, sortKey.value)
    const y = sortValue(b, sortKey.value)
    const c = typeof x === 'string' || typeof y === 'string' ? String(x).localeCompare(String(y), undefined, { numeric: true }) : x - y
    return c * dir || a.name.localeCompare(b.name, undefined, { numeric: true })
  })
})

const sections = computed(() => {
  if (groupBy.value === 'none') return [{ label: '', devices: sorted.value }]
  const map = new Map<string, DeviceView[]>()
  for (const d of sorted.value) {
    const label =
      groupBy.value === 'group' ? (d.group ?? d.tags[0] ?? 'Ungrouped') : groupBy.value === 'model' ? (d.model_override ?? d.model) : (({ online: 'Online', degraded: 'Needs attention', offline: 'Offline', paused: 'Paused' } as Record<string, string>)[d.status] ?? 'Other')
    map.set(label, [...(map.get(label) ?? []), d])
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })).map(([label, devices]) => ({ label, devices }))
})

function sortBy(k: SortKey): void {
  if (sortKey.value === k) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else {
    sortKey.value = k
    sortDir.value = k === 'name' || k === 'status' || k === 'efficiency' ? 'asc' : 'desc'
  }
}

function toggle(id: string): void {
  const next = new Set(selected.value)
  if (!next.delete(id)) next.add(id)
  selected.value = next
}
function toggleAll(on: boolean): void {
  selected.value = on ? new Set(sorted.value.map((d) => d.id)) : new Set()
}
function stopSelecting(): void {
  selecting.value = false
  selected.value = new Set()
}
function tileClick(e: MouseEvent, d: DeviceView): void {
  if (!selecting.value) return
  e.preventDefault()
  e.stopPropagation()
  toggle(d.id)
}
function runBulk(action: string): void {
  bulk.value = { open: true, action }
}
function clearFilters(): void {
  q.value = ''
  status.value = 'all'
  tag.value = ''
}

const chips = computed<{ value: StatusFilter; label: string; n: number }[]>(() => [
  { value: 'all', label: 'All', n: counts.value.all },
  { value: 'online', label: 'Online', n: counts.value.online },
  { value: 'attention', label: 'Needs attention', n: counts.value.attention },
  { value: 'offline', label: 'Offline', n: counts.value.offline },
  { value: 'paused', label: 'Paused', n: counts.value.paused },
])
const hashShown = computed(() => fmt.hashrate(filtered.value.reduce((a, d) => a + (d.hashrate_smooth_hs ?? 0), 0)))
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 class="text-2xl font-semibold tracking-tight text-fg">Miners</h2>
        <p class="mt-1 text-sm text-muted" data-testid="miners-summary">
          <template v-if="live.deviceCount">{{ filtered.length }} shown · {{ hashShown }} together</template>
          <template v-else>None added yet</template>
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <Button v-if="session.canControl && live.deviceCount" :variant="selecting ? 'soft' : 'ghost'" size="sm" data-testid="select-mode" @click="selecting ? stopSelecting() : (selecting = true)">
          <template #icon><CheckSquare class="size-4" /></template>
          {{ selecting ? 'Done selecting' : 'Select' }}
        </Button>
        <Segmented
          v-model="view"
          label="Layout"
          size="sm"
          icon-only
          :options="[
            { value: 'grid', label: 'Cards', icon: LayoutGrid },
            { value: 'table', label: 'Table', icon: Rows3 },
          ]"
        />
        <Button v-if="session.canControl" variant="primary" size="sm" @click="ui.addMinerOpen = true">
          <template #icon><Plus class="size-4" /></template>
          Add miner
        </Button>
      </div>
    </header>

    <div v-if="!live.loaded" class="grid gap-[var(--gap-grid)] sm:grid-cols-2 xl:grid-cols-4" aria-busy="true">
      <Skeleton v-for="i in 4" :key="i" class="h-40 rounded-2xl" />
    </div>

    <EmptyState v-else-if="!live.deviceCount" :icon="Cpu" title="No miners yet" description="Scan your network and we will find your Bitaxe, NerdQAxe, Avalon, Antminer and similar miners for you.">
      <Button v-if="session.canControl" variant="primary" size="lg" @click="ui.addMinerOpen = true">
        <template #icon><Radar class="size-5" /></template>
        Scan my network
      </Button>
    </EmptyState>

    <template v-else>
      <div class="flex flex-wrap items-center gap-2.5">
        <div class="w-full sm:w-64">
          <Input v-model="q" placeholder="Search name, model, address…" size="sm" aria-label="Search miners" data-testid="miner-search">
            <template #end><Search class="mr-3 size-4 text-subtle" aria-hidden="true" /></template>
          </Input>
        </div>
        <div class="flex flex-wrap gap-1.5" role="group" aria-label="Filter by status">
          <button
            v-for="c in chips"
            :key="c.value"
            :class="[
              'inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors',
              status === c.value ? 'border-accent-line bg-accent-soft text-accent-text' : 'border-line text-muted hover:border-line-strong hover:text-fg',
              c.value !== 'all' && c.n === 0 && status !== c.value && 'hidden sm:inline-flex',
            ]"
            :aria-pressed="status === c.value"
            @click="status = c.value"
          >
            {{ c.label }} <span class="tnum text-subtle">{{ c.n }}</span>
          </button>
        </div>
        <div class="ml-auto flex flex-wrap items-center gap-2">
          <Select v-if="allTags.length" v-model="tag" size="sm" class="w-36" aria-label="Filter by tag" :options="[{ value: '', label: 'All tags' }, ...allTags.map((t) => ({ value: t, label: `#${t}` }))]" />
          <Select
            v-model="groupBy"
            size="sm"
            class="w-40"
            aria-label="Group by"
            :options="[
              { value: 'none', label: 'No grouping' },
              { value: 'group', label: 'Group by group' },
              { value: 'model', label: 'Group by model' },
              { value: 'status', label: 'Group by status' },
            ]"
          />
          <Select
            v-if="view === 'grid'"
            :model-value="sortKey"
            size="sm"
            class="w-40"
            aria-label="Sort by"
            :options="[
              { value: 'name', label: 'Sort: name' },
              { value: 'status', label: 'Sort: problems first' },
              { value: 'hashrate', label: 'Sort: hashrate' },
              { value: 'temp', label: 'Sort: temperature' },
              { value: 'efficiency', label: 'Sort: efficiency' },
            ]"
            @update:model-value="(v) => sortBy(v as SortKey)"
          />
        </div>
      </div>

      <EmptyState v-if="!filtered.length" compact :icon="Search" title="No miners match" description="Try a different search or clear the filters.">
        <Button size="sm" variant="secondary" @click="clearFilters">Clear filters</Button>
      </EmptyState>

      <template v-else>
        <div v-for="s in sections" :key="s.label" class="space-y-3">
          <h3 v-if="s.label" class="flex items-center gap-2 text-sm font-semibold text-fg">
            {{ s.label }} <span class="rounded-full bg-surface-3 px-2 py-0.5 text-xs font-medium text-muted">{{ s.devices.length }}</span>
          </h3>
          <div v-if="view === 'grid'" class="grid gap-[var(--gap-grid)] sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4" data-testid="miner-grid">
            <div v-for="d in s.devices" :key="d.id" class="relative" @click.capture="tileClick($event, d)">
              <MinerTile :device="d" :class="selected.has(d.id) && 'ring-2 ring-accent'" />
              <span v-if="selecting" class="pointer-events-none absolute top-3 right-3 grid size-6 place-items-center rounded-md border-2" :class="selected.has(d.id) ? 'border-accent bg-accent text-accent-fg' : 'border-line-strong bg-surface-2'">
                <svg v-if="selected.has(d.id)" viewBox="0 0 16 16" class="size-3.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 8 3.5 3.5L13 5" /></svg>
              </span>
            </div>
          </div>
          <MinerTable v-else :devices="s.devices" :selectable="selecting" :selected="selected" :sort-key="sortKey" :sort-dir="sortDir" @toggle="toggle" @toggle-all="toggleAll" @sort="sortBy" />
        </div>
      </template>
    </template>

    <Transition name="rise">
      <div v-if="selecting && selected.size" class="card sticky bottom-24 z-20 mx-auto flex max-w-3xl flex-wrap items-center gap-2 p-3 shadow-pop lg:bottom-6" role="toolbar" aria-label="Actions for selected miners" data-testid="bulk-bar">
        <span class="px-2 text-sm font-medium text-fg">{{ selected.size }} selected</span>
        <span class="mx-1 hidden h-5 w-px bg-line sm:block" aria-hidden="true" />
        <Button size="sm" variant="secondary" @click="runBulk('identify')"><template #icon><Flashlight class="size-4" /></template>Flash</Button>
        <Button size="sm" variant="secondary" @click="runBulk('restart')"><template #icon><RotateCcw class="size-4" /></template>Restart</Button>
        <Button size="sm" variant="secondary" @click="runBulk('pause')"><template #icon><Pause class="size-4" /></template>Pause</Button>
        <Button size="sm" variant="secondary" @click="runBulk('resume')"><template #icon><Play class="size-4" /></template>Resume</Button>
        <Button size="iconSm" variant="ghost" class="ml-auto" aria-label="Clear selection" @click="selected = new Set()"><X class="size-4" /></Button>
      </div>
    </Transition>

    <BulkActionDialog v-model:open="bulk.open" :action="bulk.action" :ids="[...selected]" @done="stopSelecting" />
  </div>
</template>

<style scoped>
.rise-enter-active,
.rise-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.rise-enter-from,
.rise-leave-to {
  opacity: 0;
  transform: translateY(14px);
}
</style>
