<script setup lang="ts">
import { Plus, Radar } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError, describeError } from '@/lib/api'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import { useUi } from '@/stores/ui'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Segmented from '@/components/ui/Segmented.vue'
import TagInput from '@/components/ui/TagInput.vue'
import DiscoveryPanel from './DiscoveryPanel.vue'

const ui = useUi()
const live = useLive()
const toasts = useToasts()
const router = useRouter()

const mode = ref<'scan' | 'address'>('scan')
const host = ref('')
const name = ref('')
const tags = ref<string[]>([])
const busy = ref(false)
const error = ref<string | null>(null)

const open = computed({ get: () => ui.addMinerOpen, set: (v: boolean) => (ui.addMinerOpen = v) })
const existingTags = computed(() => [...new Set(live.devices.flatMap((d) => d.tags))])

watch(open, (v) => {
  if (v) {
    error.value = null
    host.value = ''
    name.value = ''
    tags.value = []
  }
})

async function addByAddress(): Promise<void> {
  error.value = null
  if (!host.value.trim()) {
    error.value = 'Enter the miner’s IP address or host name.'
    return
  }
  busy.value = true
  try {
    const res = await api.addDevice({ host: host.value.trim(), name: name.value.trim() || undefined, tags: tags.value })
    live.upsertDevice(res.device)
    if (res.created) toasts.success(`Added ${res.device.name}`, `${res.device.model_override ?? res.device.model} at ${res.device.host}`)
    else toasts.info(`${res.device.name} was already monitored`, res.note ?? undefined)
    open.value = false
    void router.push(`/miners/${res.device.id}`)
  } catch (e) {
    error.value =
      e instanceof ApiError && e.code === 'no_miner_found'
        ? `${e.message} Open ${host.value.trim()} in a browser tab to confirm it is a miner and the address is right.`
        : describeError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open" title="Add miners" description="Find them automatically, or type an address." size="lg">
    <div class="space-y-5">
      <Segmented
        v-model="mode"
        label="How to add"
        :options="[
          { value: 'scan', label: 'Scan my network', icon: Radar },
          { value: 'address', label: 'Add by address', icon: Plus },
        ]"
      />

      <DiscoveryPanel v-if="mode === 'scan'" @adopted="(n) => n > 0 && (open = false)" @navigate="open = false" />

      <form v-else class="space-y-4" @submit.prevent="addByAddress">
        <Field label="Miner address" required hint="The IP address or name you use to open the miner’s own web page, for example 192.168.1.50 or bitaxe.local. Add :4028 for Avalon/Antminer style miners if needed.">
          <template #default="{ id, describedBy }">
            <Input :id="id" v-model="host" :described-by="describedBy" mono placeholder="192.168.1.50" autocomplete="off" data-testid="add-host" />
          </template>
        </Field>
        <Field label="Name (optional)" hint="Shown everywhere in the app. You can change it later.">
          <template #default="{ id, describedBy }"><Input :id="id" v-model="name" :described-by="describedBy" placeholder="Garage Gamma" /></template>
        </Field>
        <Field label="Tags (optional)" hint="Use tags to group miners, for example “garage” or “rack-1”.">
          <template #default="{ id }"><TagInput :id="id" v-model="tags" :suggestions="existingTags" /></template>
        </Field>
        <p v-if="error" class="rounded-xl border border-bad/30 bg-bad-soft px-3 py-2.5 text-sm text-bad" role="alert">{{ error }}</p>
        <Button type="submit" variant="primary" size="lg" class="w-full" :loading="busy" data-testid="add-submit">Add miner</Button>
      </form>
    </div>
  </Dialog>
</template>
