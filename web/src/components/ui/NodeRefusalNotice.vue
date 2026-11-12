<script setup lang="ts">
import { CircleAlert } from 'lucide-vue-next'
import { useId } from 'vue'
import type { NodeRefusal } from '@/lib/types'

// Says why a Bitcoin node refuses the app and what to change. The words come from the server (one copy, shared with
// the API agents read); this only lays them out. A text heading and icon carry the meaning, never colour alone.
defineProps<{ refusal: NodeRefusal }>()
const titleId = `node-refusal-${useId()}`
</script>

<template>
  <div role="group" :aria-labelledby="titleId" class="rounded-xl border border-warn/30 bg-warn-soft p-3 text-xs leading-relaxed">
    <p :id="titleId" class="flex items-center gap-2 font-medium text-warn"><CircleAlert class="size-4 shrink-0" aria-hidden="true" />{{ refusal.title }}</p>
    <p class="mt-1 text-muted">{{ refusal.message }}</p>
    <p class="mt-1 text-fg"><span class="font-medium">What to do:</span> {{ refusal.next_step }}</p>
  </div>
</template>
