<script setup lang="ts">
import { BellRing, CircleCheck, CircleX, Pencil, Plus, Send, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Switch from '@/components/ui/Switch.vue'
import ToggleRow from '@/components/ui/ToggleRow.vue'
import { confirmDialog } from '@/composables/useConfirm'
import { api, describeError } from '@/lib/api'
import type { Channel, ChannelField, ChannelType, SendResult, Severity } from '@/lib/types'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const session = useSession()
const settings = useSettings()
const toasts = useToasts()
const admin = computed(() => session.canAdmin)

const types = ref<ChannelType[]>([])
const channels = ref<Channel[]>([])
const loading = ref(true)
const testingId = ref<string | null>(null)

async function load(): Promise<void> {
  try {
    ;[types.value, channels.value] = await Promise.all([api.channelTypes(), api.channels()])
  } finally {
    loading.value = false
  }
}
onMounted(() => void load())

const typeOf = (kind: string): ChannelType | undefined => types.value.find((t) => t.kind === kind)

// ---- dialog
const open = ref(false)
const editing = ref<Channel | null>(null)
const form = reactive<{ kind: string; name: string; min_severity: Severity; values: Record<string, string | number | boolean> }>({ kind: '', name: '', min_severity: 'info', values: {} })
const result = ref<SendResult | null>(null)
const testing = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const spec = computed(() => typeOf(form.kind) ?? null)
const savedDraft = ref('')
const needsSave = computed(() => !!editing.value && JSON.stringify(form) !== savedDraft.value)
watch(form, () => { result.value = null }, { deep: true, flush: 'sync' })

function seedValues(t: ChannelType | undefined, existing?: Record<string, unknown>): void {
  form.values = {}
  for (const f of t?.fields ?? []) {
    const v = existing?.[f.name] ?? (f.secret ? '' : f.default ?? (f.kind === 'boolean' ? false : ''))
    form.values[f.name] = v as string | number | boolean
  }
}
function openAdd(): void {
  editing.value = null
  const first = types.value[0]
  Object.assign(form, { kind: first?.kind ?? '', name: '', min_severity: 'info' })
  seedValues(first)
  result.value = null
  error.value = null
  open.value = true
}
function openEdit(c: Channel): void {
  editing.value = c
  Object.assign(form, { kind: c.kind, name: c.name, min_severity: c.min_severity })
  seedValues(typeOf(c.kind), c.config)
  savedDraft.value = JSON.stringify(form)
  result.value = null
  error.value = null
  open.value = true
}
function onKind(v: string | number | null | undefined): void {
  form.kind = String(v)
  seedValues(typeOf(form.kind))
  if (!form.name) result.value = null
}

function payload() {
  const config: Record<string, unknown> = {}
  const secret: Record<string, string> = {}
  for (const f of spec.value?.fields ?? []) {
    const v = form.values[f.name]
    if (f.secret) {
      if (v !== '' && v !== undefined) secret[f.name] = String(v)
    } else if (v !== '' && v !== undefined) config[f.name] = f.kind === 'number' ? Number(v) : v
  }
  return { kind: form.kind, name: form.name.trim() || spec.value?.label || form.kind, config, secret, min_severity: form.min_severity }
}
function missing(): string | null {
  for (const f of spec.value?.fields ?? []) {
    const blankSecretWhileEditing = f.secret && editing.value
    if (f.required && !blankSecretWhileEditing && (form.values[f.name] === '' || form.values[f.name] === undefined)) return `${f.label} is needed.`
  }
  return null
}

async function runTest(): Promise<void> {
  if (testing.value || saving.value) return
  if (needsSave.value) {
    error.value = 'Save your changes before sending a test.'
    return
  }
  error.value = missing()
  if (error.value) return
  testing.value = true
  try {
    const testedDraft = JSON.stringify(form)
    const response = editing.value ? await api.testChannel(editing.value.id) : await api.testChannelInline(payload())
    if (testedDraft === JSON.stringify(form)) result.value = response
  } catch (e) {
    result.value = { ok: false, error: describeError(e) }
  } finally {
    testing.value = false
  }
}

async function save(): Promise<void> {
  error.value = missing()
  if (error.value) return
  saving.value = true
  try {
    const p = payload()
    if (editing.value) await api.updateChannel(editing.value.id, { name: p.name, config: p.config, min_severity: p.min_severity, ...(Object.keys(p.secret).length ? { secret: p.secret } : {}) })
    else await api.createChannel(p)
    toasts.success(editing.value ? 'Saved' : 'Channel added', 'Use “Send test” to make sure it arrives.')
    open.value = false
    await load()
  } catch (e) {
    error.value = describeError(e)
  } finally {
    saving.value = false
  }
}

async function sendTest(c: Channel): Promise<void> {
  testingId.value = c.id
  try {
    const r = await api.testChannel(c.id)
    if (r.ok) toasts.success(`Test sent to ${c.name}`, 'Check your phone or inbox.')
    else toasts.error(`${c.name} did not accept it`, r.error ?? undefined)
  } catch (e) {
    toasts.error('Could not send the test', describeError(e))
  } finally {
    testingId.value = null
  }
}
async function toggle(c: Channel, on: boolean): Promise<void> {
  const before = c.enabled
  c.enabled = on
  try {
    await api.updateChannel(c.id, { enabled: on })
  } catch (e) {
    c.enabled = before
    toasts.error('Could not change that', describeError(e))
  }
}
async function remove(c: Channel): Promise<void> {
  if (!(await confirmDialog({ title: `Remove ${c.name}?`, message: 'Alerts stop going there.', confirmLabel: 'Remove', tone: 'danger' }))) return
  try {
    await api.deleteChannel(c.id)
    await load()
  } catch (e) {
    toasts.error('Could not remove it', describeError(e))
  }
}

const fieldType = (f: ChannelField): string => (f.kind === 'password' || f.secret ? 'password' : f.kind === 'number' ? 'number' : f.kind === 'email' ? 'email' : 'text')

// ---- quiet hours
const quiet = computed(() => settings.data?.alerts.quiet_hours ?? null)
async function setQuiet(on: boolean): Promise<void> {
  try {
    await settings.patch({ alerts: { quiet_hours: on ? { start: '23:00', end: '07:00' } : null } })
  } catch (e) {
    toasts.error('Could not change that', describeError(e))
  }
}
async function setQuietTime(which: 'start' | 'end', v: string | number | null): Promise<void> {
  if (!quiet.value || typeof v !== 'string' || !/^\d\d:\d\d$/.test(v)) return
  try {
    await settings.patch({ alerts: { quiet_hours: { ...quiet.value, [which]: v } } })
  } catch (e) {
    toasts.error('Could not change that', describeError(e))
  }
}
</script>

<template>
  <SettingsCard title="Where alerts go" description="The dashboard always shows problems. A channel sends them to your phone or inbox so you hear about a hot miner or a found block while you are away.">
    <div class="mb-4 flex justify-end"><Button v-if="admin" variant="primary" size="sm" data-testid="add-channel" @click="openAdd"><template #icon><Plus class="size-4" /></template>Add a channel</Button></div>
    <div v-if="loading" class="space-y-2"><Skeleton v-for="i in 2" :key="i" class="h-16 rounded-xl" /></div>
    <ul v-else-if="channels.length" class="space-y-3" data-testid="channel-list">
      <li v-for="c in channels" :key="c.id" class="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface-2/50 p-4">
        <BellRing class="size-5 shrink-0 text-muted" aria-hidden="true" />
        <div class="min-w-0 flex-1 basis-48">
          <p class="flex flex-wrap items-center gap-2 text-sm font-medium text-fg">{{ c.name }}<Badge size="sm">{{ typeOf(c.kind)?.label ?? c.kind }}</Badge><Badge v-if="!c.enabled" size="sm" tone="warn">Off</Badge></p>
          <p class="mt-0.5 text-xs text-subtle">Sends {{ c.min_severity === 'info' ? 'everything' : c.min_severity === 'warning' ? 'warnings and worse' : 'only critical alerts' }}</p>
        </div>
        <Button v-if="session.canControl" size="sm" variant="secondary" :loading="testingId === c.id" @click="sendTest(c)"><template #icon><Send class="size-3.5" /></template>Send test</Button>
        <template v-if="admin">
          <Switch :model-value="c.enabled" :label="`${c.name} enabled`" @update:model-value="(v) => toggle(c, v)" />
          <Button size="iconSm" variant="ghost" :aria-label="`Edit ${c.name}`" @click="openEdit(c)"><Pencil class="size-4" /></Button>
          <Button size="iconSm" variant="ghost" :aria-label="`Remove ${c.name}`" @click="remove(c)"><Trash2 class="size-4" /></Button>
        </template>
      </li>
    </ul>
    <EmptyState v-else compact :icon="BellRing" title="No channels yet" description="ntfy is the quickest: install the app, pick a topic name and you are done in a minute. Telegram, Discord, Slack, email and more also work.">
      <Button v-if="admin" variant="soft" @click="openAdd">Add your first channel</Button>
    </EmptyState>
  </SettingsCard>

  <SettingsCard title="Quiet hours" description="Hold back routine notifications overnight. Critical alerts and found blocks always come through.">
    <ToggleRow :model-value="!!quiet" :disabled="!admin" title="Pause routine notifications at night" @update:model-value="setQuiet" />
    <div v-if="quiet" class="mt-2 grid max-w-sm grid-cols-2 gap-4">
      <Field label="From"><template #default="{ id }"><Input :id="id" :model-value="quiet.start" type="time" :disabled="!admin" @update:model-value="(v) => setQuietTime('start', v)" /></template></Field>
      <Field label="Until"><template #default="{ id }"><Input :id="id" :model-value="quiet.end" type="time" :disabled="!admin" @update:model-value="(v) => setQuietTime('end', v)" /></template></Field>
    </div>
  </SettingsCard>

  <Dialog v-model:open="open" :title="editing ? `Edit ${editing.name}` : 'Add a channel'" size="lg">
    <form class="space-y-5" @submit.prevent="save">
      <Field v-if="!editing" label="Where should alerts go?">
        <template #default="{ id }"><Select :id="id" :model-value="form.kind" :options="types.map((t) => ({ value: t.kind, label: t.label }))" data-testid="channel-kind" @update:model-value="onKind" /></template>
      </Field>
      <p v-if="spec?.help" class="rounded-xl border border-line bg-surface-2/60 p-4 text-sm leading-relaxed text-muted">{{ spec.help }}</p>
      <div class="grid gap-4 sm:grid-cols-2">
        <Field label="Name" hint="So you can tell channels apart." class="sm:col-span-2"><template #default="{ id }"><Input :id="id" v-model="form.name" :placeholder="spec?.label" /></template></Field>
        <Field v-for="f in spec?.fields ?? []" :key="f.name" :label="f.label" :required="f.required && !(f.secret && editing)" :hint="f.secret && editing ? 'Saved. Leave empty to keep it.' : f.help || undefined">
          <template #default="{ id, describedBy }">
            <Select v-if="f.kind === 'select'" :id="id" :model-value="String(form.values[f.name] ?? '')" :options="f.options.map((o) => ({ value: o, label: o }))" @update:model-value="(v) => (form.values[f.name] = v ?? '')" />
            <Switch v-else-if="f.kind === 'boolean'" :id="id" :model-value="!!form.values[f.name]" :label="f.label" @update:model-value="(v) => (form.values[f.name] = v)" />
            <Input v-else :id="id" :model-value="String(form.values[f.name] ?? '')" :type="fieldType(f)" :placeholder="f.secret && editing ? '••••••••' : f.placeholder" :described-by="describedBy" autocomplete="off" mono @update:model-value="(v) => (form.values[f.name] = v ?? '')" />
          </template>
        </Field>
        <Field label="Send which alerts?" class="sm:col-span-2">
          <template #default="{ id }">
            <Select :id="id" v-model="form.min_severity" :options="[{ value: 'info', label: 'Everything (including good news)' }, { value: 'warning', label: 'Warnings and critical only' }, { value: 'critical', label: 'Only critical alerts' }]" />
          </template>
        </Field>
      </div>
      <div v-if="result" :class="['flex items-start gap-2.5 rounded-xl border p-4 text-sm', result.ok ? 'border-ok/30 bg-ok-soft text-ok' : 'border-bad/30 bg-bad-soft text-bad']" role="status" data-testid="channel-test-result">
        <CircleCheck v-if="result.ok" class="mt-0.5 size-4 shrink-0" /><CircleX v-else class="mt-0.5 size-4 shrink-0" />
        <span class="text-fg">{{ result.ok ? 'Delivered. Check that it arrived.' : (result.error ?? 'It did not go through.') }}</span>
      </div>
      <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
      <p v-if="needsSave" class="text-sm text-muted" role="status">Save your changes before sending a test.</p>
    </form>
    <template #footer>
      <Button variant="ghost" @click="open = false">Cancel</Button>
      <Button variant="secondary" :loading="testing" :disabled="needsSave || saving" @click="runTest"><template #icon><Send class="size-4" /></template>Send a test</Button>
      <Button variant="primary" :loading="saving" data-testid="channel-save" @click="save">{{ editing ? 'Save' : 'Add channel' }}</Button>
    </template>
  </Dialog>
</template>
