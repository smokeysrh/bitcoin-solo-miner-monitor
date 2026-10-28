<script setup lang="ts">
import { CircleCheck, Info, Lightbulb, OctagonAlert, TriangleAlert, X } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { SETUP_INSIGHT_IDS, useInsights } from '@/stores/insights'
import Button from '@/components/ui/Button.vue'
import WidgetFrame from '../WidgetFrame.vue'

const insights = useInsights()
const router = useRouter()
onMounted(() => void insights.refresh())

// "best-share" is told better by the Closest call card; setup steps live in the checklist
const items = computed(() => insights.items.filter((i) => !SETUP_INSIGHT_IDS.includes(i.id) && i.id !== 'best-share'))

const icons = { warning: TriangleAlert, critical: OctagonAlert, tip: Lightbulb, info: Info } as const
const tones: Record<string, string> = { warning: 'text-warn bg-warn-soft', critical: 'text-bad bg-bad-soft', tip: 'text-accent-text bg-accent-soft', info: 'text-info bg-info-soft' }

function act(a: { type: string; target: string }): void {
  if (a.type === 'route') void router.push(a.target)
}
</script>

<template>
  <WidgetFrame title="Tips &amp; observations" subtitle="Plain-language notes about your setup">
    <div v-if="insights.error" class="mb-3 text-sm text-warn" role="status">
      <p>{{ insights.loaded ? 'Observations are stale.' : 'Could not load observations' }}</p>
      <p v-if="insights.lastSuccess">Last checked: {{ new Date(insights.lastSuccess).toLocaleString() }}</p>
      <p>{{ insights.error }}</p>
      <Button size="xs" variant="outline" :loading="insights.loading" @click="insights.refresh(true)">Retry observations</Button>
    </div>
    <p v-else-if="!insights.loaded" class="text-sm text-muted" role="status">Checking observations…</p>
    <ul v-if="items.length" class="space-y-2.5" data-testid="widget-insights">
      <li v-for="i in items.slice(0, 5)" :key="i.id" class="flex items-start gap-3 rounded-xl border border-line bg-surface-2/60 p-3.5">
        <span :class="['grid size-8 shrink-0 place-items-center rounded-full', tones[i.level] ?? tones.info]">
          <component :is="icons[i.level as keyof typeof icons] ?? Info" class="size-4" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-fg">
            <RouterLink v-if="i.device_id" :to="`/miners/${i.device_id}`" class="hover:underline">{{ i.title }}</RouterLink>
            <template v-else>{{ i.title }}</template>
          </p>
          <p class="mt-1 text-xs leading-relaxed text-muted">{{ i.body }}</p>
          <Button v-if="i.action" size="xs" variant="soft" class="mt-2" @click="act(i.action)">{{ i.action.label }}</Button>
        </div>
        <button class="-m-1 grid size-7 shrink-0 place-items-center rounded-md text-subtle hover:bg-surface-3 hover:text-fg" :aria-label="`Dismiss: ${i.title}`" @click="insights.dismiss(i.id)">
          <X class="size-3.5" />
        </button>
      </li>
    </ul>
    <div v-else-if="insights.loaded && !insights.error" class="flex items-center gap-3 rounded-xl border border-line bg-surface-2/60 p-4">
      <CircleCheck class="size-5 shrink-0 text-ok" aria-hidden="true" />
      <p class="text-sm text-muted">Nothing to suggest. Your setup looks healthy.</p>
    </div>
  </WidgetFrame>
</template>
