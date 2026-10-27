<script setup lang="ts">
import { computed, useId } from 'vue'

const props = defineProps<{
  label?: string
  hint?: string
  error?: string | null
  required?: boolean
  id?: string
  /** hide the label visually but keep it for screen readers */
  srLabel?: boolean
}>()

const uid = useId()
const fieldId = computed(() => props.id ?? `f-${uid}`)
const describedBy = computed(() => (props.error ? `${fieldId.value}-err` : props.hint ? `${fieldId.value}-hint` : undefined))
</script>

<template>
  <div class="space-y-1.5">
    <label v-if="label" :for="fieldId" :class="srLabel ? 'sr-only' : 'flex items-center gap-1.5 text-[13px] font-medium text-fg'">
      {{ label }}
      <span v-if="required" class="text-bad" aria-hidden="true">*</span>
      <slot name="label-extra" />
    </label>
    <slot :id="fieldId" :described-by="describedBy" :invalid="!!error" />
    <p v-if="error" :id="`${fieldId}-err`" class="text-xs text-bad" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="`${fieldId}-hint`" class="text-xs leading-relaxed text-subtle">{{ hint }}</p>
  </div>
</template>
