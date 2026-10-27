<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'

defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <div :class="cn('skeleton h-4 w-full', $props.class)" aria-hidden="true" />
</template>
