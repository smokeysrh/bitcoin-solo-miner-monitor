<script setup lang="ts">
import { computed } from 'vue'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import { CircleHelp } from 'lucide-vue-next'
import { GLOSSARY } from '@/lib/glossary'

const props = defineProps<{ k: string; icon?: boolean }>()
const entry = computed(() => GLOSSARY[props.k])
</script>

<template>
  <PopoverRoot v-if="entry">
    <PopoverTrigger
      class="inline cursor-help rounded-sm underline decoration-dotted decoration-subtle underline-offset-4 hover:decoration-accent focus-visible:outline-2"
      :aria-label="`What is ${entry.title}?`"
    >
      <slot>{{ entry.title }}</slot>
      <CircleHelp v-if="icon" class="ml-1 inline size-3 -translate-y-px text-subtle" aria-hidden="true" />
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        :side-offset="8"
        class="z-[70] w-72 animate-pop-in rounded-xl border border-line-strong bg-surface-2 p-3.5 text-left shadow-pop"
      >
        <p class="mb-1 text-[13px] font-semibold text-fg">{{ entry.title }}</p>
        <p class="text-xs leading-relaxed text-muted">{{ entry.body }}</p>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
  <span v-else><slot /></span>
</template>
