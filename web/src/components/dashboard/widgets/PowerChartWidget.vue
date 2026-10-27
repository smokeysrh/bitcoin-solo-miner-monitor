<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import RangePicker from '@/components/ui/RangePicker.vue'
import WidgetFrame from '../WidgetFrame.vue'

const range = useStorage('bsmm.dash.powerRange', '24h')
</script>

<template>
  <WidgetFrame title="Power &amp; efficiency" subtitle="Lower efficiency numbers are better" to="/analytics" link-label="Analytics">
    <template #actions><RangePicker v-model="range" :ranges="['1h', '6h', '24h', '7d', '30d']" /></template>
    <HistoryChart :metrics="['power_w', 'efficiency_j_th']" :range="range" :height="250" aria-label="Power and efficiency over time" />
  </WidgetFrame>
</template>
