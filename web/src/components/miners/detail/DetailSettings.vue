<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMinerActions } from '@/composables/useMinerActions'
import { api, describeError, type UpdateDeviceBody } from '@/lib/api'
import type { DeviceView } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useToasts } from '@/stores/toasts'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import TagInput from '@/components/ui/TagInput.vue'
import Textarea from '@/components/ui/Textarea.vue'
import ToggleRow from '@/components/ui/ToggleRow.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

const props = defineProps<{ device: DeviceView }>()
const live = useLive()
const toasts = useToasts()
const session = useSession()
const router = useRouter()
const actions = useMinerActions()

interface Form {
  name: string
  tags: string[]
  group: string
  notes: string
  model_override: string
  poll_interval_s: number | null
  allow_control: boolean
  enabled: boolean
  host: string
  port: number | null
  power_override_w: number | null
}

function fromDevice(d: DeviceView): Form {
  const po = d.extra?.power_override_w
  return {
    name: d.name,
    tags: [...d.tags],
    group: d.group ?? '',
    notes: d.notes ?? '',
    model_override: d.model_override ?? '',
    poll_interval_s: d.poll_interval_s,
    allow_control: d.allow_control,
    enabled: d.enabled,
    host: d.host,
    port: d.port,
    power_override_w: typeof po === 'number' ? po : null,
  }
}

const form = reactive<Form>(fromDevice(props.device))
const busy = ref(false)
const error = ref<string | null>(null)
// re-seed when switching miner, but never clobber what the user is typing on a live update
watch(() => props.device.id, () => Object.assign(form, fromDevice(props.device)))

const baseline = computed(() => fromDevice(props.device))
const dirty = computed(() => JSON.stringify(form) !== JSON.stringify(baseline.value))
const allTags = computed(() => [...new Set(live.devices.flatMap((d) => d.tags))])
const editable = computed(() => session.canControl)

async function save(): Promise<void> {
  error.value = null
  const b = baseline.value
  const body: UpdateDeviceBody = {}
  if (form.name.trim() !== b.name) body.name = form.name.trim()
  if (JSON.stringify(form.tags) !== JSON.stringify(b.tags)) body.tags = form.tags
  if (form.group.trim() !== b.group) body.group = form.group.trim() || null
  if (form.notes !== b.notes) body.notes = form.notes || null
  if (form.model_override.trim() !== b.model_override) body.model_override = form.model_override.trim() || null
  if (form.poll_interval_s !== b.poll_interval_s) body.poll_interval_s = form.poll_interval_s
  if (form.allow_control !== b.allow_control) body.allow_control = form.allow_control
  if (form.enabled !== b.enabled) body.enabled = form.enabled
  if (form.host.trim() !== b.host) body.host = form.host.trim()
  if (form.port !== b.port && form.port) body.port = form.port
  if (form.power_override_w !== b.power_override_w) body.power_override_w = form.power_override_w
  if (!Object.keys(body).length) return
  busy.value = true
  try {
    live.upsertDevice(await api.updateDevice(props.device.id, body))
    toasts.success('Saved')
    Object.assign(form, fromDevice(live.byId(props.device.id) ?? props.device))
  } catch (e) {
    error.value = describeError(e)
  } finally {
    busy.value = false
  }
}

async function remove(): Promise<void> {
  if (await actions.remove(props.device)) await router.replace('/miners')
}
</script>

