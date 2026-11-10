import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { pendingConfirm } from '@/composables/useConfirm'
import { api } from '@/lib/api'
import type { ActionResult, DeviceView, PoolInfo, Telemetry, TuningInfo } from '@/lib/types'
import { useSession } from '@/stores/session'
import DetailPools from './DetailPools.vue'
import DetailTuning from './DetailTuning.vue'

// Review round for issue 21: (1) the tuning form must reload only after the read-back poll settles,
// because the tuning endpoint reports the last polled values; (2) a thrown pool request keeps the server's message inline.

const DEVICE_ID = 'issue21-review-miner'
const OLD_FREQUENCY = 485
const NEW_FREQUENCY = 525
const SERVER_MESSAGE = 'network down'

const pool = { role: 'primary', url: 'solo.ckpool.org', port: 3333, user: 'bc1qexample.worker', address: 'bc1qexample', worker: 'worker', active: true, tls: false } as PoolInfo
const device = {
  id: DEVICE_ID,
  name: 'Issue 21 review miner',
  allow_control: true,
  capabilities: ['set_pool', 'set_frequency'],
  telemetry: { pools: [pool], fan_pct: null, fan_rpm: null } as Telemetry,
} as DeviceView

function tuningAt(frequency: number): TuningInfo {
  return {
    allowed: true,
    tuning_enabled_in_settings: true,
    options: { frequency_mhz: [OLD_FREQUENCY, NEW_FREQUENCY], core_voltage_mv: [1150, 1200], default_frequency_mhz: OLD_FREQUENCY, default_core_voltage_mv: 1200, max_power_w: null, max_temp_c: null },
    current: { frequency_mhz: frequency, core_voltage_mv: 1200, power_w: null, hashrate_hs: null, efficiency_j_th: null, temp_asic_c: null },
  }
}

const accepted: ActionResult = { ok: true, message: 'sent' }

let wrapper: ReturnType<typeof mount> | undefined

beforeEach(() => {
  setActivePinia(createPinia())
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: mock the miner endpoints') }))
  const session = useSession()
  session.me = { name: 'tester', scope: 'admin', via: 'token' }
  session.state = 'ready'
  vi.spyOn(api, 'sources').mockResolvedValue({ sources: [], implicit: [] })
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  pendingConfirm.value = null
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

async function confirmAndFlush(form: { trigger(event: 'submit'): Promise<void> }): Promise<void> {
  await form.trigger('submit')
  await flushPromises()
  expect(pendingConfirm.value).not.toBeNull()
  pendingConfirm.value?.resolve(true)
  await flushPromises()
}

describe('issue 21 review round: tuning reload ordering', () => {
  /**
   * Behaves like the real backend: the tuning endpoint only knows the new frequency once the read-back poll has finished.
   * The poll is held open until the test releases it.
   */
  function stubSlowReadBack(pollOutcome: 'resolve' | 'reject') {
    let polled = false
    let release: () => void = () => undefined
    const gate = new Promise<void>((resolve) => { release = resolve })
    const tuningCalls = vi.spyOn(api, 'deviceTuning').mockImplementation(async () => tuningAt(polled ? NEW_FREQUENCY : OLD_FREQUENCY))
    vi.spyOn(api, 'pollDevice').mockImplementation(async () => {
      await gate
      polled = true
      if (pollOutcome === 'reject') throw new Error('poll unreachable')
      return { ...device, name: 'polled' } as DeviceView
    })
    vi.spyOn(api, 'action').mockResolvedValue(accepted)
    return { tuningCalls, release }
  }

  async function applyNewFrequency() {
    wrapper = mount(DetailTuning, { props: { device }, global: { stubs: { Term: { template: '<span><slot /></span>' } } } })
    await flushPromises()
    await wrapper.findAll('select')[0]!.setValue(String(NEW_FREQUENCY))
    await confirmAndFlush(wrapper.findAll('form')[0]!)
    return wrapper
  }

  it('shows the new values once the read-back poll has settled', async () => {
    const { tuningCalls, release } = stubSlowReadBack('resolve')
    const view = await applyNewFrequency()
    // Only the mount-time load so far: reloading while the poll is still running would read the old values.
    expect(tuningCalls).toHaveBeenCalledTimes(1)
    release()
    await flushPromises()
    expect(tuningCalls).toHaveBeenCalledTimes(2)
    expect((view.findAll('select')[0]!.element as HTMLSelectElement).value).toBe(String(NEW_FREQUENCY))
  })

  it('still reloads the form when the read-back poll fails, without calling the change failed', async () => {
    const { tuningCalls, release } = stubSlowReadBack('reject')
    const view = await applyNewFrequency()
    release()
    await flushPromises()
    expect(tuningCalls).toHaveBeenCalledTimes(2)
    expect((view.findAll('select')[0]!.element as HTMLSelectElement).value).toBe(String(NEW_FREQUENCY))
    expect(view.find('[role="alert"]').exists()).toBe(false)
  })
})

describe('issue 21 review round: pool form error text', () => {
  it('keeps the server message inline when the request itself fails', async () => {
    vi.spyOn(api, 'action').mockRejectedValue(new Error(SERVER_MESSAGE))
    vi.spyOn(api, 'pollDevice').mockResolvedValue(device)
    wrapper = mount(DetailPools, { props: { device }, global: { stubs: { Term: { template: '<span><slot /></span>' } } } })
    await flushPromises()
    await confirmAndFlush(wrapper.get('form'))
    expect(wrapper.get('[role="alert"]').text()).toBe(SERVER_MESSAGE)
  })
})
