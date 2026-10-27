<script setup lang="ts">
import { ArrowDown, ArrowUp, ExternalLink, EllipsisVertical, Eye, Flashlight, Pause, Play, RefreshCw, RotateCcw, Trash2 } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { useMinerActions } from '@/composables/useMinerActions'
import { tempLevel } from '@/lib/format'
import type { DeviceView } from '@/lib/types'
import { useSettings } from '@/stores/settings'
import Badge, { type Tone } from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Menu, { type MenuItem } from '@/components/ui/Menu.vue'
import Sparkline from '@/components/ui/Sparkline.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { useRouter } from 'vue-router'

export type SortKey = 'name' | 'status' | 'hashrate' | 'temp' | 'power' | 'efficiency' | 'shares' | 'best' | 'uptime'

const props = defineProps<{
  devices: DeviceView[]
  selectable?: boolean
  selected: Set<string>
  sortKey: SortKey
  sortDir: 'asc' | 'desc'
}>()
const emit = defineEmits<{ toggle: [id: string]; toggleAll: [on: boolean]; sort: [key: SortKey] }>()

const fmt = useFmt()
const settings = useSettings()
const actions = useMinerActions()
const router = useRouter()

/** aria-sort belongs on the column header cell, not on the button inside it */
const sortAttr = (key: SortKey): 'ascending' | 'descending' | undefined => (props.sortKey === key ? (props.sortDir === 'asc' ? 'ascending' : 'descending') : undefined)

const allSelected = computed(() => props.devices.length > 0 && props.devices.every((d) => props.selected.has(d.id)))

const statusMeta: Record<string, { label: string; tone: Tone }> = {
  online: { label: 'Online', tone: 'ok' },
  degraded: { label: 'Needs attention', tone: 'warn' },
  offline: { label: 'Offline', tone: 'bad' },
  paused: { label: 'Paused', tone: 'info' },
  unknown: { label: 'Connecting', tone: 'neutral' },
  disabled: { label: 'Disabled', tone: 'neutral' },
}

const cols: { key: SortKey; label: string; align?: 'right'; hideBelow?: string }[] = [
  { key: 'hashrate', label: 'Hashrate', align: 'right' },
  { key: 'temp', label: 'Temp', align: 'right' },
  { key: 'power', label: 'Power', align: 'right' },
  { key: 'efficiency', label: 'Efficiency', align: 'right', hideBelow: 'lg' },
  { key: 'shares', label: 'Shares', align: 'right', hideBelow: 'xl' },
  { key: 'best', label: 'Best share', align: 'right', hideBelow: 'xl' },
  { key: 'uptime', label: 'Uptime', align: 'right', hideBelow: 'xl' },
]
const hide = (b?: string): string => (b === 'lg' ? 'hidden lg:table-cell' : b === 'xl' ? 'hidden xl:table-cell' : '')

function tempTone(d: DeviceView): string {
  const l = tempLevel(d.telemetry?.temp_asic_c, settings.data?.alerts.temp_warn_c ?? 75, settings.data?.alerts.temp_crit_c ?? 85)
  return { ok: 'text-fg', warn: 'text-warn', crit: 'text-bad', none: 'text-subtle' }[l]
}

function rowMenu(d: DeviceView): MenuItem[] {
  const paused = d.status === 'paused'
  const items: MenuItem[] = [
    { label: 'Open details', icon: Eye, run: () => void router.push(`/miners/${d.id}`) },
    { label: 'Refresh now', icon: RefreshCw, run: () => void actions.pollNow(d) },
  ]
  if (d.web_url || d.host) items.push({ label: "Open the miner's own page", icon: ExternalLink, run: () => window.open(d.web_url ?? `http://${d.host}${d.port && d.port !== 80 ? ':' + d.port : ''}`, '_blank', 'noopener') })
  const control: MenuItem[] = []
  if (actions.can(d, 'identify')) control.push({ label: 'Flash to identify', icon: Flashlight, run: () => void actions.identify(d) })
  if (actions.can(d, 'pause')) control.push(paused ? { label: 'Resume mining', icon: Play, run: () => void actions.resume(d) } : { label: 'Pause mining', icon: Pause, run: () => void actions.pause(d) })
  if (actions.can(d, 'restart')) control.push({ label: 'Restart', icon: RotateCcw, run: () => void actions.restart(d) })
  if (control.length) items.push({ separator: true }, ...control)
  if (actions.can(d, 'restart') || d.allow_control) items.push({ separator: true }, { label: 'Stop monitoring', icon: Trash2, danger: true, run: () => void actions.remove(d) })
  return items
}
</script>