<template>
  <div class="grid gap-[var(--gap-grid)] xl:grid-cols-[minmax(0,1fr)_22rem]">
    <MetricCard title="About this miner">
      <form class="space-y-5" @submit.prevent="save">
        <div class="grid gap-4 sm:grid-cols-2">
          <Field label="Name" hint="Shown everywhere in the app.">
            <template #default="{ id, describedBy }"><Input :id="id" v-model="form.name" :described-by="describedBy" :disabled="!editable" data-testid="device-name" /></template>
          </Field>
          <Field label="Group" hint="For example “garage” or “rack 1”. Used to group the miners page.">
            <template #default="{ id, describedBy }"><Input :id="id" v-model="form.group" :described-by="describedBy" :disabled="!editable" /></template>
          </Field>
        </div>
        <Field label="Tags" hint="Alert rules and bulk actions can target tags.">
          <template #default="{ id }"><TagInput :id="id" v-model="form.tags" :suggestions="allTags" /></template>
        </Field>
        <Field label="Notes" hint="Anything you want to remember: firmware quirks, where it sits, the PSU it uses.">
          <template #default="{ id, describedBy }"><Textarea :id="id" v-model="form.notes" :described-by="describedBy" :rows="3" :disabled="!editable" :maxlength="2000" /></template>
        </Field>

        <div class="border-t border-line pt-5">
          <h3 class="mb-1 text-sm font-semibold text-fg">Connection</h3>
          <div class="grid gap-4 sm:grid-cols-[1fr_7rem]">
            <Field label="Address" hint="Change this if the miner got a new IP address.">
              <template #default="{ id, describedBy }"><Input :id="id" v-model="form.host" mono :described-by="describedBy" :disabled="!editable" /></template>
            </Field>
            <Field label="Port">
              <template #default="{ id }"><Input :id="id" v-model="form.port" type="number" :min="1" :max="65535" mono :disabled="!editable" /></template>
            </Field>
          </div>
          <p v-if="device.alt_hosts.length" class="mt-2 text-xs text-subtle">Also answers on: <span class="font-mono">{{ device.alt_hosts.join(', ') }}</span> (the same miner, counted once).</p>
          <div class="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Check every (seconds)" hint="Leave empty to use the global setting.">
              <template #default="{ id, describedBy }"><Input :id="id" v-model="form.poll_interval_s" type="number" :min="2" :max="3600" :described-by="describedBy" :disabled="!editable" placeholder="default" /></template>
            </Field>
            <Field label="Model name override" hint="Only if the app guessed the model wrong.">
              <template #default="{ id, describedBy }"><Input :id="id" v-model="form.model_override" :described-by="describedBy" :disabled="!editable" :placeholder="device.model" /></template>
            </Field>
          </div>
          <Field class="mt-4" label="Measured power (watts)" hint="Only for miners that cannot report their own power. Enter what a smart plug or meter shows at the wall.">
            <template #default="{ id, describedBy }"><Input :id="id" v-model="form.power_override_w" type="number" :min="0" :max="20000" suffix="W" :described-by="describedBy" :disabled="!editable" /></template>
          </Field>
        </div>

        <div class="divide-y divide-line border-t border-line">
          <ToggleRow v-model="form.enabled" title="Monitor this miner" description="Switch off to stop checking it without deleting its history." :disabled="!editable" />
          <ToggleRow v-model="form.allow_control" title="Allow control from this app" description="When off, the app only watches this miner. Restarts, pool and tuning changes are blocked." :disabled="!editable" />
        </div>

        <p v-if="error" class="rounded-xl border border-bad/30 bg-bad-soft px-3 py-2.5 text-sm text-bad" role="alert">{{ error }}</p>
        <div class="flex items-center gap-3">
          <Button type="submit" variant="primary" :loading="busy" :disabled="!dirty || !editable" data-testid="save-device">Save changes</Button>
          <Button v-if="dirty" type="button" variant="ghost" @click="Object.assign(form, baseline)">Discard</Button>
        </div>
      </form>
    </MetricCard>

    <div class="space-y-[var(--gap-grid)]">
      <MetricCard title="Identity">
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between gap-3"><dt class="text-muted">Type</dt><dd class="text-right font-medium text-fg">{{ device.model }}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-muted">Driver</dt><dd class="text-right font-mono text-[13px] text-fg">{{ device.driver }}</dd></div>
          <div v-if="device.mac" class="flex justify-between gap-3"><dt class="text-muted">MAC</dt><dd class="text-right font-mono text-[13px] text-fg">{{ device.mac }}</dd></div>
          <div v-if="device.serial" class="flex justify-between gap-3"><dt class="text-muted">Serial</dt><dd class="truncate text-right font-mono text-[13px] text-fg">{{ device.serial }}</dd></div>
          <div v-if="device.board_version" class="flex justify-between gap-3"><dt class="text-muted">Board</dt><dd class="text-right text-fg">{{ device.board_version }}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-muted">Can do</dt><dd class="text-right text-xs text-fg">{{ device.capabilities.join(', ') || 'watch only' }}</dd></div>
        </dl>
      </MetricCard>
      <MetricCard v-if="editable" title="Danger zone">
        <p class="mb-3 text-sm text-muted">Stops monitoring this miner and deletes its history from this app. The miner itself is not touched.</p>
        <Button variant="danger" @click="remove">
          <template #icon><Trash2 class="size-4" /></template>
          Remove this miner
        </Button>
      </MetricCard>
    </div>
  </div>
</template>
