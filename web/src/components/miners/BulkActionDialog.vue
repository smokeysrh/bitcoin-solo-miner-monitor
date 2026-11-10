<script setup lang="ts">
import { CircleCheck, CircleX } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { api, describeError } from '@/lib/api'
import type { ActionResult } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const props = defineProps<{ action: string; ids: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ done: [] }>()

const live = useLive()
const toasts = useToasts()
const phase = ref<'loading' | 'preview' | 'running' | 'done'>('loading')
const results = ref<ActionResult[]>([])
const error = ref<string | null>(null)
/** The exact action and miners a successful preview covered; Apply sends only this. */
const previewed = ref<{ action: string; ids: string[] } | null>(null)
/** Bumped whenever the operation changes, so a late response from an older one is ignored. */
let generation = 0

const VERB: Record<string, { title: string; verb: string; warn?: string }> = {
  restart: { title: 'Restart miners', verb: 'Restart', warn: 'Each miner stops hashing for a minute or so while it reboots.' },
  identify: { title: 'Flash miners', verb: 'Flash', warn: 'Makes the screen or LED flash so you can find them.' },
  pause: { title: 'Pause mining', verb: 'Pause', warn: 'They stay paused until you resume them.' },
  resume: { title: 'Resume mining', verb: 'Resume' },
}
const meta = computed(() => VERB[props.action] ?? { title: props.action, verb: 'Run' })
const okCount = computed(() => results.value.filter((r) => r.ok).length)
const operationKey = computed(() => JSON.stringify([props.action, props.ids]))

function invalidate(): void {
  generation++
  previewed.value = null
  results.value = []
  error.value = null
}

async function preview(): Promise<void> {
  invalidate()
  const mine = generation
  const snapshot = { action: props.action, ids: [...props.ids] }
  phase.value = 'loading'
  try {
    const r = await api.bulkAction({ action: snapshot.action, device_ids: snapshot.ids, dry_run: true })
    if (mine !== generation) return
    results.value = r.results
    previewed.value = snapshot
    phase.value = 'preview'
  } catch (e) {
    if (mine !== generation) return
    error.value = describeError(e)
    phase.value = 'preview'
  }
}

async function apply(): Promise<void> {
  const snapshot = previewed.value
  if (!snapshot || phase.value !== 'preview') return
  const mine = ++generation
  phase.value = 'running'
  try {
    const r = await api.bulkAction({ action: snapshot.action, device_ids: snapshot.ids, dry_run: false })
    // The miners were already told. If the dialog moved on meanwhile, still report the outcome but leave its new state alone.
    const current = mine === generation
    if (current) {
      results.value = r.results
      phase.value = 'done'
    }
    const ok = r.results.filter((x) => x.ok).length
    const verb = (VERB[snapshot.action] ?? { verb: 'Run' }).verb
    if (ok === r.results.length) toasts.success(`${verb} sent to ${ok} miner${ok === 1 ? '' : 's'}`)
    else toasts.warning(`${ok} of ${r.results.length} worked`, 'See the list for what failed.')
    void live.reload()
    if (current) emit('done')
  } catch (e) {
    if (mine !== generation) {
      toasts.error('A miner action did not finish', describeError(e))
      return
    }
    error.value = describeError(e)
    phase.value = 'preview'
  }
}

// Closing or changing the action/miners drops the old preview. A finished apply stays on screen even though
// the parent clears the selection after `done`.
watch([open, operationKey], () => {
  if (!open.value) {
    invalidate()
    phase.value = 'loading'
  } else if (phase.value !== 'done') {
    void preview()
  }
}, { immediate: true })
</script>

<template>
  <Dialog v-model:open="open" :title="meta.title" :description="`${ids.length} miner${ids.length === 1 ? '' : 's'} selected`" size="md" :dismissible="phase !== 'running'">
    <div class="space-y-3">
      <p v-if="phase === 'running'" class="text-sm text-muted">Sending to your miners. This window stays open until they answer.</p>
      <p v-if="meta.warn && phase !== 'done'" class="text-sm text-muted">{{ meta.warn }}</p>
      <div v-if="phase === 'loading'" class="space-y-2"><Skeleton v-for="i in Math.min(4, ids.length)" :key="i" class="h-11 rounded-xl" /></div>
      <p v-if="error" class="rounded-xl border border-bad/30 bg-bad-soft px-3 py-2.5 text-sm text-bad" role="alert">{{ error }}</p>
      <ul v-if="results.length && phase !== 'loading'" class="divide-y divide-line rounded-xl border border-line">
        <li v-for="r in results" :key="r.device_id" class="flex items-start gap-3 px-3.5 py-2.5">
          <CircleCheck v-if="r.ok" class="mt-0.5 size-4.5 shrink-0 text-ok" aria-hidden="true" />
          <CircleX v-else class="mt-0.5 size-4.5 shrink-0 text-bad" aria-hidden="true" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-fg">{{ r.name ?? live.deviceName(r.device_id) }}</p>
            <p class="text-xs" :class="r.ok ? 'text-subtle' : 'text-bad'">
              {{ r.ok ? (phase === 'done' ? (r.message ?? 'Done') : 'Ready') : (r.error ?? 'Not possible on this miner') }}
            </p>
          </div>
        </li>
      </ul>
    </div>
    <template #footer>
      <Button variant="ghost" :disabled="phase === 'running'" @click="open = false">{{ phase === 'done' ? 'Close' : 'Cancel' }}</Button>
      <Button v-if="phase !== 'done'" :variant="action === 'restart' || action === 'pause' ? 'danger' : 'primary'" :loading="phase === 'running'" :disabled="phase === 'loading' || !previewed || okCount === 0" @click="apply">
        {{ meta.verb }} {{ okCount }} miner{{ okCount === 1 ? '' : 's' }}
      </Button>
    </template>
  </Dialog>
</template>
