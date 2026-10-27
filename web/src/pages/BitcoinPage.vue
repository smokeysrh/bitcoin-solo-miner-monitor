<script setup lang="ts">
import { Blocks, Bitcoin, ExternalLink, Network, Server, Trophy, Unplug } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { kindLabel, sourceLabel } from '@/lib/labels'
import { useLive } from '@/stores/live'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import KeyValue from '@/components/ui/KeyValue.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import Stat from '@/components/ui/Stat.vue'
import Term from '@/components/ui/Term.vue'

const live = useLive()
const fmt = useFmt()
const now = useNowSec()

const n = computed(() => live.network)
const node = computed(() => n.value?.node ?? null)
const pools = computed(() => n.value?.pools ?? [])
const mine = computed(() => new Set(live.blocksFound.map((b) => b.hash)))
const sources = computed(() => n.value?.sources ?? [])
const synced = computed(() => !!node.value && node.value.reachable && !node.value.initial_block_download && !(node.value.headers && node.value.blocks && node.value.headers - node.value.blocks > 2))
const mempoolFill = computed(() => (node.value?.mempool_bytes && node.value.mempool_max_bytes ? node.value.mempool_bytes / node.value.mempool_max_bytes : null))
</script>

<template>
  <div class="space-y-5">
    <header>
      <h2 class="text-2xl font-semibold tracking-tight text-fg">Bitcoin network</h2>
      <p class="mt-1 text-sm text-muted">
        <template v-if="n?.available">Data from {{ sourceLabel(n.source) }}<span v-if="n.stale" class="text-warn"> (stale)</span></template>
        <template v-else>No network data yet</template>
      </p>
    </header>

    <div v-if="n?.available" class="grid gap-[var(--gap-grid)] sm:grid-cols-2 xl:grid-cols-4">
      <div class="card p-[var(--pad-card)]"><Stat label="Block height" :value="fmt.formatNumber(n.height)" :sub="n.tip_time ? `latest block ${fmt.formatAgo(n.tip_time, now)}` : undefined" size="lg" /></div>
      <div class="card p-[var(--pad-card)]">
        <Stat label="Difficulty" size="lg" :value="fmt.formatDifficulty(n.difficulty)" :sub="n.epoch?.estimated_change_pct != null ? `next change ${n.epoch.estimated_change_pct >= 0 ? '+' : ''}${n.epoch.estimated_change_pct.toFixed(2)}%` : undefined">
          <template #label><Term k="difficulty">Difficulty</Term></template>
        </Stat>
      </div>
      <div class="card p-[var(--pad-card)]"><Stat label="Network hashrate" size="lg" :value="fmt.splitHash(n.network_hashrate_hs).value" :unit="fmt.splitHash(n.network_hashrate_hs).unit" /></div>
      <div class="card p-[var(--pad-card)]"><Stat label="Bitcoin price" size="lg" :value="n.btc_price ? fmt.money(n.btc_price, 0) : '–'" :sub="`Block reward ${n.block_reward_btc ?? '–'} BTC`" /></div>
    </div>

    <div v-if="n?.available" class="grid gap-[var(--gap-grid)] lg:grid-cols-2">
      <MetricCard v-if="n.epoch" title="Difficulty adjustment" :icon="Network">
        <p class="text-sm text-muted">The <Term k="retarget">difficulty adjusts</Term> every 2,016 blocks so blocks keep arriving about every ten minutes.</p>
        <ProgressBar class="mt-4" :value="n.epoch.progress" tone="info" label="Progress to the next adjustment" />
        <div class="mt-4">
          <KeyValue :rows="[
            { label: 'Blocks until the change', value: `${fmt.formatNumber(n.epoch.blocks_remaining)} of 2,016` },
            { label: 'Expected in', value: `about ${fmt.formatDuration(n.epoch.seconds_remaining)}` },
            { label: 'Expected date', value: fmt.formatDate(n.epoch.estimated_date) },
            { label: 'Expected change', value: n.epoch.estimated_change_pct != null ? `${n.epoch.estimated_change_pct >= 0 ? '+' : ''}${n.epoch.estimated_change_pct.toFixed(2)}%` : 'not estimated yet', tone: (n.epoch.estimated_change_pct ?? 0) > 0 ? 'warn' : 'ok' },
          ]" />
        </div>
      </MetricCard>
      <MetricCard v-if="n.halving" title="Next halving" :icon="Bitcoin">
        <p class="text-sm text-muted">Every 210,000 blocks the new coins in each block are <Term k="halving">cut in half</Term>.</p>
        <ProgressBar class="mt-4" :value="n.halving.progress" tone="violet" label="Progress to the next halving" />
        <div class="mt-4">
          <KeyValue :rows="[
            { label: 'Blocks to go', value: fmt.formatNumber(n.halving.blocks_remaining) },
            { label: 'Expected in', value: `about ${fmt.formatDuration(n.halving.seconds_remaining)}` },
            { label: 'Expected date', value: fmt.formatDate(n.halving.estimated_date) },
            { label: 'Reward then', value: `${n.halving.subsidy_now_btc} → ${n.halving.subsidy_next_btc} BTC` },
          ]" />
        </div>
      </MetricCard>
    </div>

    <div class="grid gap-[var(--gap-grid)] lg:grid-cols-2">
      <MetricCard title="Your Bitcoin node" :icon="Server">
        <template v-if="node">
          <div class="mb-4 flex flex-wrap items-center gap-2">
            <Badge v-if="!node.reachable" tone="bad" dot>Unreachable</Badge>
            <Badge v-else-if="synced" tone="ok" dot>Synced</Badge>
            <Badge v-else tone="warn" dot>Syncing</Badge>
            <Badge v-if="node.chain && node.chain !== 'main'" tone="warn">{{ node.chain }} network</Badge>
            <Badge v-if="live.network?.node_behind_by" tone="warn">{{ live.network.node_behind_by }} blocks behind</Badge>
          </div>
          <ProgressBar v-if="node.verification_progress != null && node.verification_progress < 0.9999" :value="node.verification_progress" tone="info" label="Sync progress" class="mb-4" />
          <KeyValue :rows="[
            { label: 'Software', value: node.subversion?.replace(/\//g, '') ?? node.version ?? '–' },
            { label: 'Blocks', value: `${fmt.formatNumber(node.blocks)}${node.headers && node.headers !== node.blocks ? ` of ${fmt.formatNumber(node.headers)}` : ''}` },
            { label: 'Peers', value: node.connections != null ? `${node.connections}${node.connections_in != null ? ` (${node.connections_in} in, ${node.connections_out} out)` : ''}` : '–' },
            { label: 'Mempool', value: `${fmt.formatNumber(node.mempool_tx_count)} transactions${mempoolFill != null ? ` · ${(mempoolFill * 100).toFixed(0)}% full` : ''}` },
            { label: 'Disk used', value: fmt.formatBytes(node.size_on_disk) + (node.pruned ? ' (pruned)' : '') },
            { label: 'Running for', value: fmt.formatUptime(node.uptime_s) },
          ]" />
          <p v-for="w in node.warnings" :key="w" class="mt-3 text-xs text-warn">{{ w }}</p>
          <p v-if="node.error" class="mt-3 text-sm text-bad" role="alert">{{ node.error }}</p>
        </template>
        <EmptyState v-else compact :icon="Unplug" title="No node connected" description="Connect your own node for private network data, the earliest possible notice of a found block, and a health check on what you mine against.">
          <Button to="/settings/sources" variant="soft">Connect a node</Button>
        </EmptyState>
      </MetricCard>

      <MetricCard title="Your pool" :icon="Network">
        <template v-if="pools.length">
          <div v-for="p in pools" :key="p.kind + (p.address ?? '')" class="space-y-4 [&+&]:mt-6 [&+&]:border-t [&+&]:border-line [&+&]:pt-6">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-medium text-fg">{{ p.name || kindLabel(p.kind) }}</p>
              <Badge :tone="p.reachable ? 'ok' : 'bad'" dot size="sm">{{ p.reachable ? 'Connected' : 'Unreachable' }}</Badge>
            </div>
            <KeyValue :rows="[
              ...(p.pool_hashrate_hs != null ? [{ label: 'Whole pool', value: `${fmt.hashrate(p.pool_hashrate_hs)}${p.pool_miners ? ` · ${fmt.formatNumber(p.pool_miners)} miners` : ''}` }] : []),
              { label: 'Your hashrate (pool view)', value: fmt.hashrate(p.hashrate_hs) },
              { label: 'Your best share', value: `${fmt.formatDifficulty(p.best_difficulty)}${p.best_difficulty_ever ? ` · ever ${fmt.formatDifficulty(p.best_difficulty_ever)}` : ''}` },
              { label: 'Last share', value: p.last_share ? fmt.formatAgo(p.last_share, now) : '–' },
              ...(p.blocks_found != null ? [{ label: 'Blocks the pool found', value: fmt.formatNumber(p.blocks_found) }] : []),
            ]" />
            <div v-if="p.workers.length" class="relative overflow-x-auto">
              <table class="w-full text-sm">
                <thead><tr class="text-left text-xs text-subtle"><th class="pb-2 font-medium">Worker</th><th class="pb-2 text-right font-medium">Hashrate</th><th class="pb-2 text-right font-medium">Best share</th><th class="pb-2 text-right font-medium">Seen</th></tr></thead>
                <tbody>
                  <tr v-for="w in p.workers" :key="w.name" class="border-t border-line/60">
                    <td class="max-w-[10rem] truncate py-2 pr-3 text-fg">{{ w.name }}</td>
                    <td class="tnum py-2 text-right text-muted">{{ fmt.hashrate(w.hashrate_hs) }}</td>
                    <td class="tnum py-2 text-right text-muted">{{ fmt.formatDifficulty(w.best_difficulty) }}</td>
                    <td class="tnum py-2 text-right text-subtle">{{ w.last_seen ? fmt.formatAgo(w.last_seen, now) : '–' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-if="p.error" class="text-sm text-bad" role="alert">{{ p.error }}</p>
          </div>
        </template>
        <EmptyState v-else compact :icon="Unplug" title="No pool connected" description="Add Public Pool, ckpool or similar to see what the pool sees: your workers, their hashrate and best shares.">
          <Button to="/settings/sources" variant="soft">Connect a pool</Button>
        </EmptyState>
      </MetricCard>
    </div>

    <div class="grid gap-[var(--gap-grid)] lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <MetricCard title="Latest blocks" :icon="Blocks">
        <div v-if="live.recentBlocks.length" class="relative overflow-x-auto">
          <table class="w-full min-w-[420px] text-sm">
            <thead><tr class="text-left text-xs text-subtle"><th class="pb-2 font-medium">Height</th><th class="pb-2 font-medium">Found by</th><th class="pb-2 text-right font-medium">Transactions</th><th class="pb-2 text-right font-medium">Age</th><th class="w-8" /></tr></thead>
            <tbody>
              <tr v-for="b in live.recentBlocks" :key="b.hash" class="border-t border-line/60">
                <td class="tnum py-2.5 pr-3 font-medium text-fg">{{ fmt.formatNumber(b.height) }} <Badge v-if="b.yours || mine.has(b.hash)" tone="accent" size="sm" class="ml-1">You</Badge></td>
                <td class="max-w-[12rem] truncate py-2.5 pr-3 text-muted">{{ b.pool_name ?? 'Unknown' }}</td>
                <td class="tnum py-2.5 text-right text-muted">{{ fmt.formatNumber(b.tx_count) }}</td>
                <td class="tnum py-2.5 text-right text-subtle">{{ fmt.formatAgo(b.ts, now) }}</td>
                <td class="py-2.5 text-right"><a :href="`https://mempool.space/block/${b.hash}`" target="_blank" rel="noopener noreferrer" class="text-subtle hover:text-fg" :aria-label="`Block ${b.height} on mempool.space`"><ExternalLink class="size-3.5" /></a></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="text-sm text-muted">Recent blocks appear once network data is available.</p>
      </MetricCard>

      <div class="space-y-[var(--gap-grid)]">
        <MetricCard title="Blocks you found" :icon="Trophy">
          <ul v-if="live.blocksFound.length" class="space-y-3">
            <li v-for="b in live.blocksFound" :key="b.hash" class="rounded-xl border border-accent-line bg-accent-softer p-3">
              <p class="tnum text-sm font-semibold text-fg">Block {{ fmt.formatNumber(b.height) }}</p>
              <p class="mt-0.5 text-xs text-muted">{{ fmt.formatDateTime(b.ts) }}<template v-if="b.reward_sats"> · {{ fmt.formatBtc(b.reward_sats / 1e8) }}</template></p>
            </li>
          </ul>
          <p v-else class="text-sm leading-relaxed text-muted">None yet. When it happens you will see it here, on the dashboard and in every notification channel you set up.</p>
        </MetricCard>
        <MetricCard title="Data sources" subtitle="Where the numbers above come from">
          <ul class="space-y-2.5">
            <li v-for="s in sources" :key="s.id" class="flex items-center gap-2.5 text-sm">
              <span class="size-2 shrink-0 rounded-full" :class="s.ok === null ? 'bg-subtle' : s.ok ? 'bg-ok' : 'bg-bad'" aria-hidden="true" />
              <span class="min-w-0 flex-1 truncate text-fg">{{ s.name }}</span>
              <span class="shrink-0 text-xs" :class="s.ok === false ? 'text-bad' : 'text-subtle'">{{ s.ok === false ? (s.error ?? 'not answering') : s.last_ok ? fmt.formatAgo(s.last_ok, now) : 'waiting' }}</span>
            </li>
          </ul>
          <RouterLink to="/settings/sources" class="mt-4 inline-block text-xs font-medium text-accent-text underline underline-offset-2 hover:no-underline">Manage data sources</RouterLink>
        </MetricCard>
      </div>
    </div>
  </div>
</template>
