<script setup lang="ts">
import { computed } from 'vue'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Term from '@/components/ui/Term.vue'
import ToggleRow from '@/components/ui/ToggleRow.vue'
import { confirmDialog } from '@/composables/useConfirm'
import { useFmt } from '@/composables/useFmt'
import { useSectionForm } from '@/composables/useSectionForm'
import { describeError } from '@/lib/api'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const settings = useSettings()
const session = useSession()
const toasts = useToasts()
const fmt = useFmt()
const admin = computed(() => session.canAdmin)
const safety = useSectionForm('safety')

async function setControl(on: boolean): Promise<void> {
  try {
    await settings.patch({ safety: { allow_control: on } })
  } catch (e) {
    toasts.error('Could not save that', describeError(e))
  }
}

async function setTuning(on: boolean): Promise<void> {
  if (on) {
    const ok = await confirmDialog({
      title: 'Allow speed and voltage changes?',
      message: 'Pushing a miner harder makes more heat and can shorten its life or damage it. The app only offers values the miner itself lists as supported, and refuses to tune one that is already hot. You stay responsible for cooling and power.',
      confirmLabel: 'I understand, allow it',
      tone: 'danger',
    })
    if (!ok) return
  }
  try {
    await settings.patch({ safety: { allow_tuning: on } })
  } catch (e) {
    toasts.error('Could not save that', describeError(e))
  }
}
</script>

<template>
  <SettingsCard title="What this app may change on your miners" description="By default it can restart miners, flash them and change pools. Anything riskier is off until you switch it on. These rules also apply to API tokens and AI agents.">
    <div class="divide-y divide-line">
      <ToggleRow :model-value="settings.data?.safety.allow_control ?? true" :disabled="!admin" title="Allow control" description="Restart, pause, identify, change pool and fan. Turn this off for a watch-only dashboard that can never touch a miner." @update:model-value="setControl" />
      <ToggleRow :model-value="settings.data?.safety.allow_tuning ?? false" :disabled="!admin || !(settings.data?.safety.allow_control ?? true)" title="Allow speed and voltage changes" description="Overclocking. Off by default." @update:model-value="setTuning">
        <span class="mt-1 block text-xs text-subtle"><Term k="frequency">Frequency</Term> and <Term k="coreVoltage">voltage</Term> are only ever set to values the miner says are supported.</span>
      </ToggleRow>
    </div>
  </SettingsCard>

  <SettingsCard
    title="Temperature limit"
    description="The app will not tune a miner that is already this hot, and agents are told to back off."
    show-save
    :dirty="safety.dirty.value"
    :saving="safety.saving.value"
    :error="safety.error.value"
    @save="safety.save()"
    @discard="safety.discard()"
  >
    <Field :label="`Limit: ${fmt.temp(Number(safety.form.max_temp_c))}`" hint="Between 50 and 110 °C. ASIC chips like the BM1370 are normally comfortable below 75 °C.">
      <template #default="{ id, describedBy }">
        <Input :id="id" v-model="safety.form.max_temp_c" type="number" :min="50" :max="110" suffix="°C" :described-by="describedBy" :disabled="!admin" class="max-w-40" />
      </template>
    </Field>
  </SettingsCard>
</template>
