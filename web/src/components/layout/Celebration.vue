<script setup lang="ts">
import { ExternalLink, PartyPopper } from 'lucide-vue-next'
import { onBeforeUnmount, ref, watch } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { playBlockChime } from '@/lib/sound'
import { useSettings } from '@/stores/settings'
import { useUi } from '@/stores/ui'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'

const ui = useUi()
const settings = useSettings()
const fmt = useFmt()
const canvas = ref<HTMLCanvasElement | null>(null)
const open = ref(false)
let raf = 0

watch(
  () => ui.celebration,
  (c) => {
    open.value = !!c
    if (c && settings.data?.ui.sound_on_block) playBlockChime()
    if (c && !settings.data?.ui.reduce_motion) requestAnimationFrame(() => confetti())
  },
)
watch(open, (v) => {
  if (!v) {
    ui.celebration = null
    cancelAnimationFrame(raf)
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
  const colors = ['#F7931A', '#FFD27A', '#34d399', '#60a5fa', '#a78bfa', '#f472b6']
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
    else ctx.clearRect(0, 0, w, h)
  }
  raf = requestAnimationFrame(frame)
}
</script>

<template>
  <canvas ref="canvas" class="pointer-events-none fixed inset-0 z-[90]" :class="!open && 'hidden'" aria-hidden="true" />
  <Dialog v-model:open="open" title="You found a block" hide-title size="md" class="z-[95] text-center">
    <div v-if="ui.celebration" class="flex flex-col items-center gap-4 py-6" data-testid="celebration">
      <div class="grid size-20 place-items-center rounded-3xl bg-accent-soft text-accent-text"><PartyPopper class="size-10" aria-hidden="true" /></div>
      <h2 class="text-gradient-accent text-3xl font-bold tracking-tight">You found a block!</h2>
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
