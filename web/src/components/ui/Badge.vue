<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'

export type Tone = 'neutral' | 'ok' | 'warn' | 'bad' | 'info' | 'accent' | 'violet'

const props = withDefaults(
  defineProps<{
    tone?: Tone
    dot?: boolean
    size?: 'sm' | 'md'
    class?: HTMLAttributes['class']
  }>(),
  { tone: 'neutral', size: 'md' },
)

const tones: Record<Tone, string> = {
  neutral: 'bg-surface-3 text-muted border-line',
  ok: 'bg-ok-soft text-ok border-ok/25',
  warn: 'bg-warn-soft text-warn border-warn/25',
  bad: 'bg-bad-soft text-bad border-bad/25',
  info: 'bg-info-soft text-info border-info/25',
  accent: 'bg-accent-soft text-accent-text border-accent-line',
  violet: 'bg-[color-mix(in_oklab,var(--violet)_15%,transparent)] text-violet border-violet/25',
}
const dots: Record<Tone, string> = {
  neutral: 'bg-subtle',
  ok: 'bg-ok',
  warn: 'bg-warn',
  bad: 'bg-bad',
  info: 'bg-info',
  accent: 'bg-accent',
  violet: 'bg-violet',
}
const classes = computed(() =>
  cn(
    'inline-flex items-center gap-1.5 rounded-full border font-medium leading-none whitespace-nowrap',
    props.size === 'sm' ? 'px-2 py-1 text-[11px]' : 'px-2.5 py-1.5 text-xs',
    tones[props.tone],
    props.class,
  ),
)
</script>

<template>
  <span :class="classes">
    <span v-if="dot" :class="cn('size-1.5 rounded-full', dots[tone])" aria-hidden="true" />
    <slot />
  </span>
</template>
