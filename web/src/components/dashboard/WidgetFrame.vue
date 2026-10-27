<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next'
import type { RouteLocationRaw } from 'vue-router'
import { RouterLink } from 'vue-router'

defineProps<{ title: string; subtitle?: string; to?: RouteLocationRaw; linkLabel?: string; flush?: boolean }>()
</script>

<template>
  <section class="card flex h-full min-h-0 flex-col" :aria-label="title">
    <header class="flex items-start justify-between gap-3 px-[var(--pad-card)] pt-[var(--pad-card)]">
      <div class="min-w-0">
        <h2 class="truncate text-sm font-semibold text-fg"><slot name="title">{{ title }}</slot></h2>
        <p v-if="subtitle" class="mt-0.5 truncate text-xs text-subtle">{{ subtitle }}</p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
        <RouterLink v-if="to" :to="to" class="inline-flex items-center gap-0.5 rounded-md text-xs font-medium text-muted transition-colors hover:text-accent-text">
          {{ linkLabel ?? 'Details' }}<ChevronRight class="size-3.5" aria-hidden="true" />
        </RouterLink>
      </div>
    </header>
    <div :class="['min-h-0 flex-1', flush ? 'pt-3' : 'px-[var(--pad-card)] pt-3 pb-[var(--pad-card)]']"><slot /></div>
  </section>
</template>
