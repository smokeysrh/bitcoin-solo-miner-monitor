<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(
  defineProps<{
    label: string
    value: string
    unit?: string
    sub?: string
    tone?: 'default' | 'ok' | 'warn' | 'bad' | 'info' | 'accent'
    icon?: Component
    size?: 'sm' | 'md' | 'lg'
  }>(),
  { tone: 'default', size: 'md' },
)

const toneClass = {
  default: 'text-fg',
  ok: 'text-ok',
  warn: 'text-warn',
  bad: 'text-bad',
  info: 'text-info',
  accent: 'text-accent-text',
} as const
</script>

<template>
  <div class="min-w-0">
    <p class="flex items-center gap-1.5 text-xs font-medium text-subtle">
      <component :is="icon" v-if="icon" class="size-3.5" aria-hidden="true" />
      <slot name="label">{{ label }}</slot>
    </p>
    <p :class="['tnum mt-1 truncate leading-none font-semibold tracking-tight', toneClass[tone], size === 'lg' ? 'text-3xl' : size === 'sm' ? 'text-lg' : 'text-2xl']">
      {{ value }}<span v-if="unit" class="ml-1 text-[0.55em] font-medium text-subtle">{{ unit }}</span>
    </p>
    <p v-if="sub" class="mt-1 truncate text-xs text-muted">{{ sub }}</p>
  </div>
</template>
