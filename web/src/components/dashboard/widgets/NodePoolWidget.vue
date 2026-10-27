<script setup lang="ts">
import { Network, Server, Unplug } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useNowSec } from '@/composables/useNowSec'
import { kindLabel } from '@/lib/labels'
import { useLive } from '@/stores/live'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const now = useNowSec()
const node = computed(() => live.network?.node ?? null)
const pools = computed(() => live.network?.pools ?? [])
const configured = computed(() => !!node.value || pools.value.length > 0)
const behind = computed(() => live.network?.node_behind_by ?? 0)
</script>

<template>
  <WidgetFrame title="Your node &amp; pool" to="/bitcoin" link-label="Details">
    <div v-if="configured" class="space-y-4" data-testid="widget-nodepool">
      <section v-if="node" class="space-y-2">
        <div class="flex items-center justify-between gap-2">
          <p class="flex items-center gap-2 text-sm font-medium text-fg"><Server class="size-4 text-muted" aria-hidden="true" /> Bitcoin Core</p>
          <Badge v-if="!node.reachable" tone="bad" dot size="sm">Unreachable</Badge>
          <Badge v-else-if="node.initial_block_download || (node.headers && node.blocks && node.headers - node.blocks > 2)" tone="warn" dot size="sm">Syncing</Badge>
          <Badge v-else-if="behind > 3" tone="warn" dot size="sm">{{ behind }} behind</Badge>
          <Badge v-else tone="ok" dot size="sm">Synced</Badge>
        </div>
        <ProgressBar v-if="node.reachable && node.verification_progress != null && node.verification_progress < 0.9999" :value="node.verification_progress" tone="info" :height="5" label="Sync progress" />
        <dl class="grid grid-cols-3 gap-2 text-xs">
          <div><dt class="text-subtle">Version</dt><dd class="tnum mt-0.5 truncate font-medium text-fg">{{ node.subversion?.replace(/\//g, '') ?? node.version ?? '–' }}</dd></div>
          <div><dt class="text-subtle">Peers</dt><dd class="tnum mt-0.5 font-medium text-fg">{{ node.connections ?? '–' }}</dd></div>
          <div><dt class="text-subtle">Mempool</dt><dd class="tnum mt-0.5 font-medium text-fg">{{ fmt.formatNumber(node.mempool_tx_count) }} tx</dd></div>
        </dl>
        <p v-if="node.error" class="text-xs text-bad">{{ node.error }}</p>
      </section>

      <section v-for="p in pools" :key="p.kind + (p.address ?? '')" class="space-y-2" :class="node && 'border-t border-line pt-4'">
        <div class="flex items-center justify-between gap-2">
          <p class="flex items-center gap-2 text-sm font-medium text-fg"><Network class="size-4 text-muted" aria-hidden="true" /> {{ p.name || kindLabel(p.kind) }}</p>
          <Badge :tone="p.reachable ? 'ok' : 'bad'" dot size="sm">{{ p.reachable ? 'Connected' : 'Unreachable' }}</Badge>
        </div>
        <dl class="grid grid-cols-3 gap-2 text-xs">
          <div><dt class="text-subtle">Your workers</dt><dd class="tnum mt-0.5 font-medium text-fg">{{ p.workers.length }}</dd></div>
          <div><dt class="text-subtle">Pool sees</dt><dd class="tnum mt-0.5 font-medium text-fg">{{ fmt.hashrate(p.hashrate_hs) }}</dd></div>
          <div><dt class="text-subtle">Last share</dt><dd class="tnum mt-0.5 font-medium text-fg">{{ p.last_share ? fmt.formatAgo(p.last_share, now) : '–' }}</dd></div>
        </dl>
        <p v-if="p.error" class="text-xs text-bad">{{ p.error }}</p>
      </section>
    </div>
    <EmptyState v-else compact :icon="Unplug" title="No node or pool connected" description="Connect your Bitcoin node or solo pool to see sync status, pool stats and to detect a found block the moment it happens.">
      <Button to="/settings/sources" variant="soft" size="sm">Connect one</Button>
    </EmptyState>
  </WidgetFrame>
</template>
