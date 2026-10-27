<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { api, describeError } from '@/lib/api'
import type { AlertRule, Channel, RuleType, Severity } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Segmented from '@/components/ui/Segmented.vue'
import Select from '@/components/ui/Select.vue'
import TagInput from '@/components/ui/TagInput.vue'

const props = defineProps<{ rule: AlertRule | null; types: RuleType[]; channels: Channel[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [] }>()

const live = useLive()
const toasts = useToasts()

const kind = ref('')
const name = ref('')
const severity = ref<Severity>('warning')
const scopeMode = ref<'all' | 'tags' | 'miners'>('all')
const tags = ref<string[]>([])
const deviceIds = ref<string[]>([])
const params = reactive<Record<string, number | null>>({})
const cooldownMin = ref<number | null>(null)
const channelIds = ref<string[]>([])
const busy = ref(false)
const error = ref<string | null>(null)

const spec = computed(() => props.types.find((t) => t.kind === kind.value) ?? null)
const editing = computed(() => !!props.rule)
const allTags = computed(() => [...new Set(live.devices.flatMap((d) => d.tags))])
const fleetRule = computed(() => spec.value?.scope === 'fleet')

function seed(): void {
  error.value = null
  const r = props.rule
  const t = (r ? props.types.find((x) => x.kind === r.kind) : props.types[0]) ?? null
  kind.value = r?.kind ?? t?.kind ?? ''
  name.value = r?.name ?? ''
  severity.value = r?.severity ?? t?.severity ?? 'warning'
  scopeMode.value = r?.scope.device_ids?.length ? 'miners' : r?.scope.tags?.length ? 'tags' : 'all'
  tags.value = [...(r?.scope.tags ?? [])]
  deviceIds.value = [...(r?.scope.device_ids ?? [])]
  for (const k of Object.keys(params)) delete params[k]
  for (const p of t?.params ?? []) params[p.name] = (r?.params[p.name] as number | undefined) ?? p.default
  cooldownMin.value = r ? Math.round(r.cooldown_s / 60) : t ? Math.round(t.cooldown_s / 60) : null
  channelIds.value = [...(r?.channel_ids ?? [])]
}
watch(open, (v) => v && seed(), { immediate: true })

// picking a different kind while creating re-seeds the defaults for that kind
watch(kind, (k) => {
  if (editing.value) return
  const t = props.types.find((x) => x.kind === k)
  if (!t) return
  severity.value = t.severity
  for (const key of Object.keys(params)) delete params[key]
  for (const p of t.params) params[p.name] = p.default
  cooldownMin.value = Math.round(t.cooldown_s / 60)
})

function toggle<T>(list: T[], v: T): T[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v]
}

