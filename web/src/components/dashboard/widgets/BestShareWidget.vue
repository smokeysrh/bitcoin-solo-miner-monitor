<script setup lang="ts">
import { Trophy } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import Term from '@/components/ui/Term.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()

const best = computed(() => live.summary?.best_diff ?? null)
const net = computed(() => live.network?.difficulty ?? null)
// "how many times better would it need to be?" is far easier to feel than 0.0025%
const multiple = computed(() => (best.value && net.value ? net.value / best.value : null))
// position on a log scale from difficulty 1 to the network difficulty
const logPos = computed(() => (best.value && net.value && best.value > 1 ? Math.min(1, Math.log10(best.value) / Math.log10(net.value)) : 0))
const board = computed(() => live.leaderboard.slice(0, 5))
const top = computed(() => board.value[0]?.difficulty ?? 1)
</script>

<template>
  <WidgetFrame title="Closest call" subtitle="Your luckiest share so far">
    <div v-if="best" data-testid="widget-best-share">
      <p class="flex items-baseline gap-2">
        <span class="text-gradient-accent tnum text-4xl leading-none font-bold tracking-tight">{{ fmt.formatDifficulty(best) }}</span>
        <span class="text-xs text-subtle"><Term k="bestshare">best share</Term></span>
      </p>

      <div class="mt-4">
        <div class="relative h-2.5 rounded-full bg-surface-3" role="img" :aria-label="`Best share is ${(logPos * 100).toFixed(0)}% of the way to a block on a log scale`">
          <div class="h-full rounded-full" :style="{ width: `${logPos * 100}%`, background: 'linear-gradient(90deg, color-mix(in oklab, var(--accent) 55%, transparent), var(--accent))' }" />
          <span class="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-bg bg-accent shadow" :style="{ left: `${logPos * 100}%` }" />
        </div>
        <div class="mt-1.5 flex justify-between text-[11px] text-subtle">
          <span>1</span>
          <span>needed for a block: {{ fmt.formatDifficulty(net) }}</span>
        </div>
      </div>

      <p v-if="multiple" class="mt-3 text-sm leading-relaxed text-muted">
        A block needs a share <b class="tnum text-fg">{{ fmt.formatNumber(Math.round(multiple)) }}×</b> better. Any single hash could do it.
      </p>

      <ol v-if="board.length > 1" class="mt-4 space-y-2 border-t border-line pt-3.5">
        <li v-for="(row, i) in board" :key="row.device_id" class="flex items-center gap-3 text-xs">
          <span class="w-4 text-center font-semibold" :class="i === 0 ? 'text-accent-text' : 'text-subtle'">{{ i + 1 }}</span>
          <RouterLink :to="`/miners/${row.device_id}`" class="min-w-0 flex-1 truncate text-muted hover:text-fg">{{ live.deviceName(row.device_id) }}</RouterLink>
          <span class="h-1.5 w-16 overflow-hidden rounded-full bg-surface-3" aria-hidden="true">
            <span class="block h-full rounded-full bg-accent/70" :style="{ width: `${Math.max(6, (row.difficulty / top) * 100)}%` }" />
          </span>
          <span class="tnum w-14 text-right font-medium text-fg">{{ fmt.formatDifficulty(row.difficulty) }}</span>
        </li>
      </ol>
    </div>
    <EmptyState v-else compact :icon="Trophy" title="No shares yet" description="Your best share appears once a miner has sent one to its pool." />
  </WidgetFrame>
</template>
