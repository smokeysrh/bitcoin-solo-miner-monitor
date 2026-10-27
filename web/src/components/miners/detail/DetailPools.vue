<script setup lang="ts">
import { Lock, Network } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { confirmDialog } from '@/composables/useConfirm'
import { useMinerActions } from '@/composables/useMinerActions'
import { api, describeError } from '@/lib/api'
import type { DeviceView, PoolInfo, Source } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Segmented from '@/components/ui/Segmented.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import Term from '@/components/ui/Term.vue'
import KeyValue from '@/components/ui/KeyValue.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

const props = defineProps<{ device: DeviceView }>()
const fmt = useFmt()
const live = useLive()
const toasts = useToasts()
const actions = useMinerActions()

const pools = computed<PoolInfo[]>(() => props.device.telemetry?.pools ?? [])
const canEdit = computed(() => actions.can(props.device, 'set_pool'))

const role = ref<'primary' | 'fallback'>('primary')
const preset = ref('custom')
const form = reactive({ url: '', port: 3333 as number | null, user: '', password: 'x', tls: false })
const busy = ref(false)
const error = ref<string | null>(null)

const current = computed(() => pools.value.find((p) => p.role === role.value) ?? null)

// "my pool" shortcut when a Public Pool (Umbrel, Start9...) is configured. The stratum port is not part of
// the pool's web API, so we offer the common default (2018) and leave it editable.
const sources = ref<Source[]>([])
onMounted(async () => {
  try {
    sources.value = (await api.sources()).sources
  } catch {
    /* the shortcut simply is not offered */
  }
})
const myPoolHost = computed(() => {
  const url = sources.value.find((s) => s.kind === 'public_pool' && s.enabled && s.url)?.url
  if (!url) return null
  try {
    return new URL(url).hostname
  } catch {
    return null
  }
})

const presets = computed(() => {
  const list = [
    { value: 'custom', label: 'Type it myself' },
    { value: 'ckpool', label: 'solo.ckpool.org (public solo pool)' },
  ]
  if (myPoolHost.value) list.splice(1, 0, { value: 'mine', label: `My own pool (${myPoolHost.value})` })
  return list
})

function load(): void {
  const p = current.value
  form.url = p?.url ?? ''
  form.port = p?.port ?? 3333
  form.user = p?.user ?? ''
  form.password = 'x'
  form.tls = !!p?.tls
  preset.value = 'custom'
  error.value = null
}
watch([() => props.device.id, role], load, { immediate: true })

function onPreset(v: string | number | null | undefined): void {
  preset.value = String(v)
  const addr = current.value?.address ?? form.user.split('.')[0] ?? ''
  const worker = current.value?.worker
  if (v === 'ckpool') {
    form.url = 'solo.ckpool.org'
    form.port = 3333
    form.tls = false
    if (addr) form.user = worker ? `${addr}.${worker}` : addr
  } else if (v === 'mine' && myPoolHost.value) {
    form.url = myPoolHost.value
    form.port = 2018
    form.tls = false
    if (addr) form.user = worker ? `${addr}.${worker}` : addr
  }
}

const addressLooksOff = computed(() => {
  const addr = form.user.split('.')[0] ?? ''
  return !!addr && !/^(bc1|tb1|[13mn2])[a-zA-HJ-NP-Z0-9]{25,90}$/.test(addr)
})

