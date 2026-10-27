<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 0..1 */
    value: number | null
    tone?: 'accent' | 'ok' | 'warn' | 'bad' | 'info' | 'violet'
    height?: number
    label?: string
  }>(),
  { tone: 'accent', height: 8 },
)
const color = computed(() => ({ accent: 'var(--accent)', ok: 'var(--ok)', warn: 'var(--warn)', bad: 'var(--bad)', info: 'var(--info)', violet: 'var(--violet)' })[props.tone])
const pct = computed(() => Math.min(100, Math.max(0, (props.value ?? 0) * 100)))
</script>

<template>
  <div
    class="w-full overflow-hidden rounded-full bg-surface-3"
    :style="{ height: `${height}px` }"
    role="progressbar"
    :aria-valuenow="Math.round(pct)"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-label="label"
  >
    <div
      class="h-full rounded-full transition-[width] duration-700 ease-out"
      :style="{ width: `${pct}%`, background: `linear-gradient(90deg, color-mix(in oklab, ${color} 70%, transparent), ${color})` }"
    />
  </div>
</template>
