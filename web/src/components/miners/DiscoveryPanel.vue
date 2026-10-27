<script setup lang="ts">
import { Check, CircleAlert, Cpu, Info, Network, Radar, RotateCw, Server } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { api, describeError } from '@/lib/api'
import type { DiscoveryJob, MinerCandidate, SourceCandidate } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'

const props = withDefaults(defineProps<{ autoStart?: boolean; adoptLabel?: string }>(), { adoptLabel: 'Start monitoring' })
const emit = defineEmits<{ adopted: [count: number]; navigate: [] }>()

const fmt = useFmt()
const toasts = useToasts()
const router = useRouter()
const live = useLive()

const suggested = ref<string[]>([])
const ranges = ref('')
const advanced = ref(false)
const extraPorts = ref('')
const job = ref<DiscoveryJob | null>(null)
const starting = ref(false)
const error = ref<string | null>(null)
const selected = ref<Set<string>>(new Set())
const adopting = ref(false)
const addingSource = ref<string | null>(null)
let timer: ReturnType<typeof setInterval> | null = null
let preselected = false

const running = computed(() => job.value?.status === 'running')
const finished = computed(() => job.value && job.value.status !== 'running')

function isNew(m: MinerCandidate): boolean {
  return !m.already_added && !m.duplicate_of
}
const newMiners = computed(() => job.value?.miners.filter(isNew) ?? [])
const knownMiners = computed(() => job.value?.miners.filter((m) => !isNew(m)) ?? [])

onMounted(async () => {
  try {
    suggested.value = await api.suggestRanges()
    ranges.value = suggested.value.join(', ')
  } catch {
    /* the server picks sensible defaults when no range is sent */
  }
  if (props.autoStart) void start()
})
onBeforeUnmount(() => {
  stopPolling()
  if (job.value?.status === 'running') void api.cancelDiscovery(job.value.id).catch(() => undefined)
})

function stopPolling(): void {
  if (timer) clearInterval(timer)
  timer = null
}

