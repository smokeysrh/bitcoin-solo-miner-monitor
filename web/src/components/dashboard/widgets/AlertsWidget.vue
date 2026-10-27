<script setup lang="ts">
import { CircleCheck, OctagonAlert, TriangleAlert } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { useLive } from '@/stores/live'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const now = useNowSec()
</script>

<template>
  <WidgetFrame title="Needs attention" :subtitle="live.alerts.length ? `${live.alerts.length} active` : undefined" to="/alerts" link-label="Alerts">
    <ul v-if="live.alerts.length" class="space-y-2.5" data-testid="widget-alerts">
      <li v-for="a in live.alerts.slice(0, 5)" :key="a.key" class="flex items-start gap-3 rounded-xl border p-3" :class="a.severity === 'critical' ? 'border-bad/30 bg-bad-soft' : 'border-warn/30 bg-warn-soft'">
        <OctagonAlert v-if="a.severity === 'critical'" class="mt-0.5 size-4.5 shrink-0 text-bad" aria-hidden="true" />
        <TriangleAlert v-else class="mt-0.5 size-4.5 shrink-0 text-warn" aria-hidden="true" />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-fg">
            <RouterLink v-if="a.device_id" :to="`/miners/${a.device_id}`" class="hover:underline">{{ a.title }}</RouterLink>
            <template v-else>{{ a.title }}</template>
          </p>
          <p v-if="a.body" class="mt-0.5 text-xs leading-relaxed text-muted">{{ a.body }}</p>
        </div>
        <span class="shrink-0 text-xs text-muted">{{ fmt.formatAgo(a.since, now) }}</span>
      </li>
    </ul>
    <div v-else class="flex items-center gap-3 rounded-xl border border-ok/25 bg-ok-soft p-4" data-testid="widget-alerts-clear">
      <CircleCheck class="size-6 shrink-0 text-ok" aria-hidden="true" />
      <div>
        <p class="text-sm font-medium text-fg">All clear</p>
        <p class="text-xs text-muted">Nothing needs your attention right now.</p>
      </div>
    </div>
  </WidgetFrame>
</template>
