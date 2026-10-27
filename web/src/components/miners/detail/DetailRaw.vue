<script setup lang="ts">
import { Braces } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { DeviceView } from '@/lib/types'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

const props = defineProps<{ device: DeviceView }>()
const raw = ref<unknown>(null)
const driver = ref('')
const loading = ref(true)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const r = await api.deviceRaw(props.device.id)
    raw.value = r.raw
    driver.value = r.driver
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => props.device.id, load)

const text = computed(() => JSON.stringify(raw.value, null, 2) ?? 'null')
const report = computed(() =>
  JSON.stringify(
    { app: 'bitcoin-solo-miner-monitor', device: { model: props.device.model, family: props.device.family, driver: driver.value, firmware: props.device.firmware, capabilities: props.device.capabilities }, raw: raw.value },
    null,
    2,
  ),
)
</script>

<template>
  <MetricCard title="What the miner sent" :icon="Braces">
    <p class="mb-4 max-w-3xl text-sm leading-relaxed text-muted">
      This is the unprocessed reply from the miner, with any password fields removed. It is handy if a number looks wrong, or to attach to a bug report so the developers can add support for your model.
    </p>
    <Skeleton v-if="loading" class="h-64 rounded-xl" />
    <ErrorState v-else-if="error" compact :error="error" @retry="load" />
    <template v-else>
      <CodeBlock :code="text" label="Raw reply" max-height="520px" />
      <details class="mt-4">
        <summary class="cursor-pointer text-sm font-medium text-muted hover:text-fg">Copy a ready-made bug report</summary>
        <CodeBlock :code="report" class="mt-3" max-height="260px" />
      </details>
    </template>
  </MetricCard>
</template>