function parseList(text: string): string[] {
  return text
    .split(/[\s,;]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

async function start(): Promise<void> {
  error.value = null
  starting.value = true
  preselected = false
  selected.value = new Set()
  try {
    const cidrs = parseList(ranges.value)
    const ports = parseList(extraPorts.value)
      .map(Number)
      .filter((n) => Number.isInteger(n) && n > 0 && n < 65536)
    job.value = await api.startDiscovery({ cidrs: cidrs.length ? cidrs : undefined, ports: ports.length ? ports : undefined, include_sources: true })
    stopPolling()
    timer = setInterval(() => void refresh(), 1000)
  } catch (e) {
    error.value = describeError(e)
  } finally {
    starting.value = false
  }
}

async function refresh(): Promise<void> {
  if (!job.value) return
  try {
    job.value = await api.discovery(job.value.id)
  } catch (e) {
    error.value = describeError(e)
    stopPolling()
    return
  }
  if (job.value.status !== 'running') {
    stopPolling()
    if (!preselected) {
      preselected = true
      selected.value = new Set(newMiners.value.map((m) => m.key))
    }
  }
}

async function cancel(): Promise<void> {
  if (!job.value) return
  await api.cancelDiscovery(job.value.id).catch(() => undefined)
  await refresh()
}

function toggle(key: string): void {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

async function adopt(): Promise<void> {
  if (!job.value || !selected.value.size) return
  adopting.value = true
  try {
    const res = await api.adopt(job.value.id, { keys: [...selected.value] })
    for (const d of res.added) live.upsertDevice(d)
    if (res.added.length) toasts.success(`Added ${res.added.length} miner${res.added.length === 1 ? '' : 's'}`, res.added.map((d) => d.name).join(', '))
    for (const m of res.merged) toasts.info(`${m.device} was already known`, m.note)
    emit('adopted', res.added.length)
  } catch (e) {
    toasts.error('Could not add those miners', describeError(e))
  } finally {
    adopting.value = false
  }
}

async function addSource(s: SourceCandidate): Promise<void> {
  if (s.needs_credentials) {
    emit('navigate')
    void router.push({ path: '/settings/sources', query: { add: s.kind, url: s.url } })
    return
  }
  addingSource.value = s.url
  try {
    await api.addSource({ kind: s.kind, name: s.name, url: s.url })
    toasts.success(`${s.name} connected`, 'Network data and pool stats will start appearing.')
    emit('adopted', 0)
    await live.reload()
    if (job.value) job.value = { ...job.value, sources: job.value.sources.filter((x) => x.url !== s.url) }
  } catch (e) {
    toasts.error(`Could not connect to ${s.name}`, describeError(e))
  } finally {
    addingSource.value = null
  }
}

const kindLabel: Record<string, string> = { bitcoin_core: 'Bitcoin Core node', public_pool: 'Public Pool', mempool_space: 'Mempool', ckpool: 'ckpool' }
</script>

<template>
  <div class="space-y-5" data-testid="discovery-panel">
    <!-- 1. before the scan -->
    <section v-if="!job" class="space-y-4">
      <div class="flex items-start gap-4 rounded-2xl border border-line bg-surface-2/60 p-4">
        <div class="grid size-11 shrink-0 place-items-center rounded-xl bg-accent-soft text-accent-text"><Radar class="size-6" aria-hidden="true" /></div>
        <div class="min-w-0">
          <h3 class="text-sm font-semibold text-fg">Scan my network</h3>
          <p class="mt-1 text-sm leading-relaxed text-muted">
            We look for Bitaxe, NerdQAxe, Avalon, Antminer and similar miners on your local network, and for a Bitcoin node or solo pool.
            It only talks to private addresses and never changes anything on your miners.
          </p>
        </div>
      </div>

      <Field label="Network range" hint="Prefilled with the network this computer is on. Add more, separated by commas, if your miners live elsewhere.">
        <template #default="{ id, describedBy }">
          <Input :id="id" v-model="ranges" :described-by="describedBy" mono placeholder="192.168.1.0/24" data-testid="scan-range" />
        </template>
      </Field>

      <button class="text-xs font-medium text-muted hover:text-fg" :aria-expanded="advanced" @click="advanced = !advanced">
        {{ advanced ? 'Hide' : 'Show' }} advanced options
      </button>
      <Field v-if="advanced" label="Extra ports to check" hint="Miners are found on port 80 and 4028 already. List others, separated by commas.">
        <template #default="{ id, describedBy }"><Input :id="id" v-model="extraPorts" :described-by="describedBy" mono placeholder="8080, 4029" /></template>
      </Field>

      <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
      <Button variant="primary" size="lg" class="w-full" :loading="starting" data-testid="start-scan" @click="start">
        <template #icon><Radar class="size-5" /></template>
        Scan my network
      </Button>
    </section>

    <!-- 2. scanning / results -->
    <section v-else class="space-y-5">
      <div class="rounded-2xl border border-line bg-surface-2/60 p-4">
        <div class="mb-3 flex items-center justify-between gap-3">
          <p class="text-sm font-medium text-fg" aria-live="polite">
            <template v-if="running">Scanning… {{ job.miners.length }} miner{{ job.miners.length === 1 ? '' : 's' }} found so far</template>
            <template v-else-if="job.status === 'finished'">Scan finished: {{ job.miners.length }} miner{{ job.miners.length === 1 ? '' : 's' }} found</template>
            <template v-else-if="job.status === 'cancelled'">Scan stopped</template>
            <template v-else>The scan failed</template>
          </p>
          <Button v-if="running" size="xs" variant="ghost" @click="cancel">Stop</Button>
          <Button v-else size="xs" variant="ghost" @click="job = null">
            <template #icon><RotateCw class="size-3.5" /></template>
            Scan again
          </Button>
        </div>
        <ProgressBar :value="job.progress" label="Scan progress" />
        <p class="mt-2 text-xs text-subtle">
          {{ job.scanned_hosts }} of {{ job.total_hosts || '…' }} addresses checked · {{ job.cidrs.join(', ') }}
          <span v-if="running" class="capitalize"> · {{ job.phase }}</span>
        </p>
        <p v-if="job.error" class="mt-2 text-sm text-bad" role="alert">{{ job.error }}</p>
      </div>

      <div v-if="newMiners.length" class="space-y-2">
        <h3 class="eyebrow">New miners</h3>
        <ul class="space-y-2">
          <li v-for="m in newMiners" :key="m.key">
            <label
              class="flex cursor-pointer items-center gap-3 rounded-xl border bg-surface-2/60 p-3 transition-colors hover:border-line-strong"
              :class="selected.has(m.key) ? 'border-accent-line bg-accent-softer' : 'border-line'"
            >
              <input type="checkbox" class="size-4 accent-[var(--accent)]" :checked="selected.has(m.key)" :data-testid="`pick-${m.host}`" @change="toggle(m.key)" />
              <Cpu class="size-5 shrink-0 text-muted" aria-hidden="true" />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-medium text-fg">{{ m.model }}</span>
                <span class="block truncate text-xs text-subtle">
                  <span class="font-mono">{{ m.host }}<template v-if="m.port !== 80">:{{ m.port }}</template></span>
                  <template v-if="m.firmware"> · {{ m.firmware }}</template>
                  <template v-if="m.hostname && m.hostname !== m.host"> · {{ m.hostname }}</template>
                </span>
              </span>
              <span v-if="m.hashrate_hs" class="tnum shrink-0 text-sm text-muted">{{ fmt.hashrate(m.hashrate_hs) }}</span>
            </label>
          </li>
        </ul>
      </div>

      <div v-if="knownMiners.length" class="space-y-2">
        <h3 class="eyebrow">Already handled</h3>
        <ul class="space-y-1.5">
          <li v-for="m in knownMiners" :key="m.key" class="flex items-center gap-3 rounded-xl border border-line px-3 py-2">
            <Check v-if="m.already_added" class="size-4 shrink-0 text-ok" aria-hidden="true" />
            <Info v-else class="size-4 shrink-0 text-info" aria-hidden="true" />
            <span class="min-w-0 flex-1 truncate text-sm text-muted">
              {{ m.model }} <span class="font-mono text-xs text-subtle">{{ m.host }}</span>
            </span>
            <Badge size="sm" :tone="m.already_added ? 'ok' : 'info'">{{ m.already_added ? 'Already monitored' : `Same device as ${m.duplicate_of}` }}</Badge>
          </li>
        </ul>
      </div>

      <div v-if="job.sources.length" class="space-y-2">
        <h3 class="eyebrow">Node &amp; pool found</h3>
        <ul class="space-y-2">
          <li v-for="s in job.sources" :key="s.url" class="flex items-center gap-3 rounded-xl border border-line bg-surface-2/60 p-3">
            <component :is="s.kind === 'bitcoin_core' ? Server : Network" class="size-5 shrink-0 text-muted" aria-hidden="true" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-fg">{{ s.name || kindLabel[s.kind] || s.kind }}</span>
              <span class="block truncate text-xs text-subtle"><span class="font-mono">{{ s.url }}</span> · {{ s.reason }}</span>
            </span>
            <Button size="sm" :variant="s.needs_credentials ? 'secondary' : 'soft'" :loading="addingSource === s.url" @click="addSource(s)">
              {{ s.needs_credentials ? 'Set up…' : 'Connect' }}
            </Button>
          </li>
        </ul>
      </div>

      <div v-if="finished && !job.miners.length && !job.error" class="rounded-2xl border border-warn/30 bg-warn-soft p-4 text-sm text-warn">
        <p class="flex items-center gap-2 font-medium"><CircleAlert class="size-4" aria-hidden="true" /> No miners found</p>
        <ul class="mt-2 list-disc space-y-1 pl-5 text-[13px] leading-relaxed text-muted">
          <li>Check the miners are powered on and joined to the same network (WiFi or cable) as this computer.</li>
          <li>Running in Docker? Bridge networking can't see your home network. Enter your range above (for example 192.168.1.0/24) or use host networking.</li>
          <li>If you know a miner's address, use “Add by address” instead.</li>
        </ul>
      </div>

      <Button v-if="newMiners.length" variant="primary" size="lg" class="w-full" :loading="adopting" :disabled="!selected.size" data-testid="adopt" @click="adopt">
        {{ props.adoptLabel }}
        {{ selected.size ? `(${selected.size})` : '' }}
      </Button>
    </section>
  </div>
</template>
