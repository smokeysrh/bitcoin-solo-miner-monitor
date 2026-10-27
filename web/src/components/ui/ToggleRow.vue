<script setup lang="ts">
import { useId } from 'vue'
import Switch from './Switch.vue'

defineProps<{ title: string; description?: string; disabled?: boolean }>()
const model = defineModel<boolean>({ default: false })
const id = useId()
</script>

<template>
  <div class="flex items-start justify-between gap-4 py-3">
    <label :for="id" class="min-w-0 flex-1 cursor-pointer">
      <span class="block text-sm font-medium text-fg">{{ title }}</span>
      <span v-if="description" class="mt-0.5 block text-xs leading-relaxed text-subtle">{{ description }}</span>
      <slot />
    </label>
    <Switch :id="id" v-model="model" :disabled="disabled" />
  </div>
</template>
