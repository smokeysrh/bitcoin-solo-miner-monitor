<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'

defineProps<{
  placeholder?: string
  rows?: number
  id?: string
  describedBy?: string
  disabled?: boolean
  invalid?: boolean
  mono?: boolean
  maxlength?: number
  class?: HTMLAttributes['class']
}>()
const model = defineModel<string>({ default: '' })
</script>

<template>
  <textarea
    :id="id"
    v-model="model"
    :rows="rows ?? 3"
    :placeholder="placeholder"
    :disabled="disabled"
    :maxlength="maxlength"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedBy"
    :class="
      cn(
        'w-full resize-y rounded-xl border bg-surface-2 px-3 py-2.5 text-sm text-fg outline-none transition-colors placeholder:text-subtle',
        'focus:border-accent focus:ring-2 focus:ring-accent/25',
        invalid ? 'border-bad' : 'border-line hover:border-line-strong',
        mono && 'font-mono text-[13px]',
        $props.class,
      )
    "
  />
</template>
