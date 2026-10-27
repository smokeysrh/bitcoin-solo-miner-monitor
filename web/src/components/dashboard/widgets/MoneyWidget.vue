<script setup lang="ts">
import { Coins } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const eco = computed(() => (live.odds?.available ? live.odds.economics : null))
</script>

<template>
  <WidgetFrame title="Electricity &amp; value" subtitle="What mining costs vs. the lottery payout" to="/odds" link-label="Details">
    <div v-if="eco" data-testid="widget-money">
      <div class="grid grid-cols-3 gap-3">
        <div>
          <p class="text-xs text-subtle">Per day</p>
          <p class="tnum mt-1 text-lg font-semibold text-fg">{{ fmt.money(eco.cost_per_day) }}</p>
        </div>
        <div>
          <p class="text-xs text-subtle">Per month</p>
          <p class="tnum mt-1 text-lg font-semibold text-fg">{{ fmt.money(eco.cost_per_month) }}</p>
        </div>
        <div>
          <p class="text-xs text-subtle">Per year</p>
          <p class="tnum mt-1 text-lg font-semibold text-fg">{{ fmt.money(eco.cost_per_year) }}</p>
        </div>
      </div>
      <p class="mt-1.5 text-xs text-subtle">electricity at {{ fmt.money(eco.price_per_kwh, 3) }}/kWh{{ eco.power_w ? ` for ${fmt.formatPower(eco.power_w)}` : '' }}</p>

      <dl class="mt-4 space-y-2 border-t border-line pt-3.5 text-sm">
        <div class="flex items-baseline justify-between gap-3">
          <dt class="text-muted">Expected payout / year</dt>
          <dd class="tnum font-medium text-fg">{{ eco.expected_value_per_year != null ? fmt.money(eco.expected_value_per_year) : '–' }}</dd>
        </div>
        <div v-if="eco.ev_to_cost_ratio != null" class="flex items-baseline justify-between gap-3">
          <dt class="text-muted">Payout vs. cost</dt>
          <dd class="tnum font-medium" :class="eco.ev_to_cost_ratio >= 1 ? 'text-ok' : 'text-warn'">{{ (eco.ev_to_cost_ratio * 100).toFixed(0) }}%</dd>
        </div>
        <div v-if="eco.break_even_btc_price" class="flex items-baseline justify-between gap-3">
          <dt class="text-muted">Break-even Bitcoin price</dt>
          <dd class="tnum font-medium text-fg">{{ fmt.money(eco.break_even_btc_price, 0) }}</dd>
        </div>
      </dl>
      <p class="mt-3 text-[11px] leading-relaxed text-subtle">The payout is a long-shot lottery that arrives in one huge lump, not income.</p>
    </div>
    <EmptyState v-else compact :icon="Coins" title="Costs need power and difficulty" description="Once your miners report power and network data is available, costs appear here." />
  </WidgetFrame>
</template>
