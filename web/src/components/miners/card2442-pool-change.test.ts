import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { pendingConfirm } from '@/composables/useConfirm'
import { api } from '@/lib/api'
import type { DeviceView } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import MinerTile from './MinerTile.vue'
import PoolChangeNotice from './PoolChangeNotice.vue'

// Card #2442: a miner whose pool or payout settings changed shows a badge, the notice lists the full old and new values,
// and Accept only updates HashHurdr's own record (one API call, nothing sent to the miner).

const OLD_ADDR = 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq'
const NEW_ADDR = 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'
const EVENT_ID = 42

function device(over: Partial<DeviceView> = {}): DeviceView {
  // Only what the tile and the notice read; the rest of DeviceView is not needed here.
  return {
    id: 'm1',
    name: 'Garage',
    model: 'Gamma',
    model_override: null,
    tags: [],
    status: 'online',
    status_since: null,
    status_reason: null,
    last_error: null,
    hashrate_smooth_hs: 1e12,
    spark_hashrate_hs: [],
    telemetry: { hashrate_hs: 1e12, temp_asic_c: 55 },
    pool_change: {
      event_id: EVENT_ID,
      since_ts: 1000,
      changes: [
        { slot: 'primary', setting: 'payout_address', old: OLD_ADDR, new: NEW_ADDR },
        { slot: 'primary', setting: 'pool_address', old: 'pool.example.net', new: 'other-pool.example.net' },
        { slot: 'fallback', setting: 'pool_port', old: '3333', new: null },
      ],
    },
    ...over,
  } as unknown as DeviceView
}

function mountTile(d: DeviceView) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/miners/:id', component: { template: '<div />' } }] })
  return mount(MinerTile, { props: { device: d }, global: { plugins: [router] } })
}

function signIn(scope: 'read' | 'control'): void {
  const session = useSession()
  session.state = 'ready'
  session.me = { name: 'tester', scope, via: 'token' }
}

beforeEach(() => {
  setActivePinia(createPinia())
  signIn('control')
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: mock the pool change endpoint') }))
})
afterEach(() => {
  pendingConfirm.value?.resolve(false)
  pendingConfirm.value = null
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('card 2442: pool or payout settings changed', () => {
  it('shows a badge on the miner tile only while a change is unresolved', () => {
    const open = mountTile(device())
    expect(open.find('[data-testid="pool-change-badge"]').exists()).toBe(true)
    const quiet = mountTile(device({ pool_change: null }))
    expect(quiet.find('[data-testid="pool-change-badge"]').exists()).toBe(false)
    const legacy = device() // a server from before this feature sends no pool_change at all
    delete legacy.pool_change
    expect(mountTile(legacy).find('[data-testid="pool-change-badge"]').exists()).toBe(false)
  })

  it('lists every changed setting with its full old and new value', () => {
    const wrapper = mount(PoolChangeNotice, { props: { device: device() } })
    const text = wrapper.text()
    expect(text).toContain(OLD_ADDR)
    expect(text).toContain(NEW_ADDR)
    expect(text).toContain('pool.example.net')
    expect(text).toContain('other-pool.example.net')
    expect(wrapper.findAll('[data-testid="pool-change-row"]')).toHaveLength(3)
  })

  it('renders nothing when there is no unresolved change', () => {
    const wrapper = mount(PoolChangeNotice, { props: { device: device({ pool_change: null }) } })
    expect(wrapper.find('[data-testid="pool-change-notice"]').exists()).toBe(false)
  })

  it('offers no Accept button to a read-only session', () => {
    signIn('read')
    const wrapper = mount(PoolChangeNotice, { props: { device: device() } })
    expect(wrapper.find('[data-testid="pool-change-notice"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="accept-pool-change"]').exists()).toBe(false)
  })

  it('accepts only after the user confirms, with one call to HashHurdr and an updated miner view', async () => {
    const accept = vi.spyOn(api, 'acceptPoolChange').mockResolvedValue({ ok: true, device: device({ pool_change: null }) })
    const wrapper = mount(PoolChangeNotice, { props: { device: device() } })
    await wrapper.get('[data-testid="accept-pool-change"]').trigger('click')
    expect(pendingConfirm.value).not.toBeNull()
    expect(accept).not.toHaveBeenCalled()
    pendingConfirm.value!.resolve(true)
    await flushPromises()
    expect(accept).toHaveBeenCalledTimes(1)
    expect(accept).toHaveBeenCalledWith(EVENT_ID)
    expect(useLive().byId('m1')?.pool_change).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('does nothing when the user cancels the confirmation', async () => {
    const accept = vi.spyOn(api, 'acceptPoolChange').mockResolvedValue({ ok: true, device: device({ pool_change: null }) })
    const wrapper = mount(PoolChangeNotice, { props: { device: device() } })
    await wrapper.get('[data-testid="accept-pool-change"]').trigger('click')
    pendingConfirm.value!.resolve(false)
    await flushPromises()
    expect(accept).not.toHaveBeenCalled()
  })

  it('keeps the notice and reports the failure when Accept fails', async () => {
    vi.spyOn(api, 'acceptPoolChange').mockRejectedValue(new Error('Accept failed'))
    const wrapper = mount(PoolChangeNotice, { props: { device: device() } })
    await wrapper.get('[data-testid="accept-pool-change"]').trigger('click')
    pendingConfirm.value!.resolve(true)
    await flushPromises()
    expect(wrapper.find('[data-testid="pool-change-notice"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="accept-pool-change"]').attributes('disabled')).toBeUndefined()
  })
})
