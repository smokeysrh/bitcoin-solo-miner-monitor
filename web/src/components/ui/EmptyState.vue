<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ icon?: Component; title: string; description?: string; compact?: boolean }>()
</script>

<template>
  <div :class="['flex flex-col items-center justify-center text-center', compact ? 'gap-2 px-4 py-8' : 'gap-3 px-6 py-14']">
    <div v-if="icon" class="grid size-12 place-items-center rounded-2xl border border-accent-line bg-accent-soft text-accent-text">
      <component :is="icon" class="size-6" aria-hidden="true" />
    </div>
    <h3 class="text-base font-semibold text-fg">{{ title }}</h3>
    <p v-if="description" class="max-w-md text-sm leading-relaxed text-muted">{{ description }}</p>
    <div v-if="$slots.default" class="mt-2 flex flex-wrap items-center justify-center gap-2"><slot /></div>
  </div>
</template>
