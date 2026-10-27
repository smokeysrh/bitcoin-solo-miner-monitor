<script setup lang="ts">
import { SwitchRoot, SwitchThumb } from 'reka-ui'

defineProps<{ id?: string; disabled?: boolean; label?: string }>()
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <SwitchRoot
    :id="id"
    v-model="model"
    :disabled="disabled"
    :aria-label="label"
    class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border border-line-strong bg-surface-3 transition-colors data-[state=checked]:border-transparent data-[state=checked]:bg-accent disabled:opacity-50"
  >
    <SwitchThumb
      class="pointer-events-none block size-[18px] translate-x-[3px] rounded-full bg-white shadow transition-transform duration-150 data-[state=checked]:translate-x-[23px]"
    />
  </SwitchRoot>
</template>
