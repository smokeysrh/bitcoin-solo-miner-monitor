<script setup lang="ts">
import { Fuel } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const fees = computed(() => live.network?.fees_sat_vb ?? null)
const tiers: [string, string][] = [
  ['fastest', 'Next block'],
  ['half_hour', '~30 min'],
  ['hour', '~1 hour'],
  ['economy', 'Whenever'],
]
</script>

<template>
  <WidgetFrame title="Fees &amp; price" subtitle="What sending bitcoin costs right now">
    <div v-if="fees" data-testid="widget-fees">
      <div class="grid grid-cols-2 gap-x-4 gap-y-3">
        <div v-for="[k, label] in tiers" :key="k">
          <p class="text-xs text-subtle">{{ label }}</p>
          <p class="tnum mt-0.5 text-lg font-semibold text-fg">{{ fees[k] ?? '–' }} <span class="text-xs font-medium text-subtle">sat/vB</span></p>
        </div>
      </div>
      <div class="mt-4 flex items-baseline justify-between border-t border-line pt-3 text-sm">
        <span class="text-muted">Bitcoin price</span>
        <span class="tnum font-semibold text-fg">{{ live.network?.btc_price ? fmt.money(live.network.btc_price, 0) : '–' }}</span>
      </div>
      <p v-if="live.network?.mempool_tx_count" class="mt-1.5 text-xs text-subtle">{{ fmt.formatNumber(live.network.mempool_tx_count) }} transactions waiting to be mined</p>
    </div>
    <EmptyState v-else compact :icon="Fuel" title="No fee data" description="Fee estimates come from mempool.space or your own node." />
  </WidgetFrame>
</template>
