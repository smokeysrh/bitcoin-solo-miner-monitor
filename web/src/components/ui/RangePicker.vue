<script setup lang="ts">
import Segmented from './Segmented.vue'

withDefaults(defineProps<{ ranges?: string[]; label?: string }>(), {
  ranges: () => ['1h', '6h', '24h', '7d', '30d'],
  label: 'Time range',
})
const model = defineModel<string>({ required: true })
</script>

<template>
  <Segmented v-model="model" :label="label" size="sm" :options="ranges.map((r) => ({ value: r, label: r }))" />
</template>
