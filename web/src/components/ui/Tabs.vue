<script setup lang="ts">
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from 'reka-ui'
import type { Component } from 'vue'

export interface TabDef {
  value: string
  label: string
  icon?: Component
  badge?: string | number | null
}

defineProps<{ tabs: TabDef[]; label: string }>()
const model = defineModel<string>({ required: true })
</script>

<template>
  <TabsRoot v-model="model" class="flex min-h-0 flex-col">
    <TabsList :aria-label="label" class="-mx-1 flex gap-1 overflow-x-auto border-b border-line px-1 pb-px">
      <TabsTrigger
        v-for="t in tabs"
        :key="t.value"
        :value="t.value"
        class="relative -mb-px inline-flex h-10 shrink-0 items-center gap-2 border-b-2 border-transparent px-3 text-sm font-medium text-muted outline-none transition-colors hover:text-fg focus-visible:text-fg data-[state=active]:border-accent data-[state=active]:text-fg"
      >
        <component :is="t.icon" v-if="t.icon" class="size-4" aria-hidden="true" />
        {{ t.label }}
        <span v-if="t.badge !== null && t.badge !== undefined && t.badge !== ''" class="rounded-full bg-accent-soft px-1.5 py-0.5 text-[11px] leading-none text-accent-text">
          {{ t.badge }}
        </span>
      </TabsTrigger>
    </TabsList>
    <TabsContent v-for="t in tabs" :key="t.value" :value="t.value" class="pt-5 outline-none">
      <slot :name="t.value" />
    </TabsContent>
  </TabsRoot>
</template>
