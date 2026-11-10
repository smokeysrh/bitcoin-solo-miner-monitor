import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api, cancelPendingRequests, onUnauthorized } from '@/lib/api'
import { downloadText } from '@/lib/csv'
import type { AppEvent, HistoryResult, Odds } from '@/lib/types'
import { useLive } from '@/stores/live'
import AlertsPage from '@/pages/AlertsPage.vue'
import AnalyticsPage from '@/pages/AnalyticsPage.vue'
import OddsPage from '@/pages/OddsPage.vue'

// The export must never be exercised for real: the test only observes what would be written.
vi.mock('@/lib/csv', async (importOriginal) => ({ ...(await importOriginal<typeof import('@/lib/csv')>()), downloadText: vi.fn() }))

interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (error: Error) => void
}
function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const abortError = (message: string): Error => Object.assign(new Error(message), { name: 'AbortError' })

const wrappers: { unmount: () => void }[] = []
async function plugins() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:rest(.*)*', component: { template: '<div />' } }] })
  await router.push('/')
  await router.isReady()
  return [router]
}
beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.mocked(downloadText).mockClear()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  cancelPendingRequests(); onUnauthorized(null)
  vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers()
})

// ---- Analytics
const history = (value: number): HistoryResult => ({ step: 1, source: 'fixture', t: [1, 2], series: { hashrate_hs: [value, value] } })
const chartStub = { props: ['t', 'series'], template: '<div data-testid="chart">{{ series[0].data.join(\',\') }}</div>' }
interface AnalyticsVm { range: string }
async function analytics() {
  const wrapper = mount(AnalyticsPage, { global: { plugins: await plugins(), stubs: { TimeSeriesChart: chartStub } } })
  wrappers.push(wrapper)
  return { wrapper, vm: wrapper.vm as unknown as AnalyticsVm }
}

describe('issue 25: Analytics binds results to the query that produced them', () => {
  it('a failed range change never keeps, labels or exports the previous range', async () => {
    const fetch = vi.spyOn(api, 'fleetHistory').mockResolvedValueOnce(history(111)).mockRejectedValue(new Error('7d unavailable'))
    const { wrapper, vm } = await analytics(); await flushPromises()
    expect(wrapper.find('[data-testid="chart"]').text()).toBe('111,111')
    vm.range = '7d'; await nextTick(); await flushPromises()
    expect(fetch.mock.calls.at(-1)![0].range).toBe('7d')
    expect(wrapper.text()).toContain('Could not load history')
    expect(wrapper.find('[data-testid="chart"]').exists()).toBe(false)
    const exportButton = wrapper.findAll('button').find((b) => b.text().includes('Export CSV'))!
    await exportButton.trigger('click')
    expect(downloadText).not.toHaveBeenCalled()
  })

  it('a failed refresh of the same query stays visible and keeps the last good chart', async () => {
    vi.useFakeTimers(); vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    const fetch = vi.spyOn(api, 'fleetHistory').mockResolvedValue(history(24))
    const { wrapper } = await analytics(); await flushPromises()
    expect(wrapper.text()).not.toContain('stale')
    fetch.mockRejectedValue(new Error('refresh failed'))
    await vi.advanceTimersByTimeAsync(30_000); await flushPromises()
    expect(wrapper.text()).toContain('Chart is stale')
    expect(wrapper.find('[data-testid="chart"]').text()).toBe('24,24')
    fetch.mockResolvedValue(history(25))
    await vi.advanceTimersByTimeAsync(30_000); await flushPromises()
    expect(wrapper.text()).not.toContain('stale')
    expect(wrapper.find('[data-testid="chart"]').text()).toBe('25,25')
  })

  it('a superseded request that fails as aborted cannot publish an error or end the newer loading state', async () => {
    const first = deferred<HistoryResult>(); const second = deferred<HistoryResult>()
    vi.spyOn(api, 'fleetHistory').mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const { wrapper, vm } = await analytics(); await flushPromises()
    vm.range = '7d'; await nextTick()
    first.reject(abortError('first request aborted')); await flushPromises()
    expect(wrapper.text()).not.toContain('Could not load history')
    expect(wrapper.find('.skeleton').exists()).toBe(true)
    second.resolve(history(7)); await flushPromises()
    expect(wrapper.find('[data-testid="chart"]').text()).toBe('7,7')
  })

  it('a late success from a superseded request cannot replace the newer query', async () => {
    const first = deferred<HistoryResult>(); const second = deferred<HistoryResult>()
    vi.spyOn(api, 'fleetHistory').mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const { wrapper, vm } = await analytics(); await flushPromises()
    vm.range = '7d'; await nextTick()
    first.resolve(history(99)); await flushPromises()
    expect(wrapper.text()).not.toContain('99')
    second.resolve(history(7)); await flushPromises()
    expect(wrapper.find('[data-testid="chart"]').text()).toBe('7,7')
  })
})

// ---- Odds what-if
interface OddsVm { whatIf: { ths: number | null } }
async function odds() {
  vi.useFakeTimers()
  const wrapper = mount(OddsPage, { global: { plugins: await plugins() } })
  wrappers.push(wrapper)
  return { wrapper, vm: wrapper.vm as unknown as OddsVm }
}
async function typeThs(vm: OddsVm, value: number): Promise<void> {
  vm.whatIf.ths = value; await nextTick(); await vi.advanceTimersByTimeAsync(250)
}

