<script setup lang="ts">
import { describeError } from '@/lib/api'
import Button from './Button.vue'

// Shown above a list that was loaded once but could not be refreshed: the old data stays visible, labelled.
defineProps<{ error?: unknown }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="mb-3 text-sm text-warn" role="status">
    <p>Some of this could not be loaded or refreshed, so it may be out of date.</p>
    <p v-if="error">{{ describeError(error) }}</p>
    <Button size="xs" variant="outline" @click="$emit('retry')">Try again</Button>
  </div>
</template>
