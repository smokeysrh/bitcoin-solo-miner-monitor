<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import RangePicker from '@/components/ui/RangePicker.vue'
import Switch from '@/components/ui/Switch.vue'
import WidgetFrame from '../WidgetFrame.vue'

const range = useStorage('bsmm.dash.hashrateRange', '24h')
const perMiner = useStorage('bsmm.dash.hashratePerMiner', false)
</script>

<template>
  <WidgetFrame title="Hashrate" :subtitle="perMiner ? 'One line per miner' : 'All miners together'" to="/analytics" link-label="Analytics">
    <template #actions>
      <label class="hidden items-center gap-2 text-xs text-muted sm:flex">
        Per miner <Switch v-model="perMiner" label="Show one line per miner" />
      </label>
      <RangePicker v-model="range" :ranges="['1h', '6h', '24h', '7d', '30d']" />
    </template>
    <div data-testid="widget-hashrate-chart">
      <HistoryChart :metrics="['hashrate_hs']" :range="range" :per-device="perMiner" :height="270" :aria-label="`Hashrate over the last ${range}`" />
    </div>
  </WidgetFrame>
</template>
