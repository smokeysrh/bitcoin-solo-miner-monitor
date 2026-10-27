<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import RangePicker from '@/components/ui/RangePicker.vue'
import WidgetFrame from '../WidgetFrame.vue'

const range = useStorage('bsmm.dash.tempRange', '24h')
</script>

<template>
  <WidgetFrame title="Temperatures" subtitle="Hottest miner at each moment" to="/analytics" link-label="Analytics">
    <template #actions><RangePicker v-model="range" :ranges="['1h', '6h', '24h', '7d']" /></template>
    <HistoryChart :metrics="['temp_asic_c', 'temp_vr_c']" :range="range" :height="250" aria-label="Hottest chip and regulator temperatures over time" />
  </WidgetFrame>
</template>
