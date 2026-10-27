<script setup lang="ts">
import { Fan, ShieldAlert, SlidersHorizontal } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { confirmDialog } from '@/composables/useConfirm'
import { useMinerActions } from '@/composables/useMinerActions'
import { api, describeError } from '@/lib/api'
import type { DeviceView, TuningInfo } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import Term from '@/components/ui/Term.vue'
import KeyValue from '@/components/ui/KeyValue.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

const props = defineProps<{ device: DeviceView }>()
const fmt = useFmt()
const live = useLive()
const toasts = useToasts()
const actions = useMinerActions()

const info = ref<TuningInfo | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const busy = ref(false)
const fanBusy = ref(false)
const form = reactive<{ frequency: number | null; voltage: number | null }>({ frequency: null, voltage: null })
const fan = reactive({ auto: true, speed: 60, target: 60 })

const canTune = computed(() => actions.can(props.device, 'set_frequency'))
const canFan = computed(() => actions.can(props.device, 'set_fan'))
const t = computed(() => props.device.telemetry)

async function load(): Promise<void> {
  loading.value = true
  loadError.value = null
  try {
    info.value = await api.deviceTuning(props.device.id)
    form.frequency = info.value.current?.frequency_mhz != null ? Math.round(info.value.current.frequency_mhz) : null
    form.voltage = info.value.current?.core_voltage_mv != null ? Math.round(info.value.current.core_voltage_mv) : null
  } catch (e) {
    loadError.value = describeError(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => props.device.id, load)

const opts = computed(() => info.value?.options ?? null)
const label = (v: number, def: number | null | undefined, unit: string): string => `${v} ${unit}${v === def ? ' (default)' : ''}`
const freqOptions = computed(() => (opts.value?.frequency_mhz ?? []).map((v) => ({ value: v, label: label(v, opts.value?.default_frequency_mhz, 'MHz') })))
const voltOptions = computed(() => (opts.value?.core_voltage_mv ?? []).map((v) => ({ value: v, label: label(v, opts.value?.default_core_voltage_mv, 'mV') })))
const changed = computed(() => {
  const cur = info.value?.current
  return form.frequency !== Math.round(cur?.frequency_mhz ?? -1) || form.voltage !== Math.round(cur?.core_voltage_mv ?? -1)
})

function toDefaults(): void {
  if (!opts.value) return
  form.frequency = opts.value.default_frequency_mhz ?? form.frequency
  form.voltage = opts.value.default_core_voltage_mv ?? form.voltage
}

async function apply(): Promise<void> {
  const cur = info.value?.current
  const params: Record<string, number> = {}
  if (form.frequency != null && form.frequency !== Math.round(cur?.frequency_mhz ?? -1)) params.frequency_mhz = form.frequency
  if (form.voltage != null && form.voltage !== Math.round(cur?.core_voltage_mv ?? -1)) params.core_voltage_mv = form.voltage
  if (!Object.keys(params).length) return
  const ok = await confirmDialog({
    title: `Change tuning on ${props.device.name}?`,
    message: `${params.frequency_mhz ? `Frequency ${Math.round(cur?.frequency_mhz ?? 0)} → ${params.frequency_mhz} MHz. ` : ''}${params.core_voltage_mv ? `Voltage ${Math.round(cur?.core_voltage_mv ?? 0)} → ${params.core_voltage_mv} mV. ` : ''}More speed means more heat and power. Watch the temperature for the next few minutes.`,
    confirmLabel: 'Apply',
    tone: 'danger',
  })
  if (!ok) return
  busy.value = true
  try {
    const res = await api.action(props.device.id, 'set_tuning', params)
    toasts.success('Tuning changed', res.message ?? 'Give it a minute to settle.')
    live.upsertDevice(await api.pollDevice(props.device.id))
    await load()
  } catch (e) {
    toasts.error('Could not change tuning', describeError(e))
  } finally {
    busy.value = false
  }
}

async function applyFan(): Promise<void> {
  fanBusy.value = true
  try {
    const params = fan.auto ? { auto: true, temp_target_c: fan.target } : { auto: false, speed_pct: fan.speed }
    const res = await api.action(props.device.id, 'set_fan', params)
    toasts.success('Fan updated', res.message)
    live.upsertDevice(await api.pollDevice(props.device.id))
  } catch (e) {
    toasts.error('Could not change the fan', describeError(e))
  } finally {
    fanBusy.value = false
  }
}
</script>

<template>
  <div class="grid gap-[var(--gap-grid)] xl:grid-cols-2">
    <MetricCard title="Speed &amp; voltage" :icon="SlidersHorizontal">
      <div v-if="loading" class="skeleton h-40" aria-busy="true" />
      <p v-else-if="loadError" class="text-sm text-bad" role="alert">{{ loadError }}</p>
      <template v-else-if="info">
        <div v-if="!info.tuning_enabled_in_settings" class="mb-4 flex gap-3 rounded-xl border border-warn/30 bg-warn-soft p-4">
          <ShieldAlert class="mt-0.5 size-5 shrink-0 text-warn" aria-hidden="true" />
          <div class="text-sm">
            <p class="font-medium text-fg">Tuning is switched off</p>
            <p class="mt-1 leading-relaxed text-muted">
              Changing <Term k="frequency">frequency</Term> and <Term k="coreVoltage">voltage</Term> can overheat or damage a miner, so it stays off until you allow it.
            </p>
            <Button to="/settings/safety" size="sm" variant="secondary" class="mt-3">Open Safety settings</Button>
          </div>
        </div>

        <p v-if="!opts" class="text-sm text-muted">This miner's firmware does not publish a list of safe values, so tuning is not offered for it.</p>
        <form v-else class="space-y-4" @submit.prevent="apply">
          <div class="grid gap-3 sm:grid-cols-2">
            <Field label="Frequency">
              <template #default="{ id }"><Select :id="id" v-model="form.frequency" :options="freqOptions" :disabled="!canTune || !info.tuning_enabled_in_settings" /></template>
            </Field>
            <Field label="Core voltage">
              <template #default="{ id }"><Select :id="id" v-model="form.voltage" :options="voltOptions" :disabled="!canTune || !info.tuning_enabled_in_settings" /></template>
            </Field>
          </div>
          <KeyValue
            :rows="[
              { label: 'Now delivering', value: `${fmt.hashrate(info.current?.hashrate_hs)} at ${fmt.formatPower(info.current?.power_w)}` },
              { label: 'Efficiency', value: fmt.formatEfficiency(info.current?.efficiency_j_th) },
              { label: 'Chip temperature', value: fmt.temp(info.current?.temp_asic_c, 1) },
              ...(opts.max_temp_c ? [{ label: 'Safe limit (miner)', value: fmt.temp(opts.max_temp_c) }] : []),
              ...(opts.max_power_w ? [{ label: 'Power limit (miner)', value: fmt.formatPower(opts.max_power_w) }] : []),
            ]"
          />
          <p class="text-xs leading-relaxed text-subtle">Only values the miner itself lists as supported can be chosen. After a change, give it a few minutes and watch temperature and rejected shares.</p>
          <div class="flex flex-wrap gap-2">
            <Button type="submit" variant="primary" :loading="busy" :disabled="!canTune || !info.tuning_enabled_in_settings || !changed">Apply</Button>
            <Button type="button" variant="ghost" :disabled="!canTune || !info.tuning_enabled_in_settings" @click="toDefaults">Use defaults</Button>
          </div>
        </form>
      </template>
    </MetricCard>

    <MetricCard title="Cooling" :icon="Fan">
      <template v-if="canFan">
        <form class="space-y-4" @submit.prevent="applyFan">
          <label class="flex items-center justify-between gap-3 text-sm text-fg">
            <span>
              Automatic fan control
              <span class="block text-xs text-subtle">The miner raises the fan speed to hold a target temperature.</span>
            </span>
            <Switch v-model="fan.auto" label="Automatic fan control" />
          </label>
          <Field v-if="fan.auto" :label="`Target temperature: ${fmt.temp(fan.target)}`" hint="Between 30 and 85 °C. Lower runs the fan harder and the chip cooler.">
            <template #default="{ id }"><input :id="id" v-model.number="fan.target" type="range" min="30" max="85" step="1" class="w-full accent-[var(--accent)]" /></template>
          </Field>
          <Field v-else :label="`Fan speed: ${fan.speed}%`" hint="Fixed speed. Keep an eye on the chip temperature.">
            <template #default="{ id }"><input :id="id" v-model.number="fan.speed" type="range" min="0" max="100" step="5" class="w-full accent-[var(--accent)]" /></template>
          </Field>
          <p class="text-xs text-subtle">Now: {{ t?.fan_pct != null ? `${Math.round(t.fan_pct)}%` : '–' }} · {{ t?.fan_rpm != null ? `${Math.round(t.fan_rpm)} rpm` : '–' }}</p>
          <Button type="submit" variant="primary" :loading="fanBusy">Apply fan settings</Button>
        </form>
      </template>
      <p v-else class="text-sm text-muted">Fan control is not available for this miner.</p>
    </MetricCard>
  </div>
</template>
