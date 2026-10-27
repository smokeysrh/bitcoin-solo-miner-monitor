<script setup lang="ts">
import { CircleCheck, CircleX, ExternalLink, RefreshCw, TriangleAlert } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import CopyButton from '@/components/ui/CopyButton.vue'
import KeyValue from '@/components/ui/KeyValue.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useFmt } from '@/composables/useFmt'
import { api, describeError } from '@/lib/api'
import type { Diagnostics, SystemInfo, UpdateStatus } from '@/lib/types'
import { useSession } from '@/stores/session'
import { useToasts } from '@/stores/toasts'

const fmt = useFmt()
const session = useSession()
const toasts = useToasts()
const info = ref<SystemInfo | null>(null)
const update = ref<UpdateStatus | null>(null)
const diag = ref<Diagnostics | null>(null)
const checking = ref(false)
const running = ref(false)

async function runDiagnostics(): Promise<void> {
  running.value = true
  try {
    diag.value = await api.diagnostics()
  } catch (e) {
    toasts.error('Could not run the checks', describeError(e))
  } finally {
    running.value = false
  }
}
async function checkUpdate(): Promise<void> {
  checking.value = true
  try {
    update.value = await api.checkUpdate()
  } catch (e) {
    toasts.error('Could not check for updates', describeError(e))
  } finally {
    checking.value = false
  }
}
onMounted(async () => {
  void runDiagnostics()
  try {
    ;[info.value, update.value] = await Promise.all([api.systemInfo(), api.updateStatus()])
  } catch {
    /* shown as blanks */
  }
})

const icon = { pass: CircleCheck, warn: TriangleAlert, fail: CircleX } as const
const tone = { pass: 'text-ok', warn: 'text-warn', fail: 'text-bad' } as const
</script>

<template>
  <SettingsCard title="Solo Miner Monitor">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="tnum text-3xl font-bold tracking-tight text-fg" data-testid="version">{{ info?.version ?? session.meta?.version ?? '…' }}</p>
        <p v-if="update?.update_available" class="mt-2 text-sm text-ok">Version {{ update.latest }} is available. <a v-if="update.url" :href="update.url" target="_blank" rel="noopener noreferrer" class="underline">See what is new</a></p>
        <p v-else-if="update?.disabled" class="mt-2 text-sm text-muted">Update checks are off in this mode.</p>
        <p v-else-if="update?.error" class="mt-2 text-sm text-warn">{{ update.error }}</p>
        <p v-else-if="update" class="mt-2 text-sm text-muted">You are up to date.</p>
      </div>
      <Button variant="secondary" size="sm" :loading="checking" :disabled="update?.disabled" @click="checkUpdate"><template #icon><RefreshCw class="size-4" /></template>Check for updates</Button>
    </div>
    <div v-if="info" class="mt-5 border-t border-line pt-5">
      <KeyValue :rows="[
        { label: 'Running for', value: fmt.formatUptime(info.uptime_s) },
        { label: 'Computer', value: info.platform },
        { label: 'Python', value: info.python },
        { label: 'Miners watched', value: String(info.devices) },
        { label: 'Open dashboards', value: String(info.stream_subscribers) },
        { label: 'Mode', value: info.demo ? 'Demo (simulated)' : info.offline_mode ? 'Offline (no internet lookups)' : 'Normal' },
      ]" />
    </div>
    <div class="mt-5 flex flex-wrap gap-x-5 gap-y-2 border-t border-line pt-4 text-sm">
      <a v-for="l in [['Interactive API docs', '/docs'], ['OpenAPI schema', '/openapi.json'], ['Instructions for AI agents', '/llms.txt'], ['Metrics for Prometheus', '/metrics'], ['Project on GitHub', 'https://github.com/smokeysrh/bitcoin-solo-miner-monitor'], ['Report a problem', 'https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues']]" :key="l[0]" :href="l[1]" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-accent-text underline underline-offset-2 hover:no-underline">{{ l[0] }}<ExternalLink class="size-3" aria-hidden="true" /></a>
    </div>
  </SettingsCard>

  <SettingsCard title="Health check" description="Looks for the usual problems: wrong network range, firewalls, unreachable miners, data sources that are not answering.">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <Badge v-if="diag" :tone="diag.ok ? 'ok' : 'warn'" dot>{{ diag.ok ? 'Everything looks fine' : 'Some things need a look' }}</Badge>
      <span v-else />
      <div class="flex gap-2">
        <CopyButton v-if="diag" :text="JSON.stringify(diag, null, 2)" label="Copy report" variant="secondary" size="sm" what="Report copied. Paste it into a bug report." />
        <Button variant="secondary" size="sm" :loading="running" @click="runDiagnostics"><template #icon><RefreshCw class="size-4" /></template>Run again</Button>
      </div>
    </div>
    <div v-if="!diag" class="space-y-2"><Skeleton v-for="i in 4" :key="i" class="h-12 rounded-xl" /></div>
    <ul v-else class="divide-y divide-line rounded-xl border border-line" data-testid="checks">
      <li v-for="c in diag.checks" :key="c.id" class="flex items-start gap-3 px-4 py-3">
        <component :is="icon[c.status]" :class="['mt-0.5 size-4.5 shrink-0', tone[c.status]]" aria-hidden="true" />
        <div class="min-w-0">
          <p class="text-sm text-fg">{{ c.message }}</p>
          <p v-if="c.fix && c.status !== 'pass'" class="mt-1 text-xs leading-relaxed text-muted">{{ c.fix }}</p>
        </div>
      </li>
    </ul>
    <p v-if="diag?.lan_networks.length" class="mt-4 text-xs text-subtle">Networks this computer is on: <span class="font-mono">{{ diag.lan_networks.join(', ') }}</span> · listening on <span class="font-mono">{{ diag.listening }}</span></p>
  </SettingsCard>
</template>
