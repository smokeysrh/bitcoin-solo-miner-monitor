<script setup lang="ts">
import { OctagonAlert } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useMinerMonitor } from '@/composables/useMinerMonitor'
import { useNowSec } from '@/composables/useNowSec'
import { poolChangeText as words, slotLabel } from '@/lib/poolChangeText'
import type { DeviceView } from '@/lib/types'
import { useSession } from '@/stores/session'
import Button from '@/components/ui/Button.vue'

const props = defineProps<{ device: DeviceView }>()
const fmt = useFmt()
const now = useNowSec()
const monitor = useMinerMonitor()
const session = useSession()

const change = computed(() => props.device.pool_change ?? null)
const busy = ref(false)

async function accept(): Promise<void> {
  busy.value = true
  try {
    await monitor.acceptPoolChange(props.device)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section v-if="change" class="flex gap-3 rounded-2xl border border-bad/30 bg-bad-soft p-4" role="alert" data-testid="pool-change-notice">
    <OctagonAlert class="mt-0.5 size-5 shrink-0 text-bad" aria-hidden="true" />
    <div class="min-w-0 flex-1 text-sm">
      <p class="font-medium text-fg">{{ words.noticeTitle }}</p>
      <p class="mt-0.5 text-muted">{{ words.noticeIntro }} {{ words.since(fmt.formatAgo(change.since_ts, now)) }}</p>
      <ul class="mt-3 space-y-2">
        <li v-for="c in change.changes" :key="c.slot + c.setting" class="rounded-xl border border-line bg-surface-2/50 p-3" data-testid="pool-change-row">
          <p class="text-xs font-medium text-muted">{{ slotLabel(c.slot) }} · {{ words.settingLabels[c.setting] ?? c.setting }}</p>
          <dl class="mt-1 grid gap-x-4 gap-y-1 sm:grid-cols-2">
            <div class="min-w-0">
              <dt class="text-xs text-subtle">{{ words.beforeLabel }}</dt>
              <dd class="font-mono text-[13px] break-all text-fg" data-testid="pool-change-old">{{ c.old ?? words.absent }}</dd>
            </div>
            <div class="min-w-0">
              <dt class="text-xs text-subtle">{{ words.nowLabel }}</dt>
              <dd class="font-mono text-[13px] break-all text-fg" data-testid="pool-change-new">{{ c.new ?? words.absent }}</dd>
            </div>
          </dl>
        </li>
      </ul>
      <div class="mt-3">
        <Button v-if="session.canControl" size="sm" variant="primary" :loading="busy" data-testid="accept-pool-change" @click="accept">
          {{ busy ? words.acceptBusy : words.acceptButton }}
        </Button>
        <p v-else class="text-[13px] text-muted">{{ words.readOnlyNote }}</p>
      </div>
    </div>
  </section>
</template>
