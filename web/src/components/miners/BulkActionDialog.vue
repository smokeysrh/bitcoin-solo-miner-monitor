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

const VERB: Record<string, { title: string; verb: string; warn?: string }> = {
  restart: { title: 'Restart miners', verb: 'Restart', warn: 'Each miner stops hashing for a minute or so while it reboots.' },
  identify: { title: 'Flash miners', verb: 'Flash', warn: 'Makes the screen or LED flash so you can find them.' },
  pause: { title: 'Pause mining', verb: 'Pause', warn: 'They stay paused until you resume them.' },
  resume: { title: 'Resume mining', verb: 'Resume' },
}
const meta = computed(() => VERB[props.action] ?? { title: props.action, verb: 'Run' })
const okCount = computed(() => results.value.filter((r) => r.ok).length)

async function preview(): Promise<void> {
  phase.value = 'loading'
  error.value = null
  try {
    const r = await api.bulkAction({ action: props.action, device_ids: props.ids, dry_run: true })
    results.value = r.results
    phase.value = 'preview'
  } catch (e) {
    error.value = describeError(e)
    phase.value = 'preview'
  }
}

async function apply(): Promise<void> {
  phase.value = 'running'
  try {
    const r = await api.bulkAction({ action: props.action, device_ids: props.ids, dry_run: false })
    results.value = r.results
    phase.value = 'done'
    const ok = r.results.filter((x) => x.ok).length
    if (ok === r.results.length) toasts.success(`${meta.value.verb} sent to ${ok} miner${ok === 1 ? '' : 's'}`)
    else toasts.warning(`${ok} of ${r.results.length} worked`, 'See the list for what failed.')
    void live.reload()
    emit('done')
  } catch (e) {
    error.value = describeError(e)
    phase.value = 'preview'
  }
}

watch(open, (v) => v && void preview(), { immediate: true })
</script>

<template>
  <Dialog v-model:open="open" :title="meta.title" :description="`${ids.length} miner${ids.length === 1 ? '' : 's'} selected`" size="md">
    <div class="space-y-3">
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
      <Button variant="ghost" @click="open = false">{{ phase === 'done' ? 'Close' : 'Cancel' }}</Button>
      <Button v-if="phase !== 'done'" :variant="action === 'restart' || action === 'pause' ? 'danger' : 'primary'" :loading="phase === 'running'" :disabled="phase === 'loading' || okCount === 0" @click="apply">
        {{ meta.verb }} {{ okCount }} miner{{ okCount === 1 ? '' : 's' }}
      </Button>
    </template>
  </Dialog>
</template>
