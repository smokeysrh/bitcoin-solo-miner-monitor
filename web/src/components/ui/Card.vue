<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'

withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
    padded?: boolean
    hover?: boolean
    as?: string
    class?: HTMLAttributes['class']
  }>(),
  { padded: true, as: 'section' },
)
</script>

<template>
  <component :is="as" :class="cn('card', padded && 'card-pad', hover && 'card-hover', $props.class)">
    <header v-if="title || $slots.actions || $slots.title" class="mb-3 flex items-start justify-between gap-3">
      <div class="min-w-0">
        <slot name="title">
          <h2 class="truncate text-sm font-semibold text-fg">{{ title }}</h2>
        </slot>
        <p v-if="subtitle" class="mt-0.5 text-xs text-subtle">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 items-center gap-1.5"><slot name="actions" /></div>
    </header>
    <slot />
  </component>
</template>
