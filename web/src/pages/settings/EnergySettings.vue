<script setup lang="ts">
import { computed, onMounted } from 'vue'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Segmented from '@/components/ui/Segmented.vue'
import Term from '@/components/ui/Term.vue'
import { useFmt } from '@/composables/useFmt'
import { useSectionForm } from '@/composables/useSectionForm'
import { describeError } from '@/lib/api'
import { useInsights } from '@/stores/insights'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const settings = useSettings()
const session = useSession()
const live = useLive()
const fmt = useFmt()
const insights = useInsights()
const toasts = useToasts()

const energy = useSectionForm('energy')
const network = useSectionForm('network')
const admin = computed(() => session.canAdmin)

onMounted(() => void insights.refresh(true))
async function confirmRate(): Promise<void> {
  try {
    // sending the price is what marks it as confirmed on the server
    await settings.patch({ energy: { price_per_kwh: Number(energy.form.price_per_kwh) } })
    await insights.refresh(true)
  } catch (e) {
    toasts.error('Could not save that', describeError(e))
  }
}

const watts = computed(() => (live.summary?.power_w ?? 0) * (1 + Number(energy.form.psu_overhead_pct ?? 0) / 100))
const perMonth = computed(() => (watts.value / 1000) * 24 * 30.4375 * Number(energy.form.price_per_kwh ?? 0))
</script>

<template>
  <SettingsCard
    title="Electricity"
    description="Used for every cost figure in the app. Find your rate on an electricity bill: it is usually written per kWh."
    show-save
    :dirty="energy.dirty.value"
    :saving="energy.saving.value"
    :error="energy.error.value"
    @save="energy.save()"
    @discard="energy.discard()"
  >
    <div class="grid gap-5 sm:grid-cols-2">
      <Field label="Price per kWh" :hint="`In ${settings.currency}. Example: 0.14`" required>
        <template #default="{ id, describedBy }"><Input :id="id" v-model="energy.form.price_per_kwh" type="number" :min="0" :step="0.01" :prefix="settings.currency" :described-by="describedBy" :disabled="!admin" data-testid="price-kwh" /></template>
      </Field>
      <Field label="Power supply waste" hint="Power supplies lose some energy as heat, so the wall draws more than the miner reports. 10% suits a decent supply.">
        <template #default="{ id, describedBy }">
          <Input :id="id" v-model="energy.form.psu_overhead_pct" type="number" :min="0" :max="100" suffix="%" :described-by="describedBy" :disabled="!admin" />
        </template>
      </Field>
    </div>
    <p v-if="insights.has('energy-default')" class="mt-5 flex flex-wrap items-center gap-3 rounded-xl border border-accent-line bg-accent-softer px-4 py-3 text-sm text-muted">
      This is still the starting value. If it already matches your bill, confirm it so the reminder goes away.
      <Button size="xs" variant="soft" @click="confirmRate">That is my rate</Button>
    </p>
    <p v-if="live.summary?.power_w" class="mt-5 rounded-xl border border-line bg-surface-2/60 px-4 py-3 text-sm text-muted">
      With <b class="text-fg">{{ fmt.formatPower(watts) }}</b> at the wall, that is about <b class="text-fg">{{ fmt.money(perMonth) }}</b> a month. <Term k="psu">What is power supply waste?</Term>
    </p>
  </SettingsCard>

  <SettingsCard
    title="Bitcoin data for the maths"
    description="The odds calculator needs the network difficulty and, for costs, a Bitcoin price."
    show-save
    :dirty="network.dirty.value"
    :saving="network.saving.value"
    :error="network.error.value"
    @save="network.save()"
    @discard="network.discard()"
  >
    <div class="grid gap-5 sm:grid-cols-2">
      <Field label="Bitcoin price from">
        <template #default>
          <Segmented v-model="network.form.price_source" label="Price source" :options="[{ value: 'mempool', label: 'mempool.space' }, { value: 'manual', label: 'My own number' }, { value: 'none', label: 'Don’t use' }]" />
        </template>
      </Field>
      <Field v-if="network.form.price_source === 'manual'" label="Price to use" :hint="`${settings.currency} per bitcoin`">
        <template #default="{ id, describedBy }"><Input :id="id" v-model="network.form.manual_btc_price" type="number" :min="0" :described-by="describedBy" :disabled="!admin" /></template>
      </Field>
      <Field label="Network growth per year" hint="If the network keeps getting faster your odds shrink over time. 0.3 means 30% faster each year. 0 ignores growth.">
        <template #default="{ id, describedBy }"><Input :id="id" v-model="network.form.difficulty_growth_per_year" type="number" :min="0" :max="5" :step="0.05" :described-by="describedBy" :disabled="!admin" /></template>
      </Field>
      <Field label="Average fees per block (BTC)" hint="Leave empty to use what the network is paying right now.">
        <template #default="{ id, describedBy }"><Input :id="id" v-model="network.form.avg_block_fees_btc" type="number" :min="0" :step="0.01" :described-by="describedBy" :disabled="!admin" placeholder="automatic" /></template>
      </Field>
    </div>
  </SettingsCard>
</template>
