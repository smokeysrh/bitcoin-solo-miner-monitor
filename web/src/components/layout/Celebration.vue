<script setup lang="ts">
import { ExternalLink, PartyPopper } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { HASHLING_MOMENTS } from '@/lib/hashlingText'
import { prefersReducedMotion } from '@/lib/motion'
import { playBlockChime } from '@/lib/sound'
import { cssVar } from '@/lib/theme'
import { useHashling } from '@/stores/hashling'
import { useSettings } from '@/stores/settings'
import { useUi } from '@/stores/ui'
import HashlingArt from '@/components/brand/HashlingArt.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'

/** The kit's six chart colours (read at draw time: a canvas cannot use var()), and the kit orange if the stylesheet is missing. */
const CONFETTI_TOKENS = ['--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5', '--chart-6']
const CONFETTI_FALLBACK = '#f7931a'

const ui = useUi()
const settings = useSettings()
const hashling = useHashling()
const fmt = useFmt()
const canvas = ref<HTMLCanvasElement | null>(null)
const open = ref(false)
/** A confetti burst is running. The canvas shows for it with or without the dialog (the wall display has none). */
const bursting = ref(false)
let raf = 0

/** The device setting or the in-app switch asks for stillness: no confetti. Read per block, like the Hashling pop-up. */
const still = (): boolean => (settings.data?.ui.reduce_motion ?? false) || prefersReducedMotion()

/** Hashling's found-block pose and line, for a block the chain confirmed (it carries a hash). A miner's own report has none. */
const hashlingBlock = computed(() => hashling.enabled && !!ui.celebration?.hash)

watch(
  () => ui.celebration,
  (c) => {
    if (c && settings.data?.ui.sound_on_block) playBlockChime()
    // On the wall display nobody is there to press Close, so Hashling's own pop-up carries a confirmed block and closes itself.
    // The confetti still plays there.
    const onWall = !!c?.hash && hashling.enabled && hashling.surface === 'wall'
    if (onWall) ui.celebration = null
    else open.value = !!c
    if (c && !still()) requestAnimationFrame(() => confetti())
  },
)
watch(open, (v) => {
  if (!v) {
    ui.celebration = null
    cancelAnimationFrame(raf)
    bursting.value = false
  }
})
onBeforeUnmount(() => cancelAnimationFrame(raf))

interface Piece {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  rot: number
  vr: number
  color: string
}

function confetti(): void {
  const el = canvas.value
  if (!el) return
  const ctx = el.getContext('2d')
  if (!ctx) return
  const dpr = window.devicePixelRatio || 1
  const w = (el.width = window.innerWidth * dpr)
  const h = (el.height = window.innerHeight * dpr)
  cancelAnimationFrame(raf)
  bursting.value = true
  const colors = CONFETTI_TOKENS.map((token) => cssVar(token, CONFETTI_FALLBACK))
  const pieces: Piece[] = Array.from({ length: 220 }, () => ({
    x: w / 2 + (Math.random() - 0.5) * w * 0.25,
    y: h * 0.35,
    vx: (Math.random() - 0.5) * 16 * dpr,
    vy: (-Math.random() * 14 - 4) * dpr,
    r: (4 + Math.random() * 6) * dpr,
    rot: Math.random() * Math.PI,
    vr: (Math.random() - 0.5) * 0.4,
    color: colors[Math.floor(Math.random() * colors.length)]!,
  }))
  const start = performance.now()
  const frame = (now: number): void => {
    const elapsed = now - start
    ctx.clearRect(0, 0, w, h)
    for (const p of pieces) {
      p.vy += 0.32 * dpr
      p.vx *= 0.995
      p.x += p.vx
      p.y += p.vy
      p.rot += p.vr
      ctx.save()
      ctx.translate(p.x, p.y)
      ctx.rotate(p.rot)
      ctx.fillStyle = p.color
      ctx.globalAlpha = Math.max(0, 1 - elapsed / 6500)
      ctx.fillRect(-p.r / 2, -p.r / 4, p.r, p.r / 2)
      ctx.restore()
    }
    if (elapsed < 6500) raf = requestAnimationFrame(frame)
    else {
      ctx.clearRect(0, 0, w, h)
      bursting.value = false
    }
  }
  raf = requestAnimationFrame(frame)
}
</script>

<template>
  <canvas ref="canvas" class="pointer-events-none fixed inset-0 z-[90]" :class="!open && !bursting && 'hidden'" aria-hidden="true" />
  <Dialog v-model:open="open" title="You found a block" hide-title size="md" class="z-[95] text-center">
    <div v-if="ui.celebration" class="flex flex-col items-center gap-4 py-6" data-testid="celebration">
      <HashlingArt v-if="hashlingBlock" pose="found-block" :scale="3" />
      <div v-else class="grid size-20 place-items-center rounded-3xl bg-accent-soft text-accent-text"><PartyPopper class="size-10" aria-hidden="true" /></div>
      <h2 class="text-gradient-accent text-3xl font-bold tracking-tight">You found a block!</h2>
      <p v-if="hashlingBlock" class="max-w-sm text-sm font-medium text-fg">{{ HASHLING_MOMENTS.M13.line }}</p>
      <p class="max-w-sm text-sm leading-relaxed text-muted">
        Against astronomical odds, one of your miners just solved block
        <b class="text-fg">{{ fmt.formatNumber(ui.celebration.height) }}</b>.
        <template v-if="ui.celebration.reward_sats">The reward is {{ fmt.formatBtc((ui.celebration.reward_sats ?? 0) / 1e8, 4) }}.</template>
      </p>
      <code class="max-w-full truncate rounded-lg bg-surface-3 px-3 py-1.5 text-xs text-muted">{{ ui.celebration.hash }}</code>
      <div class="mt-2 flex flex-wrap justify-center gap-2">
        <Button variant="primary" :href="`https://mempool.space/block/${ui.celebration?.hash}`" target="_blank" rel="noopener">
          <template #icon><ExternalLink class="size-4" /></template>
          See it on mempool.space
        </Button>
        <Button variant="ghost" @click="open = false">Close</Button>
      </div>
    </div>
  </Dialog>
</template>
