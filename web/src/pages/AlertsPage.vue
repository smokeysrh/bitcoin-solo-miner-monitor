<script setup lang="ts">
import { BellRing, Check, CheckCheck, CircleCheck, History, OctagonAlert, Pencil, Plus, Trash2, TriangleAlert } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import RuleDialog from '@/components/alerts/RuleDialog.vue'
import Badge, { type Tone } from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EventIcon from '@/components/ui/EventIcon.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import Select from '@/components/ui/Select.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Switch from '@/components/ui/Switch.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { confirmDialog } from '@/composables/useConfirm'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { api, describeError } from '@/lib/api'
import { eventLabel, scopeLabel } from '@/lib/labels'
import type { AlertRule, AppEvent, Channel, RuleType } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useToasts } from '@/stores/toasts'

const live = useLive()
const fmt = useFmt()
const now = useNowSec()
const session = useSession()
const toasts = useToasts()
const route = useRoute()
const router = useRouter()

const tab = computed({
  get: () => (route.query.tab === 'rules' ? 'rules' : 'activity'),
  set: (v: string) => void router.replace({ query: { tab: v === 'activity' ? undefined : v } }),
})

// ---- activity
const events = ref<AppEvent[]>([])
const next = ref<number | null>(null)
const loadingEvents = ref(true)
const eventsError = ref<unknown>(null)
const severity = ref<'all' | 'warning' | 'success'>('all')
const deviceFilter = ref('')
const more = ref(false)

async function loadEvents(append = false): Promise<void> {
  if (!append) loadingEvents.value = true
  more.value = append
  try {
    const r = await api.events({
      limit: 40,
      before_id: append ? next.value : undefined,
      min_severity: severity.value === 'warning' ? 'warning' : undefined,
      device_id: deviceFilter.value || undefined,
    })
    let list = r.events
    if (severity.value === 'success') list = list.filter((e) => e.severity === 'success')
    events.value = append ? [...events.value, ...list] : list
    next.value = r.next_before_id
    eventsError.value = null
  } catch (e) {
    eventsError.value = e
  } finally {
    loadingEvents.value = false
    more.value = false
  }
}
onMounted(() => void loadEvents())
watch([severity, deviceFilter], () => void loadEvents())
watch(() => live.events[0]?.id, () => void loadEvents())

async function ack(e: AppEvent): Promise<void> {
  if (e.id == null) return
  try {
    await api.ackEvent(e.id)
    e.ack_ts = Date.now() / 1000
  } catch (err) {
    toasts.error('Could not mark it seen', describeError(err))
  }
}
async function ackAll(): Promise<void> {
  try {
    const r = await api.ackAllEvents()
    toasts.success(`Marked ${r.acknowledged} as seen`)
    await loadEvents()
  } catch (err) {
    toasts.error('Could not do that', describeError(err))
  }
}
const unseen = computed(() => events.value.filter((e) => e.ack_ts === null && e.severity !== 'info').length)

// ---- rules
const rules = ref<AlertRule[]>([])
const types = ref<RuleType[]>([])
const channels = ref<Channel[]>([])
const loadingRules = ref(true)
const rulesError = ref<unknown>(null)
const editing = ref<AlertRule | null>(null)
const dialog = ref(false)

async function loadRules(): Promise<void> {
  try {
    ;[rules.value, types.value, channels.value] = await Promise.all([api.rules(), api.ruleTypes(), api.channels()])
    rulesError.value = null
  } catch (e) {
    rulesError.value = e
  } finally {
    loadingRules.value = false
  }
}
onMounted(() => void loadRules())

const typeOf = (k: string): RuleType | undefined => types.value.find((t) => t.kind === k)
const sevTone: Record<string, Tone> = { info: 'info', warning: 'warn', critical: 'bad', success: 'ok' }