<template>
  <div class="card overflow-hidden">
    <div class="relative overflow-x-auto">
      <table class="w-full min-w-[720px] border-collapse text-sm" data-testid="miner-table">
        <thead>
          <tr class="border-b border-line text-xs text-subtle">
            <th v-if="selectable" class="w-10 py-3 pl-4">
              <input type="checkbox" class="size-4 accent-[var(--accent)]" :checked="allSelected" aria-label="Select all miners" @change="emit('toggleAll', ($event.target as HTMLInputElement).checked)" />
            </th>
            <th class="py-3 pr-3 pl-4 text-left font-medium" :aria-sort="sortAttr('name')">
              <button class="inline-flex items-center gap-1 hover:text-fg" @click="emit('sort', 'name')">
                Miner <component :is="sortDir === 'asc' ? ArrowUp : ArrowDown" v-if="sortKey === 'name'" class="size-3" />
              </button>
            </th>
            <th class="hidden py-3 pr-3 text-left font-medium md:table-cell" :aria-sort="sortAttr('status')">
              <button class="inline-flex items-center gap-1 hover:text-fg" @click="emit('sort', 'status')">
                Status <component :is="sortDir === 'asc' ? ArrowUp : ArrowDown" v-if="sortKey === 'status'" class="size-3" />
              </button>
            </th>
            <th v-for="c in cols" :key="c.key" :aria-sort="sortAttr(c.key)" :class="['py-3 pr-4 font-medium', c.align === 'right' ? 'text-right' : 'text-left', hide(c.hideBelow)]">
              <button class="inline-flex items-center gap-1 hover:text-fg" @click="emit('sort', c.key)">
                {{ c.label }} <component :is="sortDir === 'asc' ? ArrowUp : ArrowDown" v-if="sortKey === c.key" class="size-3" />
              </button>
            </th>
            <th class="w-12 py-3 pr-3"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="d in devices"
            :key="d.id"
            :class="['group border-b border-line/60 transition-colors last:border-0 hover:bg-surface-2/70', selected.has(d.id) && 'bg-accent-softer']"
            :data-testid="`miner-row-${d.id}`"
          >
            <td v-if="selectable" class="py-3 pl-4">
              <input type="checkbox" class="size-4 accent-[var(--accent)]" :checked="selected.has(d.id)" :aria-label="`Select ${d.name}`" @change="emit('toggle', d.id)" />
            </td>
            <td class="max-w-[260px] py-3 pr-3 pl-4">
              <RouterLink :to="`/miners/${d.id}`" class="flex items-center gap-2.5">
                <StatusDot :status="d.status" class="md:hidden" />
                <span class="min-w-0">
                  <span class="block truncate font-medium text-fg group-hover:text-accent-text">{{ d.name }}</span>
                  <span class="block truncate text-xs text-subtle">{{ d.model_override ?? d.model }} · <span class="font-mono">{{ d.host }}</span></span>
                </span>
              </RouterLink>
            </td>
            <td class="hidden py-3 pr-3 md:table-cell">
              <Badge :tone="statusMeta[d.status]?.tone ?? 'neutral'" dot size="sm">{{ statusMeta[d.status]?.label ?? d.status }}</Badge>
            </td>
            <td class="py-3 pr-4 text-right">
              <div class="flex items-center justify-end gap-3">
                <Sparkline class="hidden sm:block" :values="d.spark_hashrate_hs" :width="60" :height="22" :dot="false" :fill="false" :stroke-width="1.5" :color="d.status === 'offline' ? 'var(--fg-subtle)' : 'var(--accent)'" />
                <span class="tnum w-24 text-right font-medium text-fg">{{ d.status === 'offline' ? '–' : fmt.hashrate(d.hashrate_smooth_hs ?? d.telemetry?.hashrate_hs) }}</span>
              </div>
            </td>
            <td :class="['tnum py-3 pr-4 text-right font-medium', tempTone(d)]">{{ fmt.temp(d.telemetry?.temp_asic_c) }}</td>
            <td class="tnum py-3 pr-4 text-right text-muted">{{ fmt.formatPower(d.telemetry?.power_w) }}</td>
            <td class="tnum hidden py-3 pr-4 text-right text-muted lg:table-cell">{{ fmt.formatEfficiency(d.telemetry?.efficiency_j_th) }}</td>
            <td class="tnum hidden py-3 pr-4 text-right text-muted xl:table-cell">
              {{ fmt.formatNumber(d.telemetry?.shares_accepted) }}
              <span v-if="(d.telemetry?.shares_accepted ?? 0) + (d.telemetry?.shares_rejected ?? 0) >= 100 && d.telemetry?.reject_rate_pct != null" class="text-xs text-subtle">· {{ fmt.formatPercent(d.telemetry.reject_rate_pct, 1) }}</span>
            </td>
            <td class="tnum hidden py-3 pr-4 text-right text-muted xl:table-cell">{{ fmt.formatDifficulty(d.telemetry?.best_diff) }}</td>
            <td class="tnum hidden py-3 pr-4 text-right text-muted xl:table-cell">{{ fmt.formatUptime(d.telemetry?.uptime_s) }}</td>
            <td class="py-3 pr-3 text-right">
              <Menu :items="rowMenu(d)">
                <Button size="iconSm" variant="ghost" :aria-label="`Actions for ${d.name}`"><EllipsisVertical class="size-4" /></Button>
              </Menu>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
