<script setup lang="ts">
defineProps<{ rows: { label: string; value: string; tone?: 'ok' | 'warn' | 'bad' | 'muted'; title?: string; mono?: boolean }[] }>()
const tones = { ok: 'text-ok', warn: 'text-warn', bad: 'text-bad', muted: 'text-subtle' } as const
</script>

<template>
  <dl class="space-y-2 text-sm">
    <div v-for="r in rows" :key="r.label" class="flex items-baseline justify-between gap-4">
      <dt class="shrink-0 text-muted">{{ r.label }}</dt>
      <dd :class="['tnum min-w-0 truncate text-right font-medium', r.tone ? tones[r.tone] : 'text-fg', r.mono && 'font-mono text-[13px]']" :title="r.title ?? r.value">{{ r.value }}</dd>
    </div>
  </dl>
</template>
