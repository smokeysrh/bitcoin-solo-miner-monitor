import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api } from '@/lib/api'
import type { DiscoveryJob } from '@/lib/types'
import DiscoveryPanel from './DiscoveryPanel.vue'

const POLL_MS = 1000
function job(status: DiscoveryJob['status'] = 'running', withMiner = false): DiscoveryJob {
  return {
    id: 'fixture-scan', cidrs: ['127.0.0.1/32'], status, phase: 'probing', started_at: 1,
    finished_at: status === 'running' ? null : 2, total_hosts: 1, scanned_hosts: 0, progress: 0,
    miners: withMiner ? [{ key: 'fixture-miner', host: '127.0.0.1', port: 80, driver: 'axeos',
      family: 'bitaxe', model: 'Fixture miner', mac: null, serial: null, firmware: null,
      hostname: null, identity: 'fixture-miner', hashrate_hs: null, evidence: [],
      already_added: null, duplicate_of: null }] : [],
    sources: [], error: null,
  }
}
let wrapper: ReturnType<typeof mount> | undefined
beforeEach(() => {
  setActivePinia(createPinia())
  vi.useFakeTimers()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: mock discovery endpoints') }))
  vi.spyOn(api, 'suggestRanges').mockResolvedValue(['127.0.0.1/32'])
  vi.spyOn(api, 'startDiscovery').mockResolvedValue(job())
  vi.spyOn(api, 'cancelDiscovery').mockResolvedValue({ ok: true })
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers()
})
async function start() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  wrapper = mount(DiscoveryPanel, { global: { plugins: [router] } })
  await flushPromises()
  await wrapper.get('[data-testid="start-scan"]').trigger('click')
  await flushPromises()
  return wrapper
}
async function tick() {
  await vi.advanceTimersByTimeAsync(POLL_MS)
  await flushPromises()
}

describe('discovery status recovery', () => {
  it('shows an unknown status, retains results, retries the same job and resumes polling', async () => {
    vi.mocked(api.startDiscovery).mockResolvedValue(job('running', true))
    const status = vi.spyOn(api, 'discovery').mockRejectedValueOnce(new Error('Status unavailable'))
      .mockRejectedValueOnce(new Error('Still unavailable')).mockResolvedValue(job('running', true))
    const panel = await start()
    await tick()
    expect(panel.get('[role="alert"]').text()).toContain('Status unavailable')
    expect(panel.text()).toContain('Scan status unknown')
    expect(panel.text()).toContain('Fixture miner')
    expect(panel.text()).not.toMatch(/Scanning…|Scan finished|The scan failed|No miners found/)
    expect(vi.getTimerCount()).toBe(0)
    const retry = () => panel.findAll('button').find((b) => b.text() === 'Retry status')!
    await retry().trigger('click'); await flushPromises()
    expect(panel.get('[role="alert"]').text()).toContain('Still unavailable')
    await retry().trigger('click'); await flushPromises()
    expect(panel.find('[role="alert"]').exists()).toBe(false)
    expect(panel.text()).toContain('Scanning…')
    await tick()
    expect(status).toHaveBeenCalledTimes(4)
    expect(status.mock.calls).toEqual(Array.from({ length: 4 }, () => ['fixture-scan']))
    expect(api.startDiscovery).toHaveBeenCalledTimes(1)
    panel.unmount(); wrapper = undefined
    expect(api.cancelDiscovery).toHaveBeenCalledWith('fixture-scan')
    await tick()
    expect(status).toHaveBeenCalledTimes(4)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('shows successful empty completion only after a recovered status read', async () => {
    const status = vi.spyOn(api, 'discovery').mockRejectedValueOnce(new Error('Offline')).mockResolvedValue(job('finished'))
    const panel = await start(); await tick()
    expect(panel.text()).not.toContain('No miners found')
    await panel.findAll('button').find((b) => b.text() === 'Retry status')!.trigger('click')
    await flushPromises()
    expect(panel.text()).toContain('Scan finished: 0 miners found')
    expect(panel.text()).toContain('No miners found')
    expect(panel.find('[role="alert"]').exists()).toBe(false)
    await tick()
    expect(status).toHaveBeenCalledTimes(2)
    expect(api.startDiscovery).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it.each(['failed', 'cancelled'] as const)('does not describe an empty %s job as successful empty discovery', async (state) => {
    vi.spyOn(api, 'discovery').mockResolvedValue(job(state))
    const panel = await start(); await tick()
    expect(panel.text()).toContain(state === 'failed' ? 'The scan failed' : 'Scan stopped')
    expect(panel.text()).not.toContain('No miners found')
    expect(vi.getTimerCount()).toBe(0)
  })

  it('ignores a late running retry after unmount instead of restarting its timer', async () => {
    let resolve!: (value: DiscoveryJob) => void
    const pending = new Promise<DiscoveryJob>((done) => { resolve = done })
    const status = vi.spyOn(api, 'discovery').mockRejectedValueOnce(new Error('Offline')).mockReturnValue(pending)
    const panel = await start(); await tick()
    await panel.findAll('button').find((b) => b.text() === 'Retry status')!.trigger('click')
    await flushPromises()
    panel.unmount(); wrapper = undefined
    resolve(job()); await flushPromises(); await tick()
    expect(status).toHaveBeenCalledTimes(2)
    expect(api.cancelDiscovery).toHaveBeenCalledWith('fixture-scan')
    expect(vi.getTimerCount()).toBe(0)
  })
})
