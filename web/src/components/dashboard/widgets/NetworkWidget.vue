<script setup lang="ts">
import { Bitcoin } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { sourceLabel } from '@/lib/labels'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import Term from '@/components/ui/Term.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const now = useNowSec()
const n = computed(() => live.network)
const ok = computed(() => !!n.value?.available)
const change = computed(() => n.value?.epoch?.estimated_change_pct ?? null)
const tipAge = computed(() => (n.value?.tip_time ? fmt.formatAgo(n.value.tip_time, now.value) : null))
</script>

<template>
  <WidgetFrame title="Bitcoin network" :subtitle="ok ? `via ${sourceLabel(n?.source)}` : undefined" to="/bitcoin" link-label="Details">
    <div v-if="ok && n" class="space-y-4" data-testid="widget-network">
      <div class="flex items-end justify-between gap-4">
        <div>
          <p class="text-xs font-medium text-subtle">Block height</p>
          <p class="tnum mt-1 text-3xl leading-none font-bold tracking-tight text-fg">{{ fmt.formatNumber(n.height) }}</p>
          <p v-if="tipAge" class="mt-1 text-xs text-muted">latest block {{ tipAge }}</p>
        </div>
        <div class="text-right">
          <p class="text-xs font-medium text-subtle"><Term k="difficulty">Difficulty</Term></p>
          <p class="tnum mt-1 text-xl leading-none font-semibold text-fg">{{ fmt.formatDifficulty(n.difficulty) }}</p>
          <p class="mt-1 text-xs text-muted">{{ fmt.hashrate(n.network_hashrate_hs, 3) }} network</p>
        </div>
      </div>

      <div v-if="n.epoch" class="space-y-1.5">
        <div class="flex items-baseline justify-between text-xs">
          <span class="font-medium text-muted"><Term k="retarget">Next difficulty change</Term></span>
          <span class="tnum text-subtle">
            {{ fmt.formatNumber(n.epoch.blocks_remaining) }} blocks · ~{{ fmt.formatDuration(n.epoch.seconds_remaining, 1) }}
            <b v-if="change !== null" :class="change >= 0 ? 'text-warn' : 'text-ok'" class="ml-1">{{ change >= 0 ? '+' : '' }}{{ change.toFixed(2) }}%</b>
          </span>
        </div>
        <ProgressBar :value="n.epoch.progress" tone="info" :height="6" label="Progress to the next difficulty adjustment" />
      </div>

      <div v-if="n.halving" class="space-y-1.5">
        <div class="flex items-baseline justify-between text-xs">
          <span class="font-medium text-muted"><Term k="halving">Next halving</Term></span>
          <span class="tnum text-subtle">{{ fmt.formatNumber(n.halving.blocks_remaining) }} blocks · ~{{ fmt.formatDuration(n.halving.seconds_remaining, 1) }}</span>
        </div>
        <ProgressBar :value="n.halving.progress" tone="violet" :height="6" label="Progress to the next halving" />
        <p class="text-[11px] text-subtle">Block reward {{ n.halving.subsidy_now_btc }} → {{ n.halving.subsidy_next_btc }} BTC</p>
      </div>
    </div>
    <EmptyState v-else compact :icon="Bitcoin" title="No network data yet" description="Allow public data or connect your node in Settings to see difficulty and block height." />
  </WidgetFrame>
</template>
