<script setup lang="ts" generic="T extends string | number">
import { RadioGroupItem, RadioGroupRoot } from 'reka-ui'
import type { Component, HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'

export interface SegOption<V> {
  value: V
  label: string
  icon?: Component
  title?: string
}

defineProps<{ options: SegOption<T>[]; label: string; size?: 'sm' | 'md'; class?: HTMLAttributes['class']; iconOnly?: boolean }>()
const model = defineModel<T>()
</script>

<template>
  <RadioGroupRoot
    :model-value="model === undefined ? undefined : String(model)"
    :aria-label="label"
    orientation="horizontal"
    :class="cn('inline-flex rounded-xl border border-line bg-surface-2 p-0.5', $props.class)"
    @update:model-value="(v) => (model = (options.find((o) => String(o.value) === v)?.value ?? v) as T)"
  >
    <RadioGroupItem
      v-for="o in options"
      :key="String(o.value)"
      :value="String(o.value)"
      :title="o.title ?? o.label"
      :aria-label="iconOnly ? o.label : undefined"
      :class="
        cn(
          'inline-flex items-center justify-center gap-1.5 rounded-[10px] px-3 font-medium text-muted transition-colors outline-none',
          'hover:text-fg focus-visible:ring-2 focus-visible:ring-accent data-[state=checked]:bg-surface-3 data-[state=checked]:text-fg data-[state=checked]:shadow-sm',
          size === 'sm' ? 'h-7 text-xs' : 'h-8 text-[13px]',
        )
      "
    >
      <component :is="o.icon" v-if="o.icon" class="size-4" aria-hidden="true" />
      <span v-if="!iconOnly">{{ o.label }}</span>
    </RadioGroupItem>
  </RadioGroupRoot>
</template>
