import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import KioskMinerTile from '@/components/miners/KioskMinerTile.vue'
import type { DeviceView } from '@/lib/types'

// The wall display miner card shows its hashrate number in the brand orange (the same accent-text token as the
// halving and difficulty numbers, which is darkened on the light theme to stay readable). The orange fade on the
// card is CSS only, so its look and contrast are checked in web/e2e/issue81-kiosk-fill-screen.spec.ts.

const TH = 1e12

function device(over: Partial<DeviceView> = {}): DeviceView {
  // Only what the tile reads; the rest of DeviceView is not needed here.
  return {
    id: 'm1',
    name: 'Bitaxe 1',
    status: 'online',
    status_since: null,
    status_reason: null,
    hashrate_smooth_hs: 2.5 * TH,
    telemetry: { hashrate_hs: 2.5 * TH, temp_asic_c: 55 },
    ...over,
  } as unknown as DeviceView
}

beforeEach(() => setActivePinia(createPinia()))

describe('issue 81: wall display miner card colours', () => {
  it('shows the hashrate number in orange and keeps its unit muted', () => {
    const wrapper = mount(KioskMinerTile, { props: { device: device() } })
    const value = wrapper.get('.kt-hash-value')
    expect(value.text()).toBe('2.5')
    expect(value.classes()).toContain('text-accent-text')
    const unit = wrapper.get('.kt-hash-unit')
    expect(unit.text()).toBe('TH/s')
    expect(unit.classes()).toContain('text-muted')
    expect(unit.classes()).not.toContain('text-accent-text')
  })

  it('keeps the name, the status word and the temperature neutral or status-coloured, not orange', () => {
    const wrapper = mount(KioskMinerTile, { props: { device: device() } })
    expect(wrapper.get('.kt-name').classes()).not.toContain('text-accent-text')
    expect(wrapper.get('.kt-status').classes()).toContain('text-ok')
    expect(wrapper.get('.kt-temp').classes()).not.toContain('text-accent-text')
  })

  it('shows no orange hashrate for an offline miner', () => {
    const wrapper = mount(KioskMinerTile, { props: { device: device({ status: 'offline' }) } })
    expect(wrapper.find('.kt-hash-value').exists()).toBe(false)
  })
})
