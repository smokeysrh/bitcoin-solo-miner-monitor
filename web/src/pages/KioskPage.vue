<script setup lang="ts">
import { useEventListener } from '@vueuse/core'
import { ChevronLeft, ChevronRight, Lock, LockOpen, Maximize, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import MinerTile from '@/components/miners/MinerTile.vue'
import LiveBadge from '@/components/layout/LiveBadge.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { useLive } from '@/stores/live'
import { useSettings } from '@/stores/settings'

const live = useLive()
const fmt = useFmt()
const router = useRouter()
const settings = useSettings()
const now = useNowSec()

const ALL = ['overview', 'miners', 'odds', 'network', 'chart'] as const
type Panel = (typeof ALL)[number]
const cfg = computed(() => settings.data?.ui.kiosk ?? { rotate_s: 15, panels: [...ALL] as string[], show_clock: true })
const panels = computed<Panel[]>(() => {
  const p = cfg.value.panels.filter((x): x is Panel => (ALL as readonly string[]).includes(x))
  return p.length ? p : [...ALL]
})
const PANEL_LABEL: Record<Panel, string> = { overview: 'Overview', miners: 'Miners', odds: 'Odds', network: 'Network', chart: 'Chart' }
// Big, plain buttons for a display read from across a room; they grow with the screen. Orange is reserved for the lock.
const BUTTON =
  'inline-flex min-h-[clamp(2.75rem,4vw,6rem)] min-w-11 items-center justify-center gap-[0.4em] rounded-2xl border-2 px-[1.1em] text-[clamp(1.125rem,1.5vw,4rem)] font-semibold whitespace-nowrap transition-colors'
const BUTTON_IDLE = `${BUTTON} border-line-strong bg-surface-1 text-muted hover:bg-surface-2 hover:text-fg`
const BUTTON_CURRENT = `${BUTTON} border-fg bg-surface-3 text-fg`
const idx = ref(0)
const panel = computed(() => panels.value[idx.value % panels.value.length]!)
const chrome = ref(true)
/** Locked: stay on the current panel. Choosing a panel never changes this; only the lock button does. */
const locked = ref(false)
/** Spoken by the polite live region for choices the viewer makes, never for automatic rotation. */
const announcement = ref('')
let rotate: ReturnType<typeof setInterval> | null = null
let hide: ReturnType<typeof setTimeout> | null = null
let lock: { release: () => Promise<void> } | null = null

/** The one place the rotation timer is owned: stop any running one, and start a fresh full period unless locked. */
function restart(): void {
  if (rotate) clearInterval(rotate)
  rotate = null
  if (locked.value) return
  rotate = setInterval(() => (idx.value = (idx.value + 1) % panels.value.length), Math.max(5, cfg.value.rotate_s) * 1000)
}
function poke(): void {
  chrome.value = true
  if (hide) clearTimeout(hide)
  hide = setTimeout(() => (chrome.value = false), 4000)
}
function jump(n: number): void {
  idx.value = (n + panels.value.length) % panels.value.length
  announcement.value = `Showing ${PANEL_LABEL[panel.value]}`
  restart()
}
function toggleLock(): void {
  locked.value = !locked.value
  announcement.value = locked.value ? `Locked on ${PANEL_LABEL[panel.value]}. The display stays on this panel.` : 'Rotation resumed.'
  restart()
}
async function fullscreen(): Promise<void> {
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
    else await document.documentElement.requestFullscreen()
  } catch {
    /* some browsers refuse without a gesture */
  }
}

useEventListener(window, 'mousemove', poke)
useEventListener(window, 'touchstart', poke)
useEventListener(window, 'keydown', (e: KeyboardEvent) => {
  // Space advances one panel (as before; the lock is not changed). On a focused button it is that button's own key.
  const onControl = e.target instanceof Element && e.target.closest('button, a, input, select, textarea') !== null
  if (e.key === 'ArrowRight') jump(idx.value + 1)
  else if (e.key === ' ' && !onControl) {
    e.preventDefault()
    jump(idx.value + 1)
  } else if (e.key === 'ArrowLeft') jump(idx.value - 1)
  else if (e.key === 'f') void fullscreen()
  else if (e.key === 'Escape' && !document.fullscreenElement) void router.push('/')
  poke()
})

