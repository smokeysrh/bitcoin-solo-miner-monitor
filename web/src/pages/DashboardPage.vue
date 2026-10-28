<script setup lang="ts">
import { Check, EyeOff, GripVertical, Maximize2, Pencil, Plus, RotateCcw, Radar } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { useNowSec } from '@/composables/useNowSec'
import { describeError } from '@/lib/api'
import { formatAgo } from '@/lib/format'
import type { DashboardWidgetPlacement } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'
import { useUi } from '@/stores/ui'
import { availableWidgets, cycleSpan, resolveLayout, SPAN_CLASS, SPAN_LABEL, WIDGET_BY_ID } from '@/components/dashboard/registry'
import Button from '@/components/ui/Button.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const live = useLive()
const settings = useSettings()
const session = useSession()
const toasts = useToasts()
const ui = useUi()
const now = useNowSec()

const saved = computed(() => resolveLayout(settings.data?.ui.dashboard, settings.simple))
const draft = ref<DashboardWidgetPlacement[]>([])
const editing = ref(false)
const saving = ref(false)

// What is on screen: the draft while editing, the saved layout otherwise. Widgets that mean nothing without a
// miner are skipped until one exists, so a brand-new install is not a wall of empty charts.
const visible = computed(() => {
  const list = editing.value ? draft.value : saved.value
  return list.filter((p) => WIDGET_BY_ID[p.id] && (editing.value || live.deviceCount > 0 || !WIDGET_BY_ID[p.id]!.needsMiners))
})
const tray = computed(() => availableWidgets(draft.value))
const noMiners = computed(() => live.loaded && live.deviceCount === 0)

function startEdit(): void {
  draft.value = saved.value.map((p) => ({ ...p }))
  editing.value = true
}

async function finish(): Promise<void> {
  saving.value = true
  try {
    await settings.patch({ ui: { dashboard: { version: 1, widgets: draft.value } } })
    editing.value = false
    toasts.success('Dashboard saved')
  } catch (e) {
    toasts.error('Could not save the layout', describeError(e))
  } finally {
    saving.value = false
  }
}

async function reset(): Promise<void> {
  try {
    await settings.patch({ ui: { dashboard: null } })
    draft.value = resolveLayout(null, settings.simple)
    toasts.success('Back to the default layout')
  } catch (e) {
    toasts.error('Could not reset the layout', describeError(e))
  }
}

function resize(p: DashboardWidgetPlacement): void {
  const def = WIDGET_BY_ID[p.id]
  if (def) p.span = cycleSpan(def, p.span)
}
function hide(id: string): void {
  draft.value = draft.value.filter((p) => p.id !== id)
}
function add(id: string): void {
  const def = WIDGET_BY_ID[id]
  if (def) draft.value = [...draft.value, { id, span: def.defaultSpan }]
}


