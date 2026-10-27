<script setup lang="ts">
import { Check, Copy } from 'lucide-vue-next'
import { useCopy } from '@/composables/useClipboard'
import Button from './Button.vue'

const props = withDefaults(defineProps<{ text: string; label?: string; what?: string; variant?: 'ghost' | 'secondary' | 'soft'; size?: 'xs' | 'sm' | 'iconSm' | 'icon' }>(), {
  variant: 'ghost',
  size: 'iconSm',
  what: 'Copied to clipboard',
})
const { copied, copy } = useCopy()
</script>

<template>
  <Button :variant="variant" :size="size" :aria-label="label ?? 'Copy'" :title="label ?? 'Copy'" @click="copy(props.text, props.what)">
    <Check v-if="copied" class="size-4 text-ok" />
    <Copy v-else class="size-4" />
    <span v-if="size === 'xs' || size === 'sm'">{{ copied ? 'Copied' : (label ?? 'Copy') }}</span>
  </Button>
</template>
