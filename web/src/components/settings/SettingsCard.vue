<script setup lang="ts">
import Button from '@/components/ui/Button.vue'

withDefaults(defineProps<{ title: string; description?: string; dirty?: boolean; saving?: boolean; error?: string | null; showSave?: boolean }>(), { showSave: false })
defineEmits<{ save: []; discard: [] }>()
</script>

<template>
  <section class="card" :aria-label="title">
    <header class="border-b border-line px-[var(--pad-card)] py-4">
      <h3 class="text-base font-semibold text-fg">{{ title }}</h3>
      <p v-if="description" class="mt-1 max-w-2xl text-sm leading-relaxed text-muted">{{ description }}</p>
    </header>
    <div class="p-[var(--pad-card)]"><slot /></div>
    <footer v-if="showSave || error" class="flex flex-wrap items-center gap-3 border-t border-line bg-surface-2/50 px-[var(--pad-card)] py-3">
      <p v-if="error" class="mr-auto text-sm text-bad" role="alert">{{ error }}</p>
      <template v-if="showSave">
        <Button v-if="dirty" variant="ghost" size="sm" @click="$emit('discard')">Discard</Button>
        <Button variant="primary" size="sm" :loading="saving" :disabled="!dirty" @click="$emit('save')">Save</Button>
      </template>
    </footer>
  </section>
</template>