async function save(): Promise<void> {
  error.value = null
  const s = spec.value
  if (!s) return
  const body = {
    kind: s.kind,
    name: name.value.trim() || s.label,
    severity: severity.value,
    scope: fleetRule.value || scopeMode.value === 'all' ? { all: true } : scopeMode.value === 'tags' ? { tags: tags.value } : { device_ids: deviceIds.value },
    params: Object.fromEntries(Object.entries(params).filter(([, v]) => v !== null)),
    channel_ids: channelIds.value,
    cooldown_s: cooldownMin.value != null ? cooldownMin.value * 60 : undefined,
  }
  if (!fleetRule.value && scopeMode.value === 'tags' && !tags.value.length) return void (error.value = 'Add at least one tag, or choose “All miners”.')
  if (!fleetRule.value && scopeMode.value === 'miners' && !deviceIds.value.length) return void (error.value = 'Pick at least one miner, or choose “All miners”.')
  busy.value = true
  try {
    if (props.rule) await api.updateRule(props.rule.id, body)
    else await api.createRule(body)
    toasts.success(props.rule ? 'Rule saved' : 'Rule added')
    emit('saved')
    open.value = false
  } catch (e) {
    error.value = describeError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open" :title="editing ? 'Edit alert rule' : 'New alert rule'" description="Decide what is worth a notification and who hears about it." size="lg">
    <form class="space-y-5" @submit.prevent="save">
      <Field v-if="!editing" label="When should this fire?">
        <template #default="{ id }"><Select :id="id" v-model="kind" :options="types.map((t) => ({ value: t.kind, label: t.label }))" /></template>
      </Field>
      <p v-if="spec" class="-mt-2 text-sm text-muted">{{ spec.description }}</p>

      <div class="grid gap-4 sm:grid-cols-2">
        <Field label="Name" hint="Shown in notifications.">
          <template #default="{ id, describedBy }"><Input :id="id" v-model="name" :described-by="describedBy" :placeholder="spec?.label" /></template>
        </Field>
        <Field label="How serious?">
          <template #default="{ id }">
            <Select :id="id" v-model="severity" :options="[{ value: 'info', label: 'Information' }, { value: 'warning', label: 'Warning' }, { value: 'critical', label: 'Critical' }]" />
          </template>
        </Field>
      </div>

      <div v-if="spec?.params.length" class="space-y-3 rounded-xl border border-line bg-surface-2/50 p-4">
        <div class="grid gap-4 sm:grid-cols-2">
          <Field v-for="p in spec.params" :key="p.name" :label="p.label" :hint="p.help || undefined">
            <template #default="{ id, describedBy }">
              <Input :id="id" v-model="params[p.name]" type="number" :min="p.min ?? undefined" :max="p.max ?? undefined" :suffix="p.unit" :described-by="describedBy" />
            </template>
          </Field>
        </div>
      </div>

      <div v-if="!fleetRule" class="space-y-3">
        <p class="text-[13px] font-medium text-fg">Which miners?</p>
        <Segmented v-model="scopeMode" label="Which miners" size="sm" :options="[{ value: 'all', label: 'All miners' }, { value: 'tags', label: 'By tag' }, { value: 'miners', label: 'Specific miners' }]" />
        <TagInput v-if="scopeMode === 'tags'" v-model="tags" :suggestions="allTags" placeholder="Add a tag" />
        <div v-if="scopeMode === 'miners'" class="flex flex-wrap gap-1.5">
          <button
            v-for="d in live.devices"
            :key="d.id"
            type="button"
            :class="['rounded-full border px-3 py-1 text-xs font-medium', deviceIds.includes(d.id) ? 'border-accent-line bg-accent-soft text-accent-text' : 'border-line text-muted hover:text-fg']"
            :aria-pressed="deviceIds.includes(d.id)"
            @click="deviceIds = toggle(deviceIds, d.id)"
          >{{ d.name }}</button>
        </div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <Field label="Repeat at most every" hint="Stops the same problem from pinging you over and over.">
          <template #default="{ id, describedBy }"><Input :id="id" v-model="cooldownMin" type="number" :min="0" suffix="min" :described-by="describedBy" /></template>
        </Field>
        <div>
          <p class="mb-1.5 text-[13px] font-medium text-fg">Send to</p>
          <div v-if="channels.length" class="flex flex-wrap gap-1.5">
            <button
              v-for="c in channels"
              :key="c.id"
              type="button"
              :class="['rounded-full border px-3 py-1 text-xs font-medium', channelIds.includes(c.id) ? 'border-accent-line bg-accent-soft text-accent-text' : 'border-line text-muted hover:text-fg']"
              :aria-pressed="channelIds.includes(c.id)"
              @click="channelIds = toggle(channelIds, c.id)"
            >{{ c.name }}</button>
          </div>
          <p class="mt-1.5 text-xs text-subtle">{{ channels.length ? (channelIds.length ? '' : 'Nothing picked means every channel.') : 'No channels yet. Add one under Settings → Notifications.' }}</p>
        </div>
      </div>
      <p v-if="error" class="rounded-xl border border-bad/30 bg-bad-soft px-3 py-2.5 text-sm text-bad" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <Button variant="ghost" @click="open = false">Cancel</Button>
      <Button variant="primary" :loading="busy" data-testid="rule-save" @click="save">{{ editing ? 'Save rule' : 'Add rule' }}</Button>
    </template>
  </Dialog>
</template>
