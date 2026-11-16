<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { Check } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useHashling } from '@/stores/hashling'
import { useInsights } from '@/stores/insights'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import Button from '@/components/ui/Button.vue'
import RingGauge from '@/components/ui/RingGauge.vue'

const insights = useInsights()
const live = useLive()
const ui = useUi()
const router = useRouter()
const session = useSession()
const hashling = useHashling()
const hidden = useStorage('bsmm.checklistHidden', false)

// The insights answer for the fleet as it was when they were asked, and each change of miners or sources asks again. Until
// that answer is in, they are not current for the present fleet: an empty fleet's list has no reminders at all, so with the
// first miner just added it would read as "every step done". Only the latest question counts: an answer to an earlier one
// (the same miner and source counts can come back after a removal and a re-add) never makes the insights in hand current.
const fleetKey = computed(() => `${live.deviceCount}:${live.network?.sources.length ?? 0}`)
/** The fleet the insights in hand were last asked about successfully. */
const answeredFor = ref<string | null>(null)
let questionSeq = 0
async function ask(key: string, force: boolean): Promise<void> {
  const mine = ++questionSeq
  answeredFor.value = null
  await insights.refresh(force)
  if (mine === questionSeq && insights.error === null) answeredFor.value = key
}
onMounted(() => void ask(fleetKey.value, false))
watch(fleetKey, (key) => void ask(key, true))

interface Step {
  id: string
  title: string
  why: string
  done: boolean
  cta: string
  run: () => void
}

const steps = computed<Step[]>(() => [
  {
    id: 'miners',
    title: 'Add your miners',
    why: 'Scan your network or type an address. Takes about twenty seconds.',
    done: live.deviceCount > 0,
    cta: 'Find miners',
    run: () => (ui.addMinerOpen = true),
  },
  {
    id: 'node',
    title: 'Connect your node or pool',
    why: 'Unlocks pool stats and spots a found block the moment it happens.',
    done: !insights.has('no-node') && live.deviceCount > 0,
    cta: 'Connect',
    run: () => void router.push('/settings/sources'),
  },
  {
    id: 'energy',
    title: 'Set your electricity price',
    why: 'So costs use your real rate.',
    done: !insights.has('energy-default') && live.deviceCount > 0,
    cta: 'Set price',
    run: () => void router.push('/settings/energy'),
  },
  {
    id: 'alerts',
    title: 'Get alerts on your phone',
    why: 'ntfy, Telegram, Discord or email tell you when something breaks.',
    done: !insights.has('no-channel') && live.deviceCount > 0,
    cta: 'Set up',
    run: () => void router.push('/settings/notifications'),
  },
  {
    id: 'password',
    title: 'Protect the dashboard',
    why: 'A password stops anyone else on your network changing your settings and miner list.',
    done: !insights.has('no-password') && live.deviceCount > 0,
    cta: 'Set password',
    run: () => void router.push('/settings/security'),
  },
])

const doneCount = computed(() => steps.value.filter((s) => s.done).length)
const visible = computed(() => insights.loaded && !hidden.value && doneCount.value < steps.value.length && session.canControl)

// The last step done while the page is open is Hashling's moment, once ever, and only judged from insights that are current
// for the present fleet. The first current list is the baseline (a list that was already complete when the page loaded is
// not news); after that, going from unfinished to finished counts.
const current = computed(() => insights.loaded && live.loaded && answeredFor.value === fleetKey.value)
let lastCurrentDone: number | null = null
watch(
  [current, doneCount],
  ([isCurrent, done]) => {
    if (!isCurrent) return
    const before = lastCurrentDone
    lastCurrentDone = done
    if (before !== null && before < steps.value.length && done === steps.value.length) hashling.show('M21', {}, { once: 'checklist' })
  },
  { immediate: true },
)
</script>

<template>
  <section v-if="visible" class="card relative overflow-hidden" aria-label="Getting started" data-testid="widget-checklist">
    <div class="pointer-events-none absolute -top-20 right-0 size-64 rounded-full bg-accent/10 blur-3xl" aria-hidden="true" />
    <div class="relative p-[var(--pad-card)]">
      <div class="flex items-center gap-4">
        <RingGauge :value="doneCount / steps.length" :size="56" :stroke="6" :label="`${doneCount} of ${steps.length} setup steps done`">
          <span class="tnum text-sm font-semibold text-fg">{{ doneCount }}/{{ steps.length }}</span>
        </RingGauge>
        <div class="min-w-0 flex-1">
          <h2 class="text-base font-bold text-fg">Get set up</h2>
          <p class="text-sm text-muted">A few quick steps make this dashboard yours. Skip any you do not need.</p>
        </div>
        <button class="text-xs font-medium text-subtle hover:text-fg" @click="hidden = true">Hide</button>
      </div>
      <ul class="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
        <li
          v-for="s in steps"
          :key="s.id"
          class="flex flex-col gap-3 rounded-xl border p-3.5 transition-colors"
          :class="s.done ? 'border-ok/25 bg-ok-soft/60' : 'border-line bg-surface-2/60'"
        >
          <div class="flex items-start gap-2.5">
            <span class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full" :class="s.done ? 'bg-ok text-bg' : 'border border-line-strong text-transparent'">
              <Check class="size-3" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <p class="text-sm font-medium" :class="s.done ? 'text-muted line-through decoration-ok/50' : 'text-fg'">{{ s.title }}</p>
              <p v-if="!s.done" class="mt-1 text-xs leading-relaxed text-subtle">{{ s.why }}</p>
            </div>
          </div>
          <Button v-if="!s.done" size="sm" variant="soft" class="mt-auto self-start" @click="s.run">{{ s.cta }}</Button>
        </li>
      </ul>
    </div>
  </section>
</template>
