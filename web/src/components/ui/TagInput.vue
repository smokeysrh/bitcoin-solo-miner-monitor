<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps<{ placeholder?: string; suggestions?: string[]; id?: string; max?: number; /** keep case and length (for addresses and other exact values) */ raw?: boolean }>()
const tags = defineModel<string[]>({ default: () => [] })
const draft = ref('')

function add(input: string): void {
  const t = props.raw ? input.trim().slice(0, 200) : input.trim().toLowerCase().replace(/\s+/g, '-').slice(0, 24)
  if (t && !tags.value.includes(t)) tags.value = [...tags.value, t]
  draft.value = ''
}
function onKey(e: KeyboardEvent): void {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    add(draft.value)
  } else if (e.key === 'Backspace' && !draft.value && tags.value.length) {
    tags.value = tags.value.slice(0, -1)
  }
}
</script>

<template>
  <div>
    <div
      class="flex min-h-10 flex-wrap items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-2 py-1.5 transition-colors focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/25"
    >
      <span v-for="t in tags" :key="t" class="inline-flex items-center gap-1 rounded-full bg-accent-soft py-0.5 pr-1 pl-2.5 text-xs text-accent-text">
        {{ t }}
        <button type="button" class="grid size-4 place-items-center rounded-full hover:bg-accent-soft" :aria-label="`Remove tag ${t}`" @click="tags = tags.filter((x) => x !== t)">
          <X class="size-3" />
        </button>
      </span>
      <input
        :id="id"
        v-model="draft"
        class="min-w-24 flex-1 bg-transparent px-1 py-0.5 text-sm text-fg outline-none placeholder:text-subtle"
        :placeholder="tags.length ? '' : (placeholder ?? 'Add a tag and press Enter')"
        :disabled="max !== undefined && tags.length >= max"
        @keydown="onKey"
        @blur="draft && add(draft)"
      />
    </div>
    <div v-if="suggestions?.length" class="mt-1.5 flex flex-wrap gap-1.5">
      <button
        v-for="s in suggestions.filter((s) => !tags.includes(s)).slice(0, 8)"
        :key="s"
        type="button"
        class="rounded-full border border-line px-2 py-0.5 text-[11px] text-muted hover:border-line-strong hover:text-fg"
        @click="add(s)"
      >
        + {{ s }}
      </button>
    </div>
  </div>
</template>