const subtitle = computed(() => {
  const s = live.summary
  if (!s || !s.devices_total) return 'Nothing is being monitored yet'
  return `${s.devices_total} miner${s.devices_total === 1 ? '' : 's'} · updated ${formatAgo(live.lastUpdate / 1000, now.value)}`
})
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div class="min-w-0">
        <h2 class="truncate text-2xl font-semibold tracking-tight text-fg">{{ session.meta?.instance_name ?? 'Dashboard' }}</h2>
        <p class="mt-1 text-sm text-muted" data-testid="dash-subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="session.canAdmin || session.canControl" class="flex items-center gap-2">
        <template v-if="!editing">
          <Button variant="ghost" size="sm" data-testid="customize" @click="startEdit">
            <template #icon><Pencil class="size-4" /></template>
            Customize
          </Button>
        </template>
        <template v-else>
          <Button variant="ghost" size="sm" @click="reset">
            <template #icon><RotateCcw class="size-4" /></template>
            Reset
          </Button>
          <Button variant="primary" size="sm" :loading="saving" data-testid="customize-done" @click="finish">
            <template #icon><Check class="size-4" /></template>
            Done
          </Button>
        </template>
      </div>
    </header>

    <p v-if="editing" class="rounded-xl border border-accent-line bg-accent-soft px-4 py-3 text-sm text-accent-text" role="status">
      Drag a card by its handle to move it, use the size button to resize it, or hide what you do not need. Press Done to save.
    </p>

    <ErrorState v-if="live.loadError && !live.loaded" :error="live.loadError" title="Could not load your dashboard" @retry="live.reload()" />

    <div v-else-if="!live.loaded" class="grid gap-[var(--gap-grid)] md:grid-cols-6 xl:grid-cols-12" aria-busy="true">
      <Skeleton class="h-72 rounded-2xl md:col-span-6 xl:col-span-8" />
      <Skeleton class="h-72 rounded-2xl md:col-span-3 xl:col-span-4" />
      <Skeleton class="h-48 rounded-2xl md:col-span-6 xl:col-span-12" />
    </div>

    <template v-else>
      <section
        v-if="noMiners && !editing"
        class="card relative overflow-hidden p-6 sm:p-8"
        aria-label="Welcome"
        data-testid="welcome"
      >
        <div class="pointer-events-none absolute -top-20 -right-10 size-80 rounded-full bg-accent/15 blur-3xl" aria-hidden="true" />
        <div class="relative max-w-2xl">
          <h3 class="text-gradient-accent text-3xl font-bold tracking-tight">Let’s find your miners</h3>
          <p class="mt-3 text-base leading-relaxed text-muted">
            Solo Miner Monitor shows every miner you own on one screen, tells you the real odds of finding a block, and warns you when something breaks.
            Start by scanning your network. It takes about twenty seconds and changes nothing on your miners.
          </p>
          <div class="mt-5 flex flex-wrap gap-3">
            <Button v-if="session.canControl" variant="primary" size="lg" data-testid="welcome-scan" @click="ui.addMinerOpen = true">
              <template #icon><Radar class="size-5" /></template>
              Scan my network
            </Button>
            <Button size="lg" variant="outline" to="/agents">Set up with an AI agent</Button>
          </div>
        </div>
      </section>

      <VueDraggable
        v-if="editing"
        v-model="draft"
        :animation="180"
        handle=".drag-handle"
        filter=".no-drag"
        :prevent-on-filter="false"
        :delay="140"
        :delay-on-touch-only="true"
        ghost-class="opacity-40"
        class="grid gap-[var(--gap-grid)] md:grid-cols-6 xl:grid-cols-12"
      >
        <div v-for="p in draft" :key="p.id" :class="['relative min-h-[84px] min-w-0', SPAN_CLASS[p.span]]">
          <component :is="WIDGET_BY_ID[p.id]!.component" class="pointer-events-none" />
          <div class="drag-handle absolute inset-0 z-10 flex cursor-grab items-start justify-between rounded-[var(--radius-card)] bg-bg/40 p-2.5 ring-2 ring-accent/50 backdrop-blur-[1px] active:cursor-grabbing">
            <span class="inline-flex items-center gap-1.5 rounded-lg bg-surface-3 px-2 py-1.5 text-xs font-medium text-fg shadow">
              <GripVertical class="size-4 text-muted" aria-hidden="true" /> {{ WIDGET_BY_ID[p.id]!.title }}
            </span>
            <span class="no-drag flex gap-1.5">
              <button
                v-if="WIDGET_BY_ID[p.id]!.spans.length > 1"
                class="inline-flex h-8 items-center gap-1.5 rounded-lg bg-surface-3 px-2.5 text-xs font-medium text-fg shadow hover:bg-surface-2"
                :aria-label="`Resize ${WIDGET_BY_ID[p.id]!.title}`"
                @click="resize(p)"
              >
                <Maximize2 class="size-3.5" aria-hidden="true" /> {{ SPAN_LABEL[p.span] }}
              </button>
              <button
                class="grid size-8 place-items-center rounded-lg bg-surface-3 text-fg shadow hover:bg-bad-soft hover:text-bad"
                :aria-label="`Hide ${WIDGET_BY_ID[p.id]!.title}`"
                @click="hide(p.id)"
              >
                <EyeOff class="size-4" />
              </button>
            </span>
          </div>
        </div>
      </VueDraggable>

      <div v-else class="grid gap-[var(--gap-grid)] md:grid-cols-6 xl:grid-cols-12" data-testid="dashboard-grid">
        <div v-for="p in visible" :key="p.id" :class="['min-w-0 empty:hidden', SPAN_CLASS[p.span]]">
          <component :is="WIDGET_BY_ID[p.id]!.component" />
        </div>
      </div>

      <section v-if="editing && tray.length" class="card p-[var(--pad-card)]" aria-label="Hidden widgets">
        <h3 class="text-sm font-semibold text-fg">Add a widget</h3>
        <ul class="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <li v-for="w in tray" :key="w.id">
            <button class="flex w-full items-start gap-3 rounded-xl border border-line bg-surface-2/60 p-3 text-left transition-colors hover:border-accent-line hover:bg-accent-softer" @click="add(w.id)">
              <span class="grid size-9 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent-text"><component :is="w.icon" class="size-4.5" aria-hidden="true" /></span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-medium text-fg">{{ w.title }}</span>
                <span class="mt-0.5 block text-xs leading-relaxed text-subtle">{{ w.description }}</span>
              </span>
              <Plus class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />
            </button>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
