<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'
import CopyButton from './CopyButton.vue'

defineProps<{ code: string; label?: string; maxHeight?: string; class?: HTMLAttributes['class'] }>()
</script>

<template>
  <div :class="cn('group relative rounded-xl border border-line bg-surface-2', $props.class)">
    <div v-if="label" class="flex items-center justify-between border-b border-line px-3 py-1.5">
      <span class="eyebrow">{{ label }}</span>
    </div>
    <pre class="overflow-auto p-3.5 pr-12 text-[12.5px] leading-relaxed text-fg" :style="{ maxHeight }" tabindex="0" role="region" :aria-label="label ?? 'Code'"><code>{{ code }}</code></pre>
    <CopyButton :text="code" what="Copied" class="absolute top-1.5 right-1.5" :class="label ? 'top-9' : ''" />
  </div>
</template>
