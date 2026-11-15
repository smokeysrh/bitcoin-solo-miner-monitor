<script setup lang="ts">
import { Lock, Network } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import type { DeviceView, PoolInfo } from '@/lib/types'
import Badge from '@/components/ui/Badge.vue'
import Term from '@/components/ui/Term.vue'
import KeyValue from '@/components/ui/KeyValue.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

const props = defineProps<{ device: DeviceView }>()
const fmt = useFmt()

const pools = computed<PoolInfo[]>(() => props.device.telemetry?.pools ?? [])
</script>

<template>
  <div class="grid gap-[var(--gap-grid)] xl:grid-cols-2">
    <MetricCard title="Pools this miner uses" :icon="Network">
      <p class="mb-4 text-sm text-muted">
        A miner has a <Term k="pool">main pool</Term> and usually a <Term k="fallback">fallback</Term>. The one marked “in use” is receiving its work right now.
      </p>
      <ul v-if="pools.length" class="space-y-3" data-testid="pool-list">
        <li v-for="p in pools" :key="p.role + p.url" class="rounded-xl border p-4" :class="p.active ? 'border-accent-line bg-accent-softer' : 'border-line bg-surface-2/50'">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <Badge :tone="p.role === 'primary' ? 'accent' : 'neutral'" size="sm">{{ p.role === 'primary' ? 'Main pool' : 'Fallback' }}</Badge>
            <Badge v-if="p.active" tone="ok" dot size="sm">In use</Badge>
            <Badge v-if="p.tls" tone="info" size="sm"><Lock class="size-3" /> Encrypted</Badge>
          </div>
          <KeyValue
            :rows="[
              { label: 'Address', value: `${p.url ?? '–'}${p.port ? ':' + p.port : ''}`, mono: true },
              { label: 'Payout address', value: fmt.shortAddress(p.address), title: p.address ?? undefined, mono: true },
              { label: 'Worker', value: p.worker ?? '–' },
              ...(p.active ? [{ label: 'Latency', value: p.ping_ms != null ? `${Math.round(p.ping_ms)} ms` : '–' }, { label: 'Share difficulty', value: fmt.formatDifficulty(p.difficulty) }] : []),
            ]"
          />
        </li>
      </ul>
      <p v-else class="text-sm text-muted">This miner does not report its pool settings.</p>
    </MetricCard>
  </div>
</template>
