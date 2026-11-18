<script setup lang="ts">
// The supplied HashHurdr symbol (the full-body Hashling), used exactly as drawn. It is pixel art on a 32 x 32 grid,
// so pass whole-number multiples of 32 for `size` to keep every pixel sharp. Pass alt="" when the name is written next to it.
//
// He blinks every few seconds while idle (a little random jitter, so it never looks mechanical), whenever someone hovers
// him, and whenever `refreshSignal` changes (the sidebar passes the time the live stats last refreshed: I Dream of
// Genie). The blink is the kit's own frame: the same figure with his eyes closed, on the 52 x 44 pose grid, so it is
// laid over the symbol pixel for pixel. Any blink restarts the idle wait, so blinks never bunch up. Nothing moves for
// reduced motion.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BRAND_ASSETS, HASHLING_BLINK, HASHLING_GRID } from '@/lib/brand'
import { prefersReducedMotion } from '@/lib/motion'

const props = withDefaults(defineProps<{ size?: number; alt?: string; refreshSignal?: number }>(), { size: 32, alt: 'HashHurdr logo', refreshSignal: 0 })

const SYMBOL_GRID = 32
/** The idle blink comes this long after the last blink, plus up to IDLE_BLINK_JITTER_MS more at random. */
const IDLE_BLINK_EVERY_MS = 4_000
const IDLE_BLINK_JITTER_MS = 2_000
const BLINK_MS = 200
// Where the symbol's figure sits on each grid (its top-left pixel), so the blink frame lines up exactly over it.
const SYMBOL_ORIGIN = { x: 1, y: 1 } as const
const POSE_ORIGIN = { x: 11, y: 13 } as const

/** Pixels per grid unit, when that is a whole number (otherwise there is no blink: half pixels would blur). */
const unit = computed(() => (props.size % SYMBOL_GRID === 0 ? props.size / SYMBOL_GRID : 0))
const frame = computed(() => ({
  width: HASHLING_GRID.width * unit.value,
  height: HASHLING_GRID.height * unit.value,
  left: (SYMBOL_ORIGIN.x - POSE_ORIGIN.x) * unit.value,
  top: (SYMBOL_ORIGIN.y - POSE_ORIGIN.y) * unit.value,
}))

const blinking = ref(false)
let idleTimer: ReturnType<typeof setTimeout> | null = null
let blinkTimer: ReturnType<typeof setTimeout> | null = null

/** Wait for the next idle blink; a wait already running is replaced. Never runs for a still logo. */
function scheduleIdleBlink(): void {
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = null
  if (unit.value === 0 || prefersReducedMotion()) return
  idleTimer = setTimeout(() => {
    idleTimer = null
    blink()
    if (!idleTimer) scheduleIdleBlink() // a refused blink (one already running) must not end the loop
  }, IDLE_BLINK_EVERY_MS + Math.random() * IDLE_BLINK_JITTER_MS)
}

function blink(): void {
  if (unit.value === 0 || blinking.value || prefersReducedMotion()) return
  blinking.value = true
  scheduleIdleBlink()
  blinkTimer = setTimeout(() => {
    blinking.value = false
    blinkTimer = null
  }, BLINK_MS)
}

// Fresh stats arrived. The first value after load (from 0, "nothing yet") is the page loading, not a refresh.
watch(
  () => props.refreshSignal,
  (now, before) => {
    if (before && now !== before) blink()
  },
)

onMounted(scheduleIdleBlink)
onBeforeUnmount(() => {
  if (idleTimer) clearTimeout(idleTimer)
  if (blinkTimer) clearTimeout(blinkTimer)
})
</script>

<template>
  <span class="relative inline-flex shrink-0 leading-none" :style="{ width: `${size}px`, height: `${size}px` }" data-testid="logo-mark" :data-blinking="blinking ? 'true' : 'false'" @mouseenter="blink">
    <img :src="BRAND_ASSETS.symbol" :width="size" :height="size" :alt="alt" class="block shrink-0" :style="{ visibility: blinking ? 'hidden' : 'visible' }" />
    <img
      v-if="unit > 0"
      :src="HASHLING_BLINK"
      :width="frame.width"
      :height="frame.height"
      alt=""
      aria-hidden="true"
      class="hashling-art pointer-events-none absolute max-w-none"
      :style="{ left: `${frame.left}px`, top: `${frame.top}px`, visibility: blinking ? 'visible' : 'hidden' }"
      data-testid="logo-blink-frame"
    />
  </span>
</template>
