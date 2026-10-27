<script setup lang="ts">
import { History } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import EventIcon from '@/components/ui/EventIcon.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const now = useNowSec()
</script>

<template>
  <WidgetFrame title="Recent activity" subtitle="Restarts, outages, best shares and blocks" to="/alerts" link-label="Everything">
    <ul v-if="live.events.length" class="-my-1 divide-y divide-line" data-testid="widget-activity">
      <li v-for="e in live.events.slice(0, 7)" :key="e.id ?? e.ts" class="flex items-start gap-3 py-2.5">
        <EventIcon :type="e.type" :severity="e.severity" />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-fg">
            <RouterLink v-if="e.device_id" :to="`/miners/${e.device_id}`" class="hover:underline">{{ e.title }}</RouterLink>
            <template v-else>{{ e.title }}</template>
          </p>
          <p v-if="e.body" class="truncate text-xs text-subtle">{{ e.body }}</p>
        </div>
        <time class="shrink-0 pt-0.5 text-xs text-subtle" :datetime="new Date(e.ts * 1000).toISOString()">{{ fmt.formatAgo(e.ts, now) }}</time>
      </li>
    </ul>
    <EmptyState v-else compact :icon="History" title="Nothing yet" description="Events show up here as your miners restart, drop out or set new records." />
  </WidgetFrame>
</template>
