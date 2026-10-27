<script setup lang="ts">
import { computed } from 'vue'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Segmented from '@/components/ui/Segmented.vue'
import Select from '@/components/ui/Select.vue'
import TagInput from '@/components/ui/TagInput.vue'
import ToggleRow from '@/components/ui/ToggleRow.vue'
import { useSectionForm } from '@/composables/useSectionForm'
import { describeError } from '@/lib/api'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const settings = useSettings()
const session = useSession()
const toasts = useToasts()

const general = useSectionForm('general')
const polling = useSectionForm('polling')
const mining = useSectionForm('mining')
const admin = computed(() => session.canAdmin)

async function patch(change: Parameters<typeof settings.patch>[0]): Promise<void> {
  try {
    await settings.patch(change)
  } catch (e) {
    toasts.error('Could not save that', describeError(e))
  }
}
const currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'CHF', 'JPY', 'SEK', 'NOK', 'DKK', 'PLN', 'BRL', 'MXN', 'INR'].map((c) => ({ value: c, label: c }))
</script>

<template>
  <SettingsCard title="Name" description="Shown at the top of the dashboard and in notifications." show-save :dirty="general.dirty.value" :saving="general.saving.value" :error="general.error.value" @save="general.save()" @discard="general.discard()">
    <Field label="Name of this setup">
      <template #default="{ id }"><Input :id="id" v-model="general.form.instance_name" :disabled="!admin" placeholder="My solo mining fleet" /></template>
    </Field>
  </SettingsCard>

  <SettingsCard title="Units" description="How numbers are shown across the app.">
    <div class="grid gap-5 sm:grid-cols-3">
      <Field label="Temperature">
        <template #default>
          <Segmented :model-value="settings.data?.units.temperature ?? 'c'" label="Temperature unit" :options="[{ value: 'c', label: '°C' }, { value: 'f', label: '°F' }]" @update:model-value="(v) => patch({ units: { temperature: v as 'c' | 'f' } })" />
        </template>
      </Field>
      <Field label="Hashrate">
        <template #default="{ id }">
          <Select :id="id" :model-value="settings.data?.units.hashrate ?? 'auto'" :options="[{ value: 'auto', label: 'Automatic' }, { value: 'gh', label: 'Always GH/s' }, { value: 'th', label: 'Always TH/s' }, { value: 'ph', label: 'Always PH/s' }]" :disabled="!admin" @update:model-value="(v) => patch({ units: { hashrate: v as 'auto' } })" />
        </template>
      </Field>
      <Field label="Currency" hint="For electricity cost and Bitcoin price.">
        <template #default="{ id }"><Select :id="id" :model-value="settings.data?.units.currency ?? 'USD'" :options="currencies" :disabled="!admin" @update:model-value="(v) => patch({ units: { currency: String(v) } })" /></template>
      </Field>
    </div>
  </SettingsCard>

  <SettingsCard title="Beginner-friendly mode" description="Hides the extra details and keeps the dashboard to the essentials. You can switch back any time.">
    <ToggleRow :model-value="settings.simple" title="Simple mode" description="Fewer widgets on the dashboard and plainer wording." @update:model-value="(v) => patch({ ui: { simple_mode: v } })" />
  </SettingsCard>

  <SettingsCard
    title="How often to check miners"
    description="The defaults suit most setups. Checking more often gives smoother charts but is a little more network traffic."
    show-save
    :dirty="polling.dirty.value"
    :saving="polling.saving.value"
    :error="polling.error.value"
    @save="polling.save()"
    @discard="polling.discard()"
  >
    <div class="grid gap-5 sm:grid-cols-2">
      <Field label="Online miners" hint="Seconds between checks."><template #default="{ id, describedBy }"><Input :id="id" v-model="polling.form.interval_s" type="number" :min="2" :max="600" suffix="s" :described-by="describedBy" :disabled="!admin" /></template></Field>
      <Field label="Offline miners" hint="How often to retry one that stopped answering."><template #default="{ id, describedBy }"><Input :id="id" v-model="polling.form.offline_interval_s" type="number" :min="5" :max="3600" suffix="s" :described-by="describedBy" :disabled="!admin" /></template></Field>
      <Field label="Give up waiting after" hint="A slow WiFi miner may need longer."><template #default="{ id, describedBy }"><Input :id="id" v-model="polling.form.timeout_s" type="number" :min="1" :max="60" suffix="s" :described-by="describedBy" :disabled="!admin" /></template></Field>
      <Field label="Mark offline after" hint="Failed checks in a row before a miner counts as offline."><template #default="{ id, describedBy }"><Input :id="id" v-model="polling.form.offline_after_failures" type="number" :min="1" :max="20" suffix="tries" :described-by="describedBy" :disabled="!admin" /></template></Field>
    </div>
  </SettingsCard>

  <SettingsCard
    title="Your payout addresses"
    description="Bitcoin addresses to watch for found blocks, in addition to the ones your miners already use. Optional."
    show-save
    :dirty="mining.dirty.value"
    :saving="mining.saving.value"
    :error="mining.error.value"
    @save="mining.save()"
    @discard="mining.discard()"
  >
    <Field label="Addresses" hint="Press Enter after each address. They are only watched, never used to spend anything.">
      <template #default="{ id }"><TagInput :id="id" v-model="mining.form.addresses" raw placeholder="bc1q…" /></template>
    </Field>
  </SettingsCard>
</template>
