<script setup lang="ts">
import { CircleCheck, CircleX, Globe, Pencil, Plus, Server, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
import { useFmt } from '@/composables/useFmt'
import { api, describeError } from '@/lib/api'
import { kindLabel } from '@/lib/labels'
import type { ConnectionTest, ImplicitSource, Source, SourceKind } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const fmt = useFmt()
const route = useRoute()
const router = useRouter()
const session = useSession()
const settings = useSettings()
const toasts = useToasts()
const live = useLive()
const admin = computed(() => session.canAdmin)

const kinds = ref<SourceKind[]>([])
const sources = ref<Source[]>([])
const implicit = ref<ImplicitSource[]>([])
const loading = ref(true)

async function load(): Promise<void> {
  try {
    const [k, s] = await Promise.all([api.sourceKinds(), api.sources()])
    kinds.value = k
    sources.value = s.sources
    implicit.value = s.implicit
  } finally {
    loading.value = false
  }
}

// ---- dialog
const open = ref(false)
const editing = ref<Source | null>(null)
const form = reactive<{ kind: string; name: string; url: string; secret: Record<string, string>; options: Record<string, string> }>({ kind: '', name: '', url: '', secret: {}, options: {} })
const test = ref<ConnectionTest | null>(null)
const testing = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const spec = computed(() => kinds.value.find((k) => k.kind === form.kind) ?? null)

function openAdd(kind?: string, url?: string): void {
  editing.value = null
  const k = kind && kinds.value.some((x) => x.kind === kind) ? kind : (kinds.value[0]?.kind ?? '')
  Object.assign(form, { kind: k, name: '', url: url ?? '', secret: {}, options: {} })
  test.value = null
  error.value = null
  open.value = true
}
function openEdit(s: Source): void {
  editing.value = s
  Object.assign(form, { kind: s.kind, name: s.name, url: s.url ?? '', secret: {}, options: Object.fromEntries(Object.entries(s.options).map(([k, v]) => [k, String(v ?? '')])) })
  test.value = null
  error.value = null
  open.value = true
}
watch(() => form.kind, () => {
  if (!editing.value) test.value = null
})

function body() {
  const secret = Object.fromEntries(Object.entries(form.secret).filter(([, v]) => v !== ''))
  const options = Object.fromEntries(Object.entries(form.options).filter(([, v]) => v !== ''))
  return { kind: form.kind, name: form.name.trim() || undefined, url: form.url.trim() || null, secret, options }
}

async function runTest(): Promise<void> {
  testing.value = true
  error.value = null
  try {
    test.value = await api.testSource(body())
  } catch (e) {
    test.value = { ok: false, message: describeError(e), details: {}, hints: [] }
  } finally {
    testing.value = false
  }
}

async function save(force = false): Promise<void> {
  saving.value = true
  error.value = null
  try {
    if (editing.value) {
      const b = body()
      await api.updateSource(editing.value.id, { name: b.name, url: b.url, options: b.options, ...(Object.keys(b.secret).length ? { secret: b.secret } : {}) })
      toasts.success('Saved')
    } else {
      await api.addSource(body(), force)
      toasts.success(`${spec.value?.label ?? 'Source'} connected`)
    }
    open.value = false
    await Promise.all([load(), live.reload()])
  } catch (e) {
    error.value = describeError(e)
  } finally {
    saving.value = false
  }
}

async function toggleSource(s: Source, on: boolean): Promise<void> {
  try {
    await api.updateSource(s.id, { enabled: on })
    await load()
  } catch (e) {
    toasts.error('Could not change that', describeError(e))
  }
}
async function remove(s: Source): Promise<void> {
  if (!(await confirmDialog({ title: `Remove ${s.name}?`, message: 'The app stops using it. Nothing is changed on the node or pool itself.', confirmLabel: 'Remove', tone: 'danger' }))) return
  try {
    await api.deleteSource(s.id)
    await Promise.all([load(), live.reload()])
  } catch (e) {
    toasts.error('Could not remove it', describeError(e))
  }
}

async function setPublic(on: boolean): Promise<void> {
  try {
    await settings.patch({ network: { use_public_apis: on } })
    await live.reload()
  } catch (e) {
    toasts.error('Could not change that', describeError(e))
  }
}

onMounted(async () => {
  await load()
  const add = route.query.add
  if (typeof add === 'string' && admin.value) {
    openAdd(add, typeof route.query.url === 'string' ? route.query.url : undefined)
    void router.replace({ query: {} })
  }
})
</script>

<template>
  <SettingsCard title="Your node &amp; pool" description="Connect your own Bitcoin node or solo pool. You get private network data, pool-side statistics, and the app notices a found block immediately.">
    <div class="mb-4 flex justify-end"><Button v-if="admin" variant="primary" size="sm" data-testid="add-source" @click="openAdd()"><template #icon><Plus class="size-4" /></template>Connect a node or pool</Button></div>
    <div v-if="loading" class="space-y-2"><Skeleton v-for="i in 2" :key="i" class="h-16 rounded-xl" /></div>
    <ul v-else-if="sources.length" class="space-y-3" data-testid="source-list">
      <li v-for="s in sources" :key="s.id" class="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface-2/50 p-4">
        <component :is="s.kind === 'bitcoin_core' ? Server : Globe" class="size-5 shrink-0 text-muted" aria-hidden="true" />
        <div class="min-w-0 flex-1 basis-56">
          <p class="flex flex-wrap items-center gap-2 text-sm font-medium text-fg">{{ s.name }}<Badge size="sm">{{ kindLabel(s.kind) }}</Badge><Badge v-if="!s.enabled" size="sm" tone="warn">Off</Badge></p>
          <p class="truncate font-mono text-xs text-subtle">{{ s.url }}</p>
          <p v-if="s.health" class="mt-1 flex items-center gap-1.5 text-xs" :class="s.health.ok === false ? 'text-bad' : s.health.ok ? 'text-ok' : 'text-subtle'">
            <CircleCheck v-if="s.health.ok" class="size-3.5" /><CircleX v-else-if="s.health.ok === false" class="size-3.5" />
            {{ s.health.ok ? `Working, checked ${fmt.formatAgo(s.health.last_ok)}` : s.health.ok === false ? (s.health.error ?? 'Not answering') : 'Checking…' }}
          </p>
        </div>
        <template v-if="admin">
          <Switch :model-value="s.enabled" :label="`Use ${s.name}`" @update:model-value="(v) => toggleSource(s, v)" />
          <Button size="iconSm" variant="ghost" :aria-label="`Edit ${s.name}`" @click="openEdit(s)"><Pencil class="size-4" /></Button>
          <Button size="iconSm" variant="ghost" :aria-label="`Remove ${s.name}`" @click="remove(s)"><Trash2 class="size-4" /></Button>
        </template>
      </li>
    </ul>
    <EmptyState v-else compact :icon="Server" title="Nothing connected yet" description="Umbrel, Start9, RaspiBlitz, myNode and a plain Bitcoin Core all work. If you already scanned the network, we may have spotted yours.">
      <Button v-if="admin" variant="soft" @click="openAdd()">Connect now</Button>
    </EmptyState>
  </SettingsCard>

  <SettingsCard title="Public data" description="mempool.space provides block height, difficulty, fees and the Bitcoin price when you have no node. Turn it off to keep every lookup on your own network.">
    <ToggleRow :model-value="settings.data?.network.use_public_apis ?? true" :disabled="!admin" title="Use mempool.space" description="No account or key needed. Only public numbers are requested; nothing about your miners is sent." @update:model-value="setPublic" />
    <ul v-if="implicit.length" class="mt-2 space-y-1.5">
      <li v-for="i in implicit" :key="i.id" class="flex items-center gap-2 text-xs text-subtle">
        <span class="size-1.5 rounded-full" :class="i.health.ok ? 'bg-ok' : i.health.ok === false ? 'bg-bad' : 'bg-subtle'" aria-hidden="true" />{{ i.name }}: {{ i.health.ok ? 'working' : (i.health.error ?? 'waiting') }}
      </li>
    </ul>
  </SettingsCard>

  <Dialog v-model:open="open" :title="editing ? `Edit ${editing.name}` : 'Connect a node or pool'" size="lg">
    <form class="space-y-5" @submit.prevent="save()">
      <Field v-if="!editing" label="What are you connecting?">
        <template #default="{ id }"><Select :id="id" v-model="form.kind" :options="kinds.map((k) => ({ value: k.kind, label: k.label }))" data-testid="source-kind" /></template>
      </Field>
      <div v-if="spec" class="rounded-xl border border-line bg-surface-2/60 p-4 text-sm">
        <p class="font-medium text-fg">You get</p>
        <ul class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-muted"><li v-for="g in spec.gives" :key="g" class="flex items-center gap-1.5"><CircleCheck class="size-3.5 text-ok" aria-hidden="true" />{{ g }}</li></ul>
        <p v-if="spec.where_to_find_login" class="mt-3 text-xs leading-relaxed text-subtle"><b class="text-muted">Where to find the login:</b> {{ spec.where_to_find_login }}</p>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <Field label="Address" required :hint="spec ? `For example ${spec.url_example}` : undefined" class="sm:col-span-2">
          <template #default="{ id, describedBy }"><Input :id="id" v-model="form.url" mono :described-by="describedBy" :placeholder="spec?.url_example" autocomplete="off" data-testid="source-url" /></template>
        </Field>
        <Field v-for="f in spec?.secret_fields ?? []" :key="f.name" :label="f.label" :hint="editing ? 'Leave empty to keep the saved value.' : undefined">
          <template #default="{ id, describedBy }"><Input :id="id" v-model="form.secret[f.name]" :type="f.secret ? 'password' : 'text'" :described-by="describedBy" autocomplete="off" :data-testid="`source-${f.name}`" /></template>
        </Field>
        <Field v-for="f in spec?.option_fields ?? []" :key="f.name" :label="f.label">
          <template #default="{ id }"><Input :id="id" v-model="form.options[f.name]" mono /></template>
        </Field>
        <Field label="Name (optional)" class="sm:col-span-2"><template #default="{ id }"><Input :id="id" v-model="form.name" :placeholder="spec?.label" /></template></Field>
      </div>

      <div v-if="test" :class="['rounded-xl border p-4 text-sm', test.ok ? 'border-ok/30 bg-ok-soft' : 'border-bad/30 bg-bad-soft']" role="status" data-testid="source-test">
        <p class="flex items-center gap-2 font-medium" :class="test.ok ? 'text-ok' : 'text-bad'"><CircleCheck v-if="test.ok" class="size-4" /><CircleX v-else class="size-4" />{{ test.message }}</p>
        <ul v-if="test.hints.length" class="mt-2 list-disc space-y-1 pl-5 text-[13px] text-muted"><li v-for="h in test.hints" :key="h">{{ h }}</li></ul>
      </div>
      <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <Button variant="ghost" @click="open = false">Cancel</Button>
      <Button variant="secondary" :loading="testing" data-testid="source-test-btn" @click="runTest">Test connection</Button>
      <Button v-if="test && !test.ok && !editing" variant="ghost" :loading="saving" @click="save(true)">Save anyway</Button>
      <Button variant="primary" :loading="saving" data-testid="source-save" @click="save()">{{ editing ? 'Save' : 'Connect' }}</Button>
    </template>
  </Dialog>
</template>
