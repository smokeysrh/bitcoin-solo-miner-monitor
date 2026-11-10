import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { pendingConfirm } from '@/composables/useConfirm'
import { api } from '@/lib/api'
import type { ActionResult, DeviceView, PoolInfo, Telemetry, TuningInfo } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useToasts } from '@/stores/toasts'
import DetailPools from './DetailPools.vue'
import DetailTuning from './DetailTuning.vue'

const DEVICE_ID = 'issue21-miner'
const REFUSED = 'The miner refused the change.'

const pool = { role: 'primary', url: 'solo.ckpool.org', port: 3333, user: 'bc1qexample.worker', address: 'bc1qexample', worker: 'worker', active: true, tls: false } as PoolInfo
const device = {
  id: DEVICE_ID,
  name: 'Issue 21 miner',
  allow_control: true,
  capabilities: ['set_pool', 'set_fan', 'set_frequency'],
  telemetry: { pools: [pool], fan_pct: null, fan_rpm: null } as Telemetry,
} as DeviceView
const polled = { ...device, name: 'Issue 21 miner (polled)' } as DeviceView
const tuning: TuningInfo = {
  allowed: true,
  tuning_enabled_in_settings: true,
  options: { frequency_mhz: [485, 525], core_voltage_mv: [1150, 1200], default_frequency_mhz: 485, default_core_voltage_mv: 1200, max_power_w: null, max_temp_c: null },
  current: { frequency_mhz: 485, core_voltage_mv: 1200, power_w: null, hashrate_hs: null, efficiency_j_th: null, temp_asic_c: null },
}

const rejected: ActionResult = { ok: false, message: REFUSED }
const accepted: ActionResult = { ok: true, message: 'sent' }

let wrapper: ReturnType<typeof mount> | undefined

beforeEach(() => {
  setActivePinia(createPinia())
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: mock the miner endpoints') }))
  const session = useSession()
  session.me = { name: 'tester', scope: 'admin', via: 'token' }
  session.state = 'ready'
  vi.spyOn(api, 'sources').mockResolvedValue({ sources: [], implicit: [] })
  vi.spyOn(api, 'deviceTuning').mockResolvedValue(tuning)
  vi.spyOn(api, 'pollDevice').mockResolvedValue(polled)
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  pendingConfirm.value = null
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

function toasts() {
  return useToasts().items.map((t) => ({ kind: t.kind, title: t.title, body: t.body }))
}

/** Submit a form and accept the safety confirmation when one is asked for. */
async function submit(form: { trigger(event: 'submit'): Promise<void> }, confirms: boolean) {
  await form.trigger('submit')
  await flushPromises()
  if (confirms) {
    expect(pendingConfirm.value).not.toBeNull()
    pendingConfirm.value?.resolve(true)
    await flushPromises()
  }
}

async function mountPools() {
  wrapper = mount(DetailPools, { props: { device }, global: { stubs: { Term: { template: '<span><slot /></span>' } } } })
  await flushPromises()
  return wrapper
}

async function mountTuning() {
  wrapper = mount(DetailTuning, { props: { device }, global: { stubs: { Term: { template: '<span><slot /></span>' } } } })
  await flushPromises()
  await wrapper.findAll('select')[0]!.setValue('525')
  return wrapper
}

const submitPool = async () => submit((await mountPools()).get('form'), true)
const submitTuning = async () => submit((await mountTuning()).findAll('form')[0]!, true)
const submitFan = async () => submit((await mountTuning()).findAll('form')[1]!, false)

const forms = [
  { name: 'pool', run: submitPool, action: 'set_pool', success: 'Pool changed' },
  { name: 'tuning', run: submitTuning, action: 'set_tuning', success: 'Tuning changed' },
  { name: 'fan', run: submitFan, action: 'set_fan', success: 'Fan updated' },
]

describe('issue 21: miner action results in the pool, tuning and fan forms', () => {
  describe.each(forms)('$name form', ({ run, action, success }) => {
    it('does not announce a change when the miner reports ok:false', async () => {
      const call = vi.spyOn(api, 'action').mockResolvedValue(rejected)
      await run()
      expect(call).toHaveBeenCalledTimes(1)
      expect(call.mock.calls[0]![1]).toBe(action)
      expect(toasts().filter((t) => t.kind === 'success')).toEqual([])
      expect(toasts().some((t) => t.kind === 'error' && t.body === REFUSED)).toBe(true)
      expect(api.pollDevice).not.toHaveBeenCalled()
    })

    it('keeps "accepted" apart from "could not refresh" when the follow-up poll fails', async () => {
      vi.spyOn(api, 'action').mockResolvedValue(accepted)
      vi.mocked(api.pollDevice).mockRejectedValue(new Error('poll unreachable'))
      await run()
      expect(toasts().filter((t) => t.kind === 'success').map((t) => t.title)).toEqual([success])
      expect(toasts().filter((t) => t.kind === 'error')).toEqual([])
      expect(wrapper!.find('[role="alert"]').exists()).toBe(false)
    })

    it('announces the change and shows the read-back device when everything works', async () => {
      vi.spyOn(api, 'action').mockResolvedValue(accepted)
      await run()
      expect(toasts().filter((t) => t.kind === 'success').map((t) => t.title)).toEqual([success])
      expect(toasts().filter((t) => t.kind === 'error')).toEqual([])
      expect(useLive().devicesById[DEVICE_ID]?.name).toBe('Issue 21 miner (polled)')
    })
  })

  it('still reports a thrown request as a failure, never as a change', async () => {
    vi.spyOn(api, 'action').mockRejectedValue(new Error('network down'))
    await submitFan()
    expect(toasts().filter((t) => t.kind === 'success')).toEqual([])
    expect(toasts().some((t) => t.kind === 'error')).toBe(true)
  })
})
