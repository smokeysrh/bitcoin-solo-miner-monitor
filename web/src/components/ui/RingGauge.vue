<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 0..1 */
    value: number | null
    size?: number
    stroke?: number
    tone?: 'accent' | 'ok' | 'warn' | 'bad' | 'info' | 'violet'
    label?: string
  }>(),
  { size: 72, stroke: 7, tone: 'accent' },
)

const color = computed(() => ({ accent: 'var(--accent)', ok: 'var(--ok)', warn: 'var(--warn)', bad: 'var(--bad)', info: 'var(--info)', violet: 'var(--violet)' })[props.tone])
const r = computed(() => (props.size - props.stroke) / 2)
const c = computed(() => 2 * Math.PI * r.value)
const v = computed(() => Math.min(1, Math.max(0, props.value ?? 0)))
</script>

<template>
  <div class="relative inline-grid place-items-center" :style="{ width: `${size}px`, height: `${size}px` }" :role="label ? 'img' : undefined" :aria-label="label">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="-rotate-90">
      <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" stroke="var(--line)" :stroke-width="stroke" />
      <circle
        v-if="value !== null"
        :cx="size / 2"
        :cy="size / 2"
        :r="r"
        fill="none"
        :stroke="color"
        :stroke-width="stroke"
        stroke-linecap="round"
        :stroke-dasharray="c"
        :stroke-dashoffset="c * (1 - v)"
        style="transition: stroke-dashoffset 0.6s cubic-bezier(0.2, 0.8, 0.2, 1)"
      />
    </svg>
    <div class="absolute inset-0 grid place-items-center text-center"><slot /></div>
  </div>
</template>