describe('issue 25: what-if requests keep their own identity', () => {
  it('an in-flight request that fails after "Back to my real numbers" shows no error', async () => {
    const first = deferred<Odds>()
    const fetch = vi.spyOn(api, 'odds').mockReturnValue(first.promise)
    const { wrapper, vm } = await odds()
    await typeThs(vm, 5)
    expect(fetch).toHaveBeenCalledTimes(1)
    const back = wrapper.findAll('button').find((b) => b.text().includes('Back to my real numbers'))!
    await back.trigger('click')
    expect(fetch.mock.calls[0]![1]!.aborted).toBe(true)
    first.reject(new Error('old what-if failed')); await flushPromises()
    expect(wrapper.text()).not.toContain('old what-if failed')
  })

  it('a replaced request that fails as aborted cannot publish an error while the newer one runs', async () => {
    const first = deferred<Odds>(); const second = deferred<Odds>()
    vi.spyOn(api, 'odds').mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const { wrapper, vm } = await odds()
    await typeThs(vm, 5); await typeThs(vm, 6)
    first.reject(abortError('first what-if aborted')); await flushPromises()
    expect(wrapper.text()).not.toContain('first what-if aborted')
    second.resolve({ available: false, reason: 'later answer' } as Odds); await flushPromises()
    expect(wrapper.text()).toContain('later answer')
  })
})

// ---- Activity log
const event = (id: number, device: string | null): AppEvent => ({ id, ts: 1000 + id, type: 'restart', severity: 'warning', device_id: device, title: `evt-${id}`, body: null, data: {}, dedupe_key: null, ack_ts: 1 })
interface EventsPage { events: AppEvent[]; next_before_id: number | null }
interface EventsCall { query: Parameters<typeof api.events>[0]; answer: Deferred<EventsPage> }
interface AlertsVm { deviceFilter: string }
async function alerts() {
  const calls: EventsCall[] = []
  vi.spyOn(api, 'events').mockImplementation((query) => {
    const answer = deferred<EventsPage>()
    calls.push({ query, answer })
    return answer.promise
  })
  vi.spyOn(api, 'rules').mockResolvedValue([])
  vi.spyOn(api, 'ruleTypes').mockResolvedValue([])
  vi.spyOn(api, 'channels').mockResolvedValue([])
  const wrapper = mount(AlertsPage, { global: { plugins: await plugins(), stubs: { RuleDialog: true } } })
  wrappers.push(wrapper)
  const answer = async (call: number, events: AppEvent[], next: number | null): Promise<void> => {
    calls[call]!.answer.resolve({ events, next_before_id: next }); await flushPromises()
  }
  const titles = (): string[] => wrapper.text().match(/evt-\d+/g) ?? []
  const filterBy = async (device: string): Promise<void> => { (wrapper.vm as unknown as AlertsVm).deviceFilter = device; await nextTick() }
  const loadOlder = async (): Promise<void> => { await wrapper.findAll('button').find((b) => b.text().includes('Load older'))!.trigger('click') }
  return { wrapper, calls, answer, titles, filterBy, loadOlder }
}

describe('issue 25: Activity log ignores responses from superseded requests', () => {
  it('reversed filter responses leave the list matching the selected miner', async () => {
    const { calls, answer, titles, filterBy } = await alerts()
    await answer(0, [], null)
    await filterBy('a'); await filterBy('b')
    expect(calls.map((c) => c.query?.device_id)).toEqual([undefined, 'a', 'b'])
    await answer(2, [event(20, 'b')], null)
    await answer(1, [event(11, 'a')], null)
    expect(titles()).toEqual(['evt-20'])
  })

  it('a late "Load older" page cannot be appended after the filter changed', async () => {
    const { calls, answer, titles, filterBy, loadOlder } = await alerts()
    await answer(0, [event(10, 'a')], 10)
    await loadOlder()
    expect(calls[1]!.query?.before_id).toBe(10)
    await filterBy('b')
    await answer(2, [event(30, 'b')], null)
    await answer(1, [event(4, 'a')], null)
    expect(titles()).toEqual(['evt-30'])
  })

  it('refreshing the head keeps already loaded older pages and their cursor', async () => {
    const { calls, answer, titles, loadOlder } = await alerts()
    await answer(0, [event(10, 'a'), event(9, 'a')], 9)
    await loadOlder()
    await answer(1, [event(8, 'a'), event(7, 'a')], 7)
    expect(titles()).toEqual(['evt-10', 'evt-9', 'evt-8', 'evt-7'])
    useLive().events = [event(11, 'a')]; await nextTick()
    expect(calls).toHaveLength(3)
    await answer(2, [event(11, 'a'), event(10, 'a')], 10)
    expect(titles()).toEqual(['evt-11', 'evt-10', 'evt-9', 'evt-8', 'evt-7'])
    await loadOlder()
    expect(calls[3]!.query?.before_id).toBe(7)
  })
})
