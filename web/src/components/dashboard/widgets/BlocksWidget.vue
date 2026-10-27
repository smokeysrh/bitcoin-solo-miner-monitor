<script setup lang="ts">
import { Blocks, ExternalLink } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { useLive } from '@/stores/live'
import Badge from '@/components/ui/Badge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const now = useNowSec()
const mine = computed(() => new Set(live.blocksFound.map((b) => b.hash)))
const blocks = computed(() => live.recentBlocks.slice(0, 6))
</script>

<template>
  <WidgetFrame title="Latest blocks" :subtitle="live.blocksFound.length ? `${live.blocksFound.length} found by you` : 'Found by the whole network'" to="/bitcoin" link-label="Network">
    <ul v-if="blocks.length" class="-my-1 divide-y divide-line" data-testid="widget-blocks">
      <li v-for="b in blocks" :key="b.hash" class="flex items-center gap-3 py-2.5">
        <div class="min-w-0 flex-1">
          <p class="flex items-center gap-2 text-sm font-medium text-fg">
            <span class="tnum">{{ fmt.formatNumber(b.height) }}</span>
            <Badge v-if="b.yours || mine.has(b.hash)" tone="accent" size="sm">You</Badge>
          </p>
          <p class="truncate text-xs text-subtle">{{ b.pool_name ?? 'Unknown miner' }}<template v-if="b.tx_count"> · {{ fmt.formatNumber(b.tx_count) }} txs</template></p>
        </div>
        <time class="shrink-0 text-xs text-subtle">{{ fmt.formatAgo(b.ts, now) }}</time>
        <a
          :href="`https://mempool.space/block/${b.hash}`"
          target="_blank"
          rel="noopener noreferrer"
          class="grid size-7 shrink-0 place-items-center rounded-md text-subtle hover:bg-surface-3 hover:text-fg"
          :aria-label="`Open block ${b.height} on mempool.space`"
        >
          <ExternalLink class="size-3.5" />
        </a>
      </li>
    </ul>
    <EmptyState v-else compact :icon="Blocks" title="No blocks to show" description="Recent blocks appear once network data is available." />
  </WidgetFrame>
</template>
