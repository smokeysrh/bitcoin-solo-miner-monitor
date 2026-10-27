<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ title: string; icon?: Component; subtitle?: string }>()
</script>

<template>
  <section class="card flex h-full flex-col p-[var(--pad-card)]" :aria-label="title">
    <header class="mb-3 flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
      <h3 class="flex items-center gap-2 text-xs font-semibold tracking-wide text-subtle uppercase">
        <component :is="icon" v-if="icon" class="size-3.5" aria-hidden="true" />
        <slot name="title">{{ title }}</slot>
      </h3>
      <slot name="actions" />
    </header>
    <div class="min-h-0 flex-1"><slot /></div>
    <p v-if="subtitle" class="mt-3 text-xs text-subtle">{{ subtitle }}</p>
  </section>
</template>