onMounted(async () => {
  restart()
  poke()
  try {
    lock = await (navigator as unknown as { wakeLock?: { request: (t: string) => Promise<{ release: () => Promise<void> }> } }).wakeLock?.request('screen') ?? null
  } catch {
    lock = null // needs a secure context; the display may sleep on plain http
  }
})
onBeforeUnmount(() => {
  if (rotate) clearInterval(rotate)
  rotate = null
  if (hide) clearTimeout(hide)
  void lock?.release()
})

const s = computed(() => live.summary)
const hash = computed(() => fmt.splitHash(s.value?.hashrate_hs))
const odds = computed(() => (live.odds?.available ? live.odds : null))
const net = computed(() => live.network)
const clock = computed(() => new Date(now.value * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
const sorted = computed(() => [...live.devices].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })).slice(0, 12))
</script>

<template>
  <main class="relative flex min-h-dvh flex-col overflow-clip bg-bg p-6 sm:p-10" :class="!chrome && 'cursor-none'" data-testid="kiosk">
    <!-- The live pill sits in the very top-left corner and stays visible so a stale or lost connection is always seen. The wall display has no title; only the buttons fade with the other chrome. -->
    <div class="absolute top-3 left-3 z-10" data-testid="kiosk-live-pill"><LiveBadge large /></div>
    <div class="pointer-events-none absolute -top-40 -left-32 size-[40rem] rounded-full bg-accent/10 blur-3xl light:hidden" aria-hidden="true" />

    <header class="relative flex items-center justify-end">
      <div class="flex items-center gap-2 transition-opacity duration-500" :class="chrome ? 'opacity-100' : 'opacity-0'">
        <button class="grid size-10 place-items-center rounded-xl text-muted hover:bg-surface-3 hover:text-fg" aria-label="Full screen (F)" @click="fullscreen"><Maximize class="size-5" /></button>
        <button class="grid size-10 place-items-center rounded-xl text-muted hover:bg-surface-3 hover:text-fg" aria-label="Leave the wall display" @click="router.push('/')"><X class="size-5" /></button>
      </div>
    </header>
    <p v-if="cfg.show_clock" class="tnum absolute top-6 right-1/2 translate-x-1/2 text-lg font-medium text-subtle sm:top-10" aria-hidden="true">{{ clock }}</p>

    <Transition name="panel" mode="out-in">
      <section :key="panel" class="relative flex flex-1 flex-col justify-center py-8" :aria-label="panel">
        <template v-if="panel === 'overview'">
          <p class="eyebrow text-center">Fleet hashrate</p>
          <p class="mt-4 flex items-baseline justify-center gap-4">
            <span class="text-gradient-accent tnum text-[clamp(4rem,16vw,12rem)] leading-none font-bold tracking-tight">{{ hash.value }}</span>
            <span class="text-[clamp(1.5rem,4vw,3rem)] font-medium text-subtle">{{ hash.unit }}</span>
          </p>
          <div class="mx-auto mt-6 h-40 w-full max-w-5xl"><HistoryChart :metrics="['hashrate_hs']" range="6h" :height="160" minimal /></div>
          <dl class="mx-auto mt-8 grid w-full max-w-5xl grid-cols-2 gap-6 text-center sm:grid-cols-4">
            <div><dt class="text-sm text-subtle">Miners online</dt><dd class="tnum mt-1 text-4xl font-semibold text-fg">{{ s?.devices_online ?? 0 }}<span class="text-xl text-subtle"> / {{ s?.devices_total ?? 0 }}</span></dd></div>
            <div><dt class="text-sm text-subtle">Power</dt><dd class="tnum mt-1 text-4xl font-semibold text-fg">{{ fmt.formatPower(s?.power_w) }}</dd></div>
            <div><dt class="text-sm text-subtle">Efficiency</dt><dd class="tnum mt-1 text-4xl font-semibold text-fg">{{ s?.efficiency_j_th ? s.efficiency_j_th.toFixed(1) : '–' }}<span class="text-xl text-subtle"> J/TH</span></dd></div>
            <div><dt class="text-sm text-subtle">Hottest chip</dt><dd class="tnum mt-1 text-4xl font-semibold text-fg">{{ fmt.temp(s?.temp_max_c) }}</dd></div>
          </dl>
        </template>

        <template v-else-if="panel === 'miners'">
          <div class="mx-auto grid w-full max-w-7xl gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <MinerTile v-for="d in sorted" :key="d.id" :device="d" class="pointer-events-none" />
          </div>
        </template>

        <template v-else-if="panel === 'odds'">
          <p class="eyebrow text-center">Chance of finding a block</p>
          <template v-if="odds">
            <p class="text-gradient-accent tnum mt-4 text-center text-[clamp(3rem,12vw,9rem)] leading-none font-bold tracking-tight">{{ fmt.formatOdds(odds.horizons.year.probability) }}</p>
            <p class="mt-3 text-center text-2xl text-muted">each year</p>
            <dl class="mx-auto mt-10 grid w-full max-w-4xl grid-cols-2 gap-6 text-center sm:grid-cols-4">
              <div v-for="[k, l] in [['ten_minutes', 'Next 10 minutes'], ['day', 'Today'], ['month', 'This month'], ['five_years', '5 years'], ['ten_years', '10 years']] as const" :key="k"><dt class="text-sm text-subtle">{{ l }}</dt><dd class="tnum mt-1 text-2xl font-semibold text-fg">{{ fmt.formatOdds(odds.horizons[k].probability) }}</dd></div>
            </dl>
          </template>
          <p v-else class="mt-6 text-center text-xl text-muted">Waiting for network data…</p>
        </template>

        <template v-else-if="panel === 'network'">
          <div class="mx-auto grid w-full max-w-5xl gap-8 text-center sm:grid-cols-3">
            <div><p class="eyebrow">Block height</p><p class="tnum mt-2 text-5xl font-bold text-fg">{{ fmt.formatNumber(net?.height) }}</p></div>
            <div><p class="eyebrow">Difficulty</p><p class="tnum mt-2 text-5xl font-bold text-fg">{{ fmt.formatDifficulty(net?.difficulty) }}</p></div>
            <div><p class="eyebrow">Bitcoin</p><p class="tnum mt-2 text-5xl font-bold text-fg">{{ net?.btc_price ? fmt.money(net.btc_price, 0) : '–' }}</p></div>
          </div>
          <div v-if="net?.epoch" class="mx-auto mt-12 w-full max-w-3xl"><div class="mb-2 flex justify-between text-sm text-muted"><span>Next difficulty change</span><span class="tnum">{{ fmt.formatNumber(net.epoch.blocks_remaining) }} blocks</span></div><ProgressBar :value="net.epoch.progress" tone="info" :height="12" label="Progress to the next adjustment" /></div>
          <div v-if="net?.halving" class="mx-auto mt-8 w-full max-w-3xl"><div class="mb-2 flex justify-between text-sm text-muted"><span>Next halving</span><span class="tnum">{{ fmt.formatNumber(net.halving.blocks_remaining) }} blocks</span></div><ProgressBar :value="net.halving.progress" tone="violet" :height="12" label="Progress to the next halving" /></div>
        </template>

        <template v-else>
          <div class="mx-auto w-full max-w-6xl"><HistoryChart :metrics="['hashrate_hs', 'power_w']" range="24h" :height="460" legend /></div>
        </template>
      </section>
    </Transition>

    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>
    <footer class="sticky bottom-0 z-10 flex flex-wrap items-center justify-center gap-[clamp(0.5rem,1vw,1.5rem)] bg-bg/90 pt-4 pb-[clamp(0.5rem,1vw,2rem)] transition-opacity duration-500" :class="chrome ? 'opacity-100' : 'opacity-0'" @focusin="poke">
      <button type="button" :class="BUTTON_IDLE" aria-label="Previous panel" @click="jump(idx - 1)"><ChevronLeft class="size-[1.25em]" aria-hidden="true" />Previous</button>
      <button v-for="(p, n) in panels" :key="p" type="button" :class="n === idx % panels.length ? BUTTON_CURRENT : BUTTON_IDLE" :aria-current="n === idx % panels.length ? 'true' : undefined" :aria-label="`Show ${p}`" @click="jump(n)">{{ PANEL_LABEL[p] }}</button>
      <button type="button" :class="BUTTON_IDLE" aria-label="Next panel" @click="jump(idx + 1)">Next<ChevronRight class="size-[1.25em]" aria-hidden="true" /></button>
      <button type="button" :class="[BUTTON, 'ml-[1em]', locked ? 'border-accent bg-accent text-accent-fg' : 'border-line-strong bg-surface-3 text-fg hover:bg-surface-2']" :aria-pressed="locked" aria-label="Lock on this panel" @click="toggleLock">
        <component :is="locked ? Lock : LockOpen" class="size-[1.25em]" aria-hidden="true" />Lock
      </button>
    </footer>
  </main>
</template>

<style scoped>
.panel-enter-active,
.panel-leave-active {
  transition:
    opacity 0.45s ease,
    transform 0.45s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.panel-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.panel-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