async function toggleRule(r: AlertRule, on: boolean): Promise<void> {
  const before = r.enabled
  r.enabled = on
  try {
    await api.updateRule(r.id, { enabled: on })
  } catch (e) {
    r.enabled = before
    toasts.error('Could not change that rule', describeError(e))
  }
}
async function removeRule(r: AlertRule): Promise<void> {
  if (!(await confirmDialog({ title: `Delete “${r.name}”?`, message: 'It stops alerting immediately.', confirmLabel: 'Delete rule', tone: 'danger' }))) return
  try {
    await api.deleteRule(r.id)
    await loadRules()
  } catch (e) {
    toasts.error('Could not delete it', describeError(e))
  }
}
function edit(r: AlertRule | null): void {
  editing.value = r
  dialog.value = true
}
const channelNames = (r: AlertRule): string => (r.channel_ids.length ? r.channel_ids.map((id) => channels.value.find((c) => c.id === id)?.name ?? '?').join(', ') : channels.value.length ? 'every channel' : 'no channels yet')
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 class="text-2xl font-semibold tracking-tight text-fg">Alerts &amp; activity</h2>
        <p class="mt-1 text-sm text-muted">What is wrong now, what happened, and the rules that decide what pings you.</p>
      </div>
      <Button v-if="tab === 'activity' && unseen && session.canControl" variant="secondary" size="sm" @click="ackAll"><template #icon><CheckCheck class="size-4" /></template>Mark all seen</Button>
      <Button v-if="tab === 'rules' && session.canAdmin" variant="primary" size="sm" data-testid="add-rule" @click="edit(null)"><template #icon><Plus class="size-4" /></template>Add rule</Button>
    </header>

    <Tabs v-model="tab" label="Alerts sections" :tabs="[{ value: 'activity', label: 'Activity', icon: History, badge: live.alerts.length || null }, { value: 'rules', label: 'Rules', icon: BellRing }]">
      <template #activity>
        <div class="space-y-5">
          <section v-if="live.alerts.length" aria-label="Active alerts" class="space-y-2.5" data-testid="active-alerts">
            <h3 class="eyebrow">Happening now</h3>
            <div v-for="a in live.alerts" :key="a.key" class="flex items-start gap-3 rounded-2xl border p-4" :class="a.severity === 'critical' ? 'border-bad/30 bg-bad-soft' : 'border-warn/30 bg-warn-soft'">
              <OctagonAlert v-if="a.severity === 'critical'" class="mt-0.5 size-5 shrink-0 text-bad" aria-hidden="true" />
              <TriangleAlert v-else class="mt-0.5 size-5 shrink-0 text-warn" aria-hidden="true" />
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium text-fg"><RouterLink v-if="a.device_id" :to="`/miners/${a.device_id}`" class="hover:underline">{{ a.title }}</RouterLink><template v-else>{{ a.title }}</template></p>
                <p v-if="a.body" class="mt-0.5 text-sm text-muted">{{ a.body }}</p>
              </div>
              <span class="shrink-0 text-xs text-muted">since {{ fmt.formatAgo(a.since, now) }}</span>
            </div>
          </section>
          <div v-else class="flex items-center gap-3 rounded-2xl border border-ok/25 bg-ok-soft p-4">
            <CircleCheck class="size-5 shrink-0 text-ok" aria-hidden="true" />
            <p class="text-sm text-fg">All clear. Nothing needs your attention.</p>
          </div>

          <MetricCard title="Activity log" :icon="History">
            <template #actions>
              <div class="flex gap-2">
                <Select v-model="severity" size="sm" class="w-36" aria-label="Show" :options="[{ value: 'all', label: 'Everything' }, { value: 'warning', label: 'Problems only' }, { value: 'success', label: 'Good news' }]" />
                <Select v-model="deviceFilter" size="sm" class="w-40" aria-label="Miner" :options="[{ value: '', label: 'All miners' }, ...live.devices.map((d) => ({ value: d.id, label: d.name }))]" />
              </div>
            </template>
            <div v-if="loadingEvents" class="space-y-2"><Skeleton v-for="i in 5" :key="i" class="h-12 rounded-xl" /></div>
            <ErrorState v-else-if="eventsError" compact :error="eventsError" @retry="loadEvents()" />
            <EmptyState v-else-if="!events.length" compact :icon="History" title="Nothing here yet" description="Restarts, outages, best shares and difficulty changes will be listed as they happen." />
            <ul v-else class="-my-1 divide-y divide-line" data-testid="event-list">
              <li v-for="e in events" :key="e.id ?? e.ts" class="flex items-start gap-3 py-3.5">
                <EventIcon :type="e.type" :severity="e.severity" />
                <div class="min-w-0 flex-1">
                  <p class="flex flex-wrap items-center gap-2 text-sm text-fg">
                    <RouterLink v-if="e.device_id" :to="`/miners/${e.device_id}`" class="hover:underline">{{ e.title }}</RouterLink><template v-else>{{ e.title }}</template>
                    <Badge size="sm" :tone="sevTone[e.severity] ?? 'neutral'">{{ eventLabel(e) }}</Badge>
                    <span v-if="e.ack_ts === null && e.severity !== 'info'" class="size-2 rounded-full bg-accent" title="Not marked seen" />
                  </p>
                  <p v-if="e.body" class="mt-0.5 text-xs leading-relaxed text-subtle">{{ e.body }}</p>
                </div>
                <time class="shrink-0 pt-0.5 text-xs text-subtle" :title="fmt.formatDateTime(e.ts)">{{ fmt.formatAgo(e.ts, now) }}</time>
                <Button v-if="e.ack_ts === null && e.severity !== 'info' && session.canControl" size="iconSm" variant="ghost" aria-label="Mark seen" @click="ack(e)"><Check class="size-4" /></Button>
              </li>
            </ul>
            <div v-if="next" class="mt-4 text-center"><Button variant="secondary" size="sm" :loading="more" @click="loadEvents(true)">Load older</Button></div>
          </MetricCard>
        </div>
      </template>

      <template #rules>
        <div v-if="loadingRules" class="space-y-2"><Skeleton v-for="i in 5" :key="i" class="h-16 rounded-2xl" /></div>
        <ErrorState v-else-if="rulesError" :error="rulesError" @retry="loadRules" />
        <div v-else class="space-y-3" data-testid="rule-list">
          <p class="max-w-3xl text-sm text-muted">Rules watch your miners and node and send a notification when something matches. Where it goes is decided by your <RouterLink to="/settings/notifications" class="text-accent-text underline underline-offset-2 hover:no-underline">notification channels</RouterLink>.</p>
          <div v-for="r in rules" :key="r.id" class="card flex flex-wrap items-center gap-x-4 gap-y-3 p-4">
            <div class="min-w-0 flex-1 basis-64">
              <p class="flex flex-wrap items-center gap-2 text-sm font-medium text-fg">{{ r.name }} <Badge size="sm" :tone="sevTone[r.severity] ?? 'neutral'">{{ r.severity }}</Badge><Badge v-if="r.builtin" size="sm">built in</Badge><Badge v-if="!r.enabled" size="sm" tone="warn">Off</Badge></p>
              <p class="mt-1 text-xs text-muted">{{ typeOf(r.kind)?.description }}</p>
              <p class="mt-1 text-xs text-subtle">{{ scopeLabel(r.scope, live.deviceName) }} → {{ channelNames(r) }}</p>
            </div>
            <Switch :model-value="r.enabled" :label="`${r.name} enabled`" :disabled="!session.canAdmin" @update:model-value="(v) => toggleRule(r, v)" />
            <div v-if="session.canAdmin" class="flex gap-1">
              <Button size="iconSm" variant="ghost" :aria-label="`Edit ${r.name}`" @click="edit(r)"><Pencil class="size-4" /></Button>
              <Button v-if="!r.builtin" size="iconSm" variant="ghost" :aria-label="`Delete ${r.name}`" @click="removeRule(r)"><Trash2 class="size-4" /></Button>
            </div>
          </div>
        </div>
      </template>
    </Tabs>

    <RuleDialog v-model:open="dialog" :rule="editing" :types="types" :channels="channels" @saved="loadRules" />
  </div>
</template>