async function apply(): Promise<void> {
  error.value = null
  const url = form.url.trim().replace(/^stratum\+tcp:\/\//, '').replace(/^stratum\+ssl:\/\//, '')
  if (!url) return void (error.value = 'Enter the pool address, for example solo.ckpool.org.')
  if (!form.port || form.port < 1 || form.port > 65535) return void (error.value = 'The port must be a number between 1 and 65535.')
  if (!form.user.trim()) return void (error.value = 'Enter your payout address (optionally followed by .workername).')

  const ok = await confirmDialog({
    title: `Change the ${role.value} pool on ${props.device.name}?`,
    message: `It will reconnect to ${url}:${form.port}. If the address or login is wrong, this miner keeps hashing but nothing it finds will pay you.`,
    confirmLabel: 'Change pool',
    tone: 'danger',
  })
  if (!ok) return

  busy.value = true
  try {
    const res = await api.action(props.device.id, 'set_pool', { url, port: form.port, user: form.user.trim(), password: form.password || 'x', role: role.value, tls: form.tls })
    toasts.success('Pool changed', res.message ?? `${props.device.name} is reconnecting.`)
    live.upsertDevice(await api.pollDevice(props.device.id))
  } catch (e) {
    error.value = describeError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="grid gap-[var(--gap-grid)] xl:grid-cols-2">
    <MetricCard title="Pools this miner uses" :icon="Network">
      <p class="mb-4 text-sm text-muted">
        A miner has a <Term k="pool">main pool</Term> and usually a <Term k="fallback">fallback</Term>. The one marked “in use” is receiving its work right now.
      </p>
      <ul v-if="pools.length" class="space-y-3" data-testid="pool-list">
        <li v-for="p in pools" :key="p.role + p.url" class="rounded-xl border p-4" :class="p.active ? 'border-accent-line bg-accent-softer' : 'border-line bg-surface-2/50'">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <Badge :tone="p.role === 'primary' ? 'accent' : 'neutral'" size="sm">{{ p.role === 'primary' ? 'Main pool' : 'Fallback' }}</Badge>
            <Badge v-if="p.active" tone="ok" dot size="sm">In use</Badge>
            <Badge v-if="p.tls" tone="info" size="sm"><Lock class="size-3" /> Encrypted</Badge>
          </div>
          <KeyValue
            :rows="[
              { label: 'Address', value: `${p.url ?? '–'}${p.port ? ':' + p.port : ''}`, mono: true },
              { label: 'Payout address', value: fmt.shortAddress(p.address), title: p.address ?? undefined, mono: true },
              { label: 'Worker', value: p.worker ?? '–' },
              ...(p.active ? [{ label: 'Latency', value: p.ping_ms != null ? `${Math.round(p.ping_ms)} ms` : '–' }, { label: 'Share difficulty', value: fmt.formatDifficulty(p.difficulty) }] : []),
            ]"
          />
        </li>
      </ul>
      <p v-else class="text-sm text-muted">This miner does not report its pool settings.</p>
    </MetricCard>

    <MetricCard v-if="canEdit" title="Change a pool">
      <form class="space-y-4" @submit.prevent="apply">
        <Segmented v-model="role" label="Which pool" :options="[{ value: 'primary', label: 'Main pool' }, { value: 'fallback', label: 'Fallback' }]" />
        <Field label="Quick fill">
          <template #default="{ id }"><Select :id="id" :model-value="preset" :options="presets" @update:model-value="onPreset" /></template>
        </Field>
        <div class="grid grid-cols-[1fr_7rem] gap-3">
          <Field label="Pool address" required hint="Host name or IP, without stratum+tcp://">
            <template #default="{ id, describedBy }"><Input :id="id" v-model="form.url" mono :described-by="describedBy" placeholder="solo.ckpool.org" autocomplete="off" /></template>
          </Field>
          <Field label="Port" required>
            <template #default="{ id }"><Input :id="id" v-model="form.port" type="number" :min="1" :max="65535" mono /></template>
          </Field>
        </div>
        <Field label="Login" required hint="Your payout address, optionally followed by .workername. This is where a found block pays.">
          <template #default="{ id, describedBy, invalid }">
            <Input :id="id" v-model="form.user" mono :described-by="describedBy" :invalid="invalid || addressLooksOff" placeholder="bc1q…yourAddress.garage" autocomplete="off" />
          </template>
        </Field>
        <p v-if="addressLooksOff" class="-mt-2 text-xs text-warn">That does not look like a Bitcoin address. Double-check it for typos before saving.</p>
        <div class="grid grid-cols-2 items-end gap-3">
          <Field label="Pool password" hint="Almost always “x”.">
            <template #default="{ id }"><Input :id="id" v-model="form.password" type="password" autocomplete="off" /></template>
          </Field>
          <label class="flex h-10 items-center justify-between gap-3 rounded-xl border border-line bg-surface-2 px-3 text-sm text-muted">
            Use encryption (TLS) <Switch v-model="form.tls" label="Use TLS" />
          </label>
        </div>
        <p v-if="error" class="rounded-xl border border-bad/30 bg-bad-soft px-3 py-2.5 text-sm text-bad" role="alert">{{ error }}</p>
        <Button type="submit" variant="primary" :loading="busy">Save pool</Button>
      </form>
    </MetricCard>
    <MetricCard v-else title="Pool settings">
      <p class="text-sm text-muted">Changing pools from here is not available for this miner (or control is switched off in Settings → Safety).</p>
    </MetricCard>
  </div>
</template>
