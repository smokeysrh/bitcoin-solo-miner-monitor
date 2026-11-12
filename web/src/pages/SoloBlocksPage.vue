<script setup lang="ts">
import { Blocks, ExternalLink, Unplug } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import StaleNotice from '@/components/ui/StaleNotice.vue'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { api } from '@/lib/api'
import type { SoloBlocksResult } from '@/lib/types'

const fmt = useFmt()
const now = useNowSec()

// Blocks are rare and the server caches the list, so this loads once per visit; a failed load keeps the last list, labelled.
const data = ref<SoloBlocksResult | null>(null)
const loading = ref(true)
const error = ref<unknown>(null)
let ctrl: AbortController | null = null

async function load(): Promise<void> {
  ctrl?.abort()
  const request = new AbortController()
  ctrl = request
  loading.value = !data.value
  try {
    const result = await api.soloBlocks(request.signal)
    if (request.signal.aborted || ctrl !== request) return
    data.value = result
    error.value = null
  } catch (e) {
    if (request.signal.aborted || ctrl !== request) return
    error.value = e
  } finally {
    if (ctrl === request) loading.value = false
  }
}
onMounted(() => void load())
onBeforeUnmount(() => ctrl?.abort())

/** Why the list on screen may be out of date: this page's own failed retry, or the server's failed refresh. */
const staleError = computed<unknown>(() => error.value ?? (data.value?.stale ? data.value.error : null))
const footnote = computed(() => {
  const d = data.value
  if (!d?.available) return undefined
  const pools = d.pools.map((p) => p.name).join(', ')
  if (d.source === 'demo') return `Demo data, not real blocks. Pools covered: ${pools}. Up to ${d.limit} blocks, newest first.`
  return `Pools covered: ${pools}. Up to ${d.limit} blocks, newest first. Source: mempool.space, checked ${fmt.formatDateTime(d.fetched_at)}.`
})
const isoDate = (ts: number): string => new Date(ts * 1000).toISOString()
</script>

<template>
  <div class="space-y-5" data-testid="solo-blocks-page">
    <header>
      <h2 class="text-2xl font-bold tracking-tight text-fg">Solo blocks</h2>
      <p class="mt-1 text-sm text-muted">The latest blocks found by solo pools, with the pool that found each one.</p>
    </header>

    <MetricCard title="Latest blocks found by solo pools" :icon="Blocks" :subtitle="footnote">
      <Skeleton v-if="loading" class="h-64 w-full rounded-xl" />
      <ErrorState v-else-if="error && !data" compact title="Could not load solo blocks" :error="error" @retry="load" />
      <EmptyState
        v-else-if="data && !data.available"
        compact
        :icon="Unplug"
        title="Solo blocks are not available"
        :description="data.message ?? undefined"
        data-testid="solo-blocks-off"
      >
        <Button to="/settings/sources" variant="soft">Open data source settings</Button>
      </EmptyState>
      <template v-else-if="data">
        <StaleNotice v-if="staleError" :error="staleError" @retry="load" />
        <p v-if="data.failed_pools.length" class="mb-3 text-sm text-warn" role="status" data-testid="solo-blocks-partial">
          Could not read the blocks of {{ data.failed_pools.join(', ') }}. This list may be missing some of their blocks.
        </p>
        <EmptyState v-if="!data.blocks.length" compact :icon="Blocks" title="No solo-pool blocks to show yet" description="mempool.space did not list any blocks for these pools." />
        <ol v-else role="list" class="divide-y divide-line" data-testid="solo-block-list" aria-label="Latest blocks found by solo pools, newest first">
          <li
            v-for="b in data.blocks"
            :key="b.hash"
            data-testid="solo-block"
            :data-yours="b.yours ? 'true' : 'false'"
            :class="['flex flex-wrap items-center gap-x-4 gap-y-2 py-3', b.yours && 'rounded-xl border border-accent-line bg-accent-softer px-3']"
          >
            <div class="min-w-0 flex-1 basis-40">
              <p class="flex flex-wrap items-center gap-2">
                <span class="tnum text-base font-semibold text-fg" data-testid="solo-block-height">{{ fmt.formatNumber(b.height) }}</span>
                <Badge v-if="b.yours" tone="accent" size="sm">Yours</Badge>
              </p>
              <p class="mt-0.5 text-sm text-muted">{{ b.pool_name }}</p>
            </div>
            <div class="text-sm">
              <p class="tnum text-fg">{{ fmt.formatAgo(b.ts, now) }}</p>
              <p class="tnum text-xs text-subtle"><time :datetime="isoDate(b.ts)">{{ fmt.formatDate(b.ts) }}</time></p>
            </div>
            <a
              :href="b.url"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex min-h-9 items-center gap-1.5 text-sm font-medium text-fg underline underline-offset-2 hover:no-underline"
              :aria-label="`Block ${fmt.formatNumber(b.height)} on mempool.space`"
            >
              mempool.space
              <ExternalLink class="size-3.5" aria-hidden="true" />
            </a>
          </li>
        </ol>
      </template>
    </MetricCard>
  </div>
</template>
