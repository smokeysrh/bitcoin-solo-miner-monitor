<script setup lang="ts">
import { useEventListener } from '@vueuse/core'
import { Maximize, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import KioskMinerTile from '@/components/miners/KioskMinerTile.vue'
import LiveBadge from '@/components/layout/LiveBadge.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import { useFmt } from '@/composables/useFmt'
import { useKioskLayout } from '@/composables/useKioskLayout'
import { useNowSec } from '@/composables/useNowSec'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'

const live = useLive()
const fmt = useFmt()
const router = useRouter()
const settings = useSettings()
const session = useSession()
const now = useNowSec()

const ALL = ['overview', 'miners', 'odds', 'network', 'chart'] as const
type Panel = (typeof ALL)[number]
const cfg = computed(() => settings.data?.ui.kiosk ?? { rotate_s: 15, panels: [...ALL] as string[], show_clock: true })
const panels = computed<Panel[]>(() => {
  const p = cfg.value.panels.filter((x): x is Panel => (ALL as readonly string[]).includes(x))
  return p.length ? p : [...ALL]
})
const idx = ref(0)
const panel = computed(() => panels.value[idx.value % panels.value.length]!)
const chrome = ref(true)
let rotate: ReturnType<typeof setInterval> | null = null
let hide: ReturnType<typeof setTimeout> | null = null
let lock: { release: () => Promise<void> } | null = null

function restart(): void {
  if (rotate) clearInterval(rotate)
  rotate = setInterval(() => (idx.value = (idx.value + 1) % panels.value.length), Math.max(5, cfg.value.rotate_s) * 1000)
}
function poke(): void {
  chrome.value = true
  if (hide) clearTimeout(hide)
  hide = setTimeout(() => (chrome.value = false), 4000)
}
function jump(n: number): void {
  idx.value = (n + panels.value.length) % panels.value.length
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
  if (e.key === 'ArrowRight' || e.key === ' ') jump(idx.value + 1)
  else if (e.key === 'ArrowLeft') jump(idx.value - 1)
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
  if (hide) clearTimeout(hide)
  void lock?.release()
})

const s = computed(() => live.summary)
const hash = computed(() => fmt.splitHash(s.value?.hashrate_hs))
const odds = computed(() => (live.odds?.available ? live.odds : null))
const net = computed(() => live.network)
const clock = computed(() => new Date(now.value * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
const sorted = computed(() => [...live.devices].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })).slice(0, 12))
const { chartHeight, tileGrid, tileCell } = useKioskLayout(() => sorted.value.length)
</script>

<template>
  <main class="relative flex min-h-dvh flex-col overflow-hidden bg-bg p-[max(1rem,2vmin)]" :class="!chrome && 'cursor-none'" data-testid="kiosk">
    <div class="pointer-events-none absolute -top-40 -left-32 size-[40rem] rounded-full bg-accent/10 blur-3xl light:hidden" aria-hidden="true" />

    <header class="relative flex items-center justify-between transition-opacity duration-500" :class="chrome ? 'opacity-100' : 'opacity-0'">
      <div class="flex items-center gap-4">
        <h1 class="text-lg font-semibold tracking-tight text-fg">{{ session.meta?.instance_name ?? 'Solo Miner Monitor' }}</h1>
        <LiveBadge />
      </div>
      <div class="flex items-center gap-2">
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

    <footer class="relative flex items-center justify-center gap-2 transition-opacity duration-500" :class="chrome ? 'opacity-100' : 'opacity-0'">
      <button v-for="(p, n) in panels" :key="p" class="h-2 rounded-full transition-all" :class="n === idx % panels.length ? 'w-8 bg-accent' : 'w-2 bg-line-strong hover:bg-subtle'" :aria-label="`Show ${p}`" @click="jump(n)" />
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
