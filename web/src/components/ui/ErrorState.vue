<script setup lang="ts">
import { RotateCw, TriangleAlert } from 'lucide-vue-next'
import { describeError } from '@/lib/api'
import Button from './Button.vue'

defineProps<{ error?: unknown; title?: string; compact?: boolean }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div :class="['flex flex-col items-center text-center', compact ? 'gap-2 p-6' : 'gap-3 px-6 py-12']" role="alert">
    <div class="grid size-11 place-items-center rounded-2xl border border-bad/30 bg-bad-soft text-bad">
      <TriangleAlert class="size-5" aria-hidden="true" />
    </div>
    <h3 class="text-base font-semibold text-fg">{{ title ?? 'Something went wrong' }}</h3>
    <p v-if="error" class="max-w-md text-sm leading-relaxed text-muted">{{ describeError(error) }}</p>
    <Button size="sm" variant="secondary" @click="$emit('retry')">
      <template #icon><RotateCw class="size-4" /></template>
      Try again
    </Button>
  </div>
</template>
