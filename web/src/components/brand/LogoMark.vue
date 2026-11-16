<script setup lang="ts">
// The supplied HashHurdr symbol (the full-body Hashling), used exactly as drawn. It is pixel art on a 32 x 32 grid,
// so pass whole-number multiples of 32 for `size` to keep every pixel sharp. Pass alt="" when the name is written next to it.
//
// He blinks once a few seconds after the page loads and again whenever someone hovers him, with the kit's own blink
// frame: the same figure with his eyes closed, on the 52 x 44 pose grid, so it is laid over the symbol pixel for pixel.
// No loop, and nothing moves for reduced motion.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { BRAND_ASSETS, HASHLING_BLINK, HASHLING_GRID } from '@/lib/brand'
import { prefersReducedMotion } from '@/lib/motion'

const props = withDefaults(defineProps<{ size?: number; alt?: string }>(), { size: 32, alt: 'HashHurdr logo' })

const SYMBOL_GRID = 32
const AUTO_BLINK_AFTER_MS = 3_000
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
let autoTimer: ReturnType<typeof setTimeout> | null = null
let blinkTimer: ReturnType<typeof setTimeout> | null = null

function blink(): void {
  if (unit.value === 0 || blinking.value || prefersReducedMotion()) return
  blinking.value = true
  blinkTimer = setTimeout(() => {
    blinking.value = false
    blinkTimer = null
  }, BLINK_MS)
}

onMounted(() => {
  if (unit.value === 0 || prefersReducedMotion()) return
  autoTimer = setTimeout(() => {
    autoTimer = null
    blink()
  }, AUTO_BLINK_AFTER_MS)
})
onBeforeUnmount(() => {
  if (autoTimer) clearTimeout(autoTimer)
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
