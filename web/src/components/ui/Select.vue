<script setup lang="ts" generic="T extends string | number">
import { ChevronDown } from 'lucide-vue-next'
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'

// aria-label, data-testid and friends belong on the native <select>
defineOptions({ inheritAttrs: false })

interface Option<V> {
  value: V
  label: string
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    options: Option<T>[]
    id?: string
    describedBy?: string
    disabled?: boolean
    invalid?: boolean
    size?: 'sm' | 'md'
    placeholder?: string
    class?: HTMLAttributes['class']
  }>(),
  { size: 'md' },
)

const model = defineModel<T | null>()

function onChange(e: Event): void {
  const raw = (e.target as HTMLSelectElement).value
  const match = props.options.find((o) => String(o.value) === raw)
  model.value = match ? match.value : (raw as T)
}
</script>

<template>
  <div :class="cn('relative w-full', props.class)">
    <select
      v-bind="$attrs"
      :id="id"
      :value="model ?? ''"
      :disabled="disabled"
      :aria-invalid="invalid || undefined"
      :aria-describedby="describedBy"
      :class="
        cn(
          'w-full appearance-none rounded-xl border bg-surface-2 pl-3 pr-9 text-sm text-fg outline-none transition-colors',
          'focus:border-accent focus:ring-2 focus:ring-accent/25 disabled:opacity-55',
          invalid ? 'border-bad' : 'border-line hover:border-line-strong',
          size === 'sm' ? 'h-8' : 'h-10',
        )
      "
      @change="onChange"
    >
      <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
      <option v-for="o in options" :key="String(o.value)" :value="o.value" :disabled="o.disabled">{{ o.label }}</option>
    </select>
    <ChevronDown class="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-subtle" aria-hidden="true" />
  </div>
</template>
