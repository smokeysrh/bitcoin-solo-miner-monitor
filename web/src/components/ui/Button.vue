<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import { cva } from 'class-variance-authority'
import { Loader2 } from 'lucide-vue-next'
import { cn } from '@/lib/cn'

const variants = cva(
  'inline-flex items-center justify-center gap-2 rounded-xl font-medium whitespace-nowrap select-none ' +
    'transition-[background-color,border-color,color,transform,filter] duration-150 active:translate-y-px ' +
    'disabled:opacity-50 disabled:pointer-events-none aria-busy:cursor-progress',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-accent-fg glow-accent hover:brightness-110',
        secondary: 'bg-surface-3 text-fg border border-line hover:border-line-strong hover:bg-surface-2',
        outline: 'border border-line-strong text-fg hover:bg-surface-3',
        ghost: 'text-muted hover:text-fg hover:bg-surface-3',
        soft: 'bg-accent-soft text-accent-text border border-accent-line hover:brightness-125',
        danger: 'bg-bad-soft text-bad border border-bad/35 hover:brightness-125',
      },
      size: {
        xs: 'h-7 px-2.5 text-xs rounded-lg',
        sm: 'h-8 px-3 text-[13px]',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
        icon: 'h-9 w-9',
        iconSm: 'h-8 w-8 rounded-lg',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'soft' | 'danger'
type Size = 'xs' | 'sm' | 'md' | 'lg' | 'icon' | 'iconSm'

const props = withDefaults(
  defineProps<{
    variant?: Variant
    size?: Size
    loading?: boolean
    disabled?: boolean
    type?: 'button' | 'submit' | 'reset'
    to?: RouteLocationRaw
    href?: string
    class?: HTMLAttributes['class']
  }>(),
  { variant: 'secondary', size: 'md', type: 'button' },
)

const classes = computed(() => cn(variants({ variant: props.variant, size: props.size }), props.class))
const tag = computed(() => (props.to ? RouterLink : props.href ? 'a' : 'button'))
</script>

<template>
  <component
    :is="tag"
    :to="to"
    :href="href"
    :type="!to && !href ? type : undefined"
    :disabled="!to && !href ? disabled || loading : undefined"
    :aria-busy="loading || undefined"
    :class="classes"
  >
    <Loader2 v-if="loading" class="size-4 animate-spin" aria-hidden="true" />
    <slot v-else name="icon" />
    <slot />
  </component>
</template>
