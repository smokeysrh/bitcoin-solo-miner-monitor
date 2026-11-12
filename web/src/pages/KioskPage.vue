<script setup lang="ts">
import { useEventListener } from '@vueuse/core'
import { ChevronLeft, ChevronRight, Lock, LockOpen, Maximize, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import KioskMinerTile from '@/components/miners/KioskMinerTile.vue'
import LiveBadge from '@/components/layout/LiveBadge.vue'
import KioskNetworkPanel from '@/components/layout/KioskNetworkPanel.vue'
import { useFmt } from '@/composables/useFmt'
import { useKioskLayout } from '@/composables/useKioskLayout'
import { useNowSec } from '@/composables/useNowSec'
import { useOddsHeadline } from '@/composables/useOddsHeadline'
import { describeError } from '@/lib/api'
import { formatHorizonChance, ODDS_HEADLINES } from '@/lib/oddsHeadline'
import type { OddsHeadline } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const live = useLive()
const fmt = useFmt()
const router = useRouter()
const settings = useSettings()
const session = useSession()
const toasts = useToasts()
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
const oddsChoice = useOddsHeadline()
const oddsHeadline = oddsChoice.current
const oddsOthers = computed(() => ODDS_HEADLINES.filter((h) => h.key !== oddsHeadline.value.key))
const { chartHeight, tileGrid, tileCell } = useKioskLayout(() => sorted.value.length)

/** Tapping a time frame on the panel saves it as the wall display's headline, the same setting as Settings → Appearance. */
async function chooseHeadline(key: OddsHeadline): Promise<void> {
  restart() // a tap should not be followed straight away by the next panel
  try {
    await oddsChoice.choose(key)
  } catch (e) {
    toasts.error('Could not save that', describeError(e))
  }
}
</script>

<template>
  <main class="relative flex min-h-dvh flex-col overflow-clip bg-bg p-[max(1rem,2vmin)]" :class="!chrome && 'cursor-none'" data-testid="kiosk">
    <!-- The live pill sits in the very top-left corner and stays visible so a stale or lost connection is always seen. The wall display has no title; only the buttons fade with the other chrome. -->
    <div class="absolute top-3 left-3 z-10" data-testid="kiosk-live-pill"><LiveBadge large /></div>
    <div class="pointer-events-none absolute -top-40 -left-32 size-[40rem] rounded-full bg-accent/10 blur-3xl light:hidden" aria-hidden="true" />

    <header class="relative flex items-center justify-end">
      <div class="flex items-center gap-2 transition-opacity duration-500" :class="chrome ? 'opacity-100' : 'opacity-0'">
        <button class="grid size-10 place-items-center rounded-xl text-muted hover:bg-surface-3 hover:text-fg" aria-label="Full screen (F)" @click="fullscreen"><Maximize class="size-5" /></button>
        <button class="grid size-10 place-items-center rounded-xl text-muted hover:bg-surface-3 hover:text-fg" aria-label="Leave the wall display" @click="router.push('/')"><X class="size-5" /></button>
      </div>
    </header>
    <p v-if="cfg.show_clock" class="tnum absolute top-[max(1rem,2vmin)] right-1/2 translate-x-1/2 text-lg font-medium text-subtle" aria-hidden="true">{{ clock }}</p>

    <Transition name="panel" mode="out-in">
      <section :key="panel" class="relative flex flex-1 flex-col justify-center py-[max(1rem,2vmin)]" :aria-label="panel">
        <template v-if="panel === 'overview'">
          <p class="eyebrow text-center text-[length:max(0.875rem,2.4vmin)] leading-[1.25]">Fleet hashrate</p>
          <p class="mt-[1.5vmin] flex items-baseline justify-center gap-[2vmin]">
            <span class="text-gradient-accent tnum text-[length:clamp(4rem,min(18vw,28vmin),48rem)] leading-[1.2] font-bold tracking-tight">{{ hash.value }}</span>
            <span class="text-[length:clamp(1.5rem,min(5vw,8vmin),12rem)] font-medium text-subtle">{{ hash.unit }}</span>
          </p>
          <div class="mt-[2vmin] w-full" :style="{ height: `${chartHeight}px` }"><HistoryChart :metrics="['hashrate_hs']" range="6h" :height="chartHeight" minimal /></div>
          <dl class="mt-[3vmin] grid w-full grid-cols-2 gap-[2.5vmin] text-center landscape:grid-cols-4">
            <div><dt class="text-[length:max(0.875rem,2.4vmin)] text-subtle">Miners online</dt><dd class="tnum mt-1 text-[length:max(2.25rem,6vmin)] font-semibold text-fg">{{ s?.devices_online ?? 0 }}<span class="text-[0.55em] text-subtle"> / {{ s?.devices_total ?? 0 }}</span></dd></div>
            <div><dt class="text-[length:max(0.875rem,2.4vmin)] text-subtle">Power</dt><dd class="tnum mt-1 text-[length:max(2.25rem,6vmin)] font-semibold text-fg">{{ fmt.formatPower(s?.power_w) }}</dd></div>
            <div><dt class="text-[length:max(0.875rem,2.4vmin)] text-subtle">Efficiency</dt><dd class="tnum mt-1 text-[length:max(2.25rem,6vmin)] font-semibold text-fg">{{ s?.efficiency_j_th ? s.efficiency_j_th.toFixed(1) : '–' }}<span class="text-[0.55em] text-subtle"> J/TH</span></dd></div>
            <div><dt class="text-[length:max(0.875rem,2.4vmin)] text-subtle">Hottest chip</dt><dd class="tnum mt-1 text-[length:max(2.25rem,6vmin)] font-semibold text-fg">{{ fmt.temp(s?.temp_max_c) }}</dd></div>
          </dl>
        </template>

        <template v-else-if="panel === 'miners'">
          <div class="grid w-full" :style="tileGrid">
            <KioskMinerTile v-for="(d, i) in sorted" :key="d.id" :device="d" :style="tileCell(i)" class="pointer-events-none" />
          </div>
        </template>

        <template v-else-if="panel === 'odds'">
          <p class="eyebrow text-center text-[clamp(0.875rem,1.3vw,4rem)] leading-normal" data-testid="kiosk-odds-eyebrow">Chance of finding a block</p>
          <template v-if="odds">
            <p class="text-gradient-accent tnum mt-4 text-center text-[clamp(3rem,12vw,30rem)] leading-none font-bold tracking-tight text-balance [overflow-wrap:anywhere]" data-testid="kiosk-odds-headline">{{ formatHorizonChance(odds.horizons[oddsHeadline.key]?.probability) }}</p>
            <p class="mt-3 text-center text-[clamp(1.5rem,2.6vw,8rem)] leading-snug text-muted" data-testid="kiosk-odds-headline-label">{{ oddsHeadline.sentence }}</p>
            <dl class="mt-[clamp(1rem,3vh,5rem)] grid w-full grid-cols-2 gap-x-4 gap-y-6 text-center lg:landscape:grid-cols-5" data-testid="kiosk-odds-others">
              <div v-for="h in oddsOthers" :key="h.key"><dt class="text-[clamp(0.875rem,1.3vw,4rem)] text-subtle">{{ h.label }}</dt><dd class="tnum mt-1 text-[clamp(1.5rem,2.2vw,8rem)] font-semibold text-fg [overflow-wrap:anywhere]">{{ formatHorizonChance(odds.horizons[h.key]?.probability) }}</dd></div>
            </dl>
            <div
              v-if="session.canAdmin"
              role="group"
              aria-label="Odds time frame"
              class="mt-[clamp(1.5rem,4vh,6rem)] flex flex-wrap justify-center gap-[clamp(0.5rem,1vw,2rem)] transition-opacity duration-500"
              :class="chrome ? 'opacity-100' : 'opacity-0'"
              :inert="!chrome"
              data-testid="kiosk-odds-headline-choice"
            >
              <button
                v-for="h in ODDS_HEADLINES"
                :key="h.key"
                type="button"
                class="min-h-11 rounded-full border px-[clamp(0.75rem,1.6vw,3rem)] py-[clamp(0.25rem,0.5vw,1rem)] text-[clamp(0.875rem,1.3vw,4rem)] font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent"
                :class="h.key === oddsHeadline.key ? 'border-accent bg-accent/15 text-accent-text' : 'border-line text-muted hover:text-fg'"
                :aria-pressed="h.key === oddsHeadline.key"
                :data-testid="`kiosk-odds-choice-${h.key}`"
                @click="chooseHeadline(h.key)"
              >{{ h.label }}</button>
            </div>
          </template>
          <p v-else class="mt-6 text-center text-xl text-muted">Waiting for network data…</p>
        </template>

        <template v-else-if="panel === 'network'">
          <KioskNetworkPanel :net="net" />
        </template>

        <template v-else>
          <!-- fills the screen: 12rem is the page padding, header, section padding and footer around this panel -->
          <div class="flex h-[calc(100dvh_-_12rem)] w-full flex-col"><HistoryChart class="min-h-0 flex-1" :metrics="['hashrate_hs', 'power_w']" range="24h" :height="240" kiosk /></div>
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
