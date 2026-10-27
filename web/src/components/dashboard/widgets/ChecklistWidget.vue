<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { Check } from 'lucide-vue-next'
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
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
const hidden = useStorage('bsmm.checklistHidden', false)

onMounted(() => void insights.refresh())
watch(() => [live.deviceCount, live.network?.sources.length], () => void insights.refresh(true))

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
    why: 'So costs and break-even figures use your real rate.',
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
    why: 'A password stops anyone else on your network restarting your miners.',
    done: !insights.has('no-password') && live.deviceCount > 0,
    cta: 'Set password',
    run: () => void router.push('/settings/security'),
  },
])

const doneCount = computed(() => steps.value.filter((s) => s.done).length)
const visible = computed(() => insights.loaded && !hidden.value && doneCount.value < steps.value.length && session.canControl)
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
          <h2 class="text-base font-semibold text-fg">Get set up</h2>
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
