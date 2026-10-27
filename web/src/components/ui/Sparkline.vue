<script setup lang="ts">
import { computed, useId } from 'vue'

const props = withDefaults(
  defineProps<{
    values: (number | null | undefined)[]
    width?: number
    height?: number
    color?: string
    fill?: boolean
    strokeWidth?: number
    min?: number
    max?: number
    label?: string
    /** draw a dot on the latest value */
    dot?: boolean
  }>(),
  { width: 120, height: 32, color: 'var(--accent)', fill: true, strokeWidth: 1.75, dot: true },
)

const gid = `spark-${useId()}`
const PAD = 3

interface Pt {
  x: number
  y: number
}

const geometry = computed(() => {
  const vals = props.values
  const nums = vals.filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
  if (nums.length < 2) return { segments: [] as Pt[][], last: null as Pt | null }
  let lo = props.min ?? Math.min(...nums)
  let hi = props.max ?? Math.max(...nums)
  if (hi - lo < 1e-9) {
    // flat line: centre it instead of dividing by zero
    lo -= 1
    hi += 1
  } else if (props.min === undefined && props.max === undefined) {
    const pad = (hi - lo) * 0.08
    lo -= pad
    hi += pad
  }
  const n = vals.length
  const w = props.width
  const h = props.height
  const segments: Pt[][] = []
  let cur: Pt[] = []
  let last: Pt | null = null
  vals.forEach((v, i) => {
    if (typeof v !== 'number' || !Number.isFinite(v)) {
      if (cur.length) segments.push(cur)
      cur = []
      return
    }
    const p = { x: (i / (n - 1)) * (w - 2 * PAD) + PAD, y: h - PAD - ((v - lo) / (hi - lo)) * (h - 2 * PAD) }
    cur.push(p)
    last = p
  })
  if (cur.length) segments.push(cur)
  return { segments, last }
})

const linePath = computed(() =>
  geometry.value.segments
    .filter((s) => s.length > 1)
    .map((s) => s.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' '))
    .join(' '),
)
const areaPath = computed(() =>
  geometry.value.segments
    .filter((s) => s.length > 1)
    .map((s) => {
      const base = props.height - PAD
      return `M${s[0]!.x.toFixed(1)} ${base} ${s.map((p) => `L${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')} L${s[s.length - 1]!.x.toFixed(1)} ${base} Z`
    })
    .join(' '),
)
</script>

<template>
  <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="label ?? 'trend'" class="block overflow-visible">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.32" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <template v-if="linePath">
      <path v-if="fill" :d="areaPath" :fill="`url(#${gid})`" />
      <path :d="linePath" fill="none" :stroke="color" :stroke-width="strokeWidth" stroke-linecap="round" stroke-linejoin="round" />
      <circle v-if="dot && geometry.last" :cx="geometry.last.x" :cy="geometry.last.y" r="2.6" :fill="color" />
    </template>
    <line v-else :x1="PAD" :x2="width - PAD" :y1="height / 2" :y2="height / 2" stroke="var(--line-strong)" stroke-dasharray="3 4" />
  </svg>
</template>
