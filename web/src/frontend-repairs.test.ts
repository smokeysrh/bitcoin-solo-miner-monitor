import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { effectScope, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api, ApiError, cancelPendingRequests, onUnauthorized, request } from '@/lib/api'
import type { Settings, Insight, HistoryResult } from '@/lib/types'
import { useSectionForm } from '@/composables/useSectionForm'
import { useSettings } from '@/stores/settings'
import { useSession } from '@/stores/session'
import { useLive } from '@/stores/live'
import { useInsights } from '@/stores/insights'
import { useUi } from '@/stores/ui'
import { useToasts } from '@/stores/toasts'
import { LiveStream } from '@/lib/stream'
import { pendingConfirm, confirmDialog } from '@/composables/useConfirm'
import App from '@/App.vue'
import HistoryChart from '@/components/charts/HistoryChart.vue'
import InsightsWidget from '@/components/dashboard/widgets/InsightsWidget.vue'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function config(): Settings {
  // Only fields consumed by these components; no backend, credentials or private fixture data.
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null },
  } as Settings
}
const wrappers: { unmount: () => void }[] = []
const scopes: ReturnType<typeof effectScope>[] = []
function section(key: 'general' | 'polling') {
  const scope = effectScope(); scopes.push(scope)
  return scope.run(() => useSectionForm(key))!
}
beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  scopes.splice(0).forEach((s) => s.stop())
  cancelPendingRequests(); onUnauthorized(null)
  vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers()
})

describe('FE-01/FE-02 session lifecycle', () => {
  it('public is ready for monitoring but not an authenticated account; expiry clears permissions', () => {
    const session = useSession()
    session.state = 'ready'; session.me = { name: 'public', scope: 'read', via: 'public' }
    expect(session.authenticated).toBe(false)
    expect(session.readOnly).toBe(true)
    session.me = { name: 'admin', scope: 'admin', via: 'session' }
    expect(session.authenticated).toBe(true); expect(session.canAdmin).toBe(true)
    session.expire()
    expect(session.me).toBeNull(); expect(session.canAdmin).toBe(false); expect(session.state).toBe('login')
  })

  it('stop clears live state and rejects late overview/reload responses', async () => {
    const live = useLive()
    const response = deferred<Awaited<ReturnType<typeof api.overview>>>()
    vi.spyOn(api, 'overview').mockReturnValue(response.promise)
    vi.spyOn(api, 'devices').mockResolvedValue([])
    vi.spyOn(api, 'pool').mockResolvedValue({ pools: [] })
    vi.spyOn(api, 'recentBlocks').mockResolvedValue([])
    const refresh = live.refreshOverview(); const reload = live.reload()
    live.events = [{ id: 'private-event' } as never]; live.loaded = true
    live.stop()
    response.resolve({ summary: { updated_at: 1 }, odds: { hashrate_hs: 123 }, events: [{ id: 'old' }], network: {}, alerts: [], blocks_found: [], leaderboard: [] } as never)
    await Promise.all([refresh, reload])
    expect(live.loaded).toBe(false); expect(live.summary).toBeNull(); expect(live.odds).toBeNull()
    expect(live.events).toEqual([]); expect(live.devices).toEqual([])
  })

  it('late SSE messages and errors from a closed stream cannot revive it', () => {
    vi.useFakeTimers()
    class Source extends EventTarget { readyState = 1; onerror: (() => void) | null = null; close() { this.readyState = 2 } }
    const source = new Source(); const handler = vi.fn()
    const stream = new LiveStream({ device: handler }, { eventSourceFactory: () => source as unknown as EventSource })
    stream.start()
    source.dispatchEvent(new MessageEvent('device', { data: '{"id":"before"}' }))
    expect(handler).toHaveBeenCalledTimes(1)
    stream.stop()
    source.dispatchEvent(new MessageEvent('device', { data: '{"id":"after"}' }))
    source.dispatchEvent(new MessageEvent('hello', { data: '{}' }))
    source.onerror?.()
    expect(handler).toHaveBeenCalledTimes(1); expect(stream.status).toBe('closed')
    expect(vi.getTimerCount()).toBe(0)
  })

  it('cancels requests through body consumption and ignores an old-session 401', async () => {
    const body = deferred<string>(); const unauthorized = vi.fn()
    onUnauthorized(unauthorized)
    let signal: AbortSignal | undefined
    vi.stubGlobal('fetch', vi.fn((_url: string, opts: RequestInit) => {
      signal = opts.signal as AbortSignal
      return Promise.resolve({ status: 401, ok: false, text: () => body.promise })
    }))
    const pending = request('GET', '/settings')
    const rejected = expect(pending).rejects.toMatchObject({ name: 'AbortError' })
    await flushPromises(); cancelPendingRequests()
    expect(signal!.aborted).toBe(true)
    body.resolve('{"error":{"code":"auth_required","message":"old session"}}')
    await rejected
    expect(unauthorized).not.toHaveBeenCalled()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 200 })))
    await expect(request('GET', '/meta')).resolves.toEqual({})
  })

  it('current 401 expires the session through the real API client', async () => {
    const session = useSession(); session.state = 'ready'; session.me = { name: 'admin', scope: 'admin', via: 'session' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"error":{"code":"auth_required","message":"expired"}}', { status: 401 })))
    await expect(api.settings()).rejects.toMatchObject({ status: 401 })
    expect(session.me).toBeNull(); expect(session.state).toBe('login')
  })

  it('failed logout clears local identity, warns honestly and suppresses late page toasts', async () => {
    const session = useSession(); session.state = 'ready'; session.me = { name: 'admin', scope: 'admin', via: 'session' }
    vi.spyOn(api, 'logout').mockRejectedValue(new Error('Offline'))
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    await session.logout()
    expect(session.state).toBe('login'); expect(session.me).toBeNull()
    expect(session.error).toContain('could not be confirmed')
    const toasts = useToasts(); toasts.error('Old private action')
    expect(toasts.items).toEqual([])
    session.state = 'ready'; toasts.success('New session action')
    expect(toasts.items.map((t) => t.title)).toEqual(['New session action'])
  })

  it('App cancels a pending startup, clears caches/dialogs and navigates immediately', async () => {
    const session = useSession(); session.state = 'ready'; session.me = { name: 'admin', scope: 'admin', via: 'session' }
    const settings = useSettings(); const live = useLive(); const insights = useInsights(); const ui = useUi()
    const result = deferred<Settings>(); vi.spyOn(api, 'settings').mockReturnValue(result.promise)
    const start = vi.spyOn(live, 'start').mockImplementation(() => undefined)
    insights.items = [{ id: 'private' } as Insight]; ui.addMinerOpen = true; ui.paletteOpen = true
    const confirm = confirmDialog({ title: 'Private action' })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/miners', component: { template: '<div />' } }, { path: '/login', name: 'login', meta: { bare: true, public: true }, component: { template: '<input aria-label="Login" />' } }] })
    await router.push('/miners')
    wrappers.push(mount(App, { global: { plugins: [router], stubs: { AppShell: true, Celebration: true, Toaster: true, ConfirmHost: true } } }))
    session.expire(); result.resolve(config()); await flushPromises()
    expect(start).not.toHaveBeenCalled(); expect(settings.data).toBeNull(); expect(insights.items).toEqual([])
    expect(ui.addMinerOpen).toBe(false); expect(ui.paletteOpen).toBe(false); expect(pendingConfirm.value).toBeNull()
    await expect(confirm).resolves.toBe(false)
    expect(router.currentRoute.value.path).toBe('/login'); expect(router.currentRoute.value.query.next).toBe('/miners')
  })

  it.each(['resolve', 'reject'] as const)('settings clear prevents late PATCH %s from restoring protected data', async (outcome) => {
    const settings = useSettings(); settings.data = config()
    const pending = deferred<Settings>(); vi.spyOn(api, 'updateSettings').mockReturnValue(pending.promise)
    const save = settings.patch({ general: { instance_name: 'new' } })
    const rejected = expect(save).rejects.toBeInstanceOf(Error)
    settings.clear()
    if (outcome === 'resolve') pending.resolve(config()); else pending.reject(new Error('late failure'))
    await rejected
    expect(settings.data).toBeNull(); expect(settings.saving).toBe(false)
  })
})

describe('FE-04 captured settings drafts', () => {
  it('preserves two dirty forms across responses and sends only actually touched fields', async () => {
    const settings = useSettings(); settings.data = config()
    const general = section('general'); const polling = section('polling')
    general.form.instance_name = 'local'; polling.form.interval_s = 19
    settings.data = { ...config(), general: { ...config().general, onboarding_done: false } }
    await nextTick()
    expect(general.form.instance_name).toBe('local'); expect(polling.form.interval_s).toBe(19)
    expect(general.form.onboarding_done).toBe(false)
    const update = vi.spyOn(api, 'updateSettings').mockResolvedValue({ ...settings.data, general: { ...settings.data.general, instance_name: 'local' } })
    expect(await general.save()).toBe(true)
    expect(update).toHaveBeenCalledWith({ general: { instance_name: 'local' } })
    expect(general.dirty.value).toBe(false); expect(polling.dirty.value).toBe(true)
  })

  it('failed unrelated patch keeps drafts; explicit discard loads the current server baseline', async () => {
    const settings = useSettings(); settings.data = config(); const form = section('general')
    form.form.instance_name = 'local'
    vi.spyOn(api, 'updateSettings').mockRejectedValue(new Error('failure'))
    await expect(settings.patch({ units: { temperature: 'f' } })).rejects.toThrow('failure')
    await nextTick(); expect(form.form.instance_name).toBe('local'); expect(form.dirty.value).toBe(true)
    form.discard(); expect(form.form.instance_name).toBe('Fixture fleet'); expect(form.dirty.value).toBe(false)
  })

  it('keeps edits made while save is pending and detects same-field remote conflicts', async () => {
    const settings = useSettings(); settings.data = config(); const form = section('general')
    const pending = deferred<Settings>(); const update = vi.spyOn(api, 'updateSettings').mockReturnValue(pending.promise)
    form.form.instance_name = 'submitted'; const save = form.save()
    form.form.instance_name = 'typed later'
    pending.resolve({ ...config(), general: { ...config().general, instance_name: 'submitted' } })
    await save; await nextTick(); expect(form.form.instance_name).toBe('typed later'); expect(form.dirty.value).toBe(true)
    settings.data = { ...config(), general: { ...config().general, instance_name: 'remote' } }
    await nextTick(); expect(await form.save()).toBe(false); expect(update).toHaveBeenCalledTimes(1)
    expect(form.error.value).toContain('changed elsewhere')
    form.discard(); expect(form.form.instance_name).toBe('remote')
  })
})

describe('FE-05 observations', () => {
  it('distinguishes unknown, failed, healthy empty, warning and stale retained results', async () => {
    const first = deferred<Insight[]>(); const fetch = vi.spyOn(api, 'insights').mockReturnValue(first.promise)
    const wrapper = mount(InsightsWidget, { global: { mocks: { $router: {} }, stubs: { RouterLink: true } } }); wrappers.push(wrapper)
    expect(wrapper.text()).toContain('Checking observations'); expect(wrapper.text()).not.toContain('healthy')
    first.reject(new Error('unavailable')); await flushPromises()
    expect(wrapper.text()).toContain('Could not load observations'); expect(wrapper.text()).not.toContain('healthy')
    fetch.mockResolvedValue([]); await useInsights().refresh(true); await nextTick()
    expect(wrapper.text()).toContain('healthy')
    fetch.mockResolvedValue([{ id: 'hot', level: 'warning', title: 'Hot miner', body: 'Check cooling', action: null, device_id: null }])
    await useInsights().refresh(true); await nextTick(); expect(wrapper.text()).toContain('Hot miner')
    fetch.mockRejectedValue(new Error('unavailable')); await useInsights().refresh(true); await nextTick()
    expect(wrapper.text()).toContain('Observations are stale'); expect(wrapper.text()).toContain('Last checked:')
    expect(wrapper.text()).toContain('Hot miner'); expect(wrapper.text()).not.toContain('healthy')
  })
  it('clear discards late observations without suppressing the next session refresh', async () => {
    const result = deferred<Insight[]>(); const fetch = vi.spyOn(api, 'insights').mockReturnValueOnce(result.promise).mockResolvedValue([])
    const insights = useInsights(); const previous = insights.refresh(true)
    insights.clear(); await insights.refresh(true)
    result.resolve([{ id: 'old-session' } as Insight]); await previous
    expect(insights.items).toEqual([]); expect(insights.loaded).toBe(true); expect(fetch).toHaveBeenCalledTimes(2)
  })
})

const series = (value: number): HistoryResult => ({ step: 1, source: 'fixture', t: [1, 2], series: { hashrate_hs: [value, value] } })
function chart() {
  const wrapper = mount(HistoryChart, { props: { metrics: ['hashrate_hs'], range: '24h', refreshMs: 1000 }, global: { stubs: { TimeSeriesChart: { props: ['t', 'series'], template: '<div data-testid="chart">{{ series }}</div>' } } } })
  wrappers.push(wrapper); return wrapper
}
describe('FE-07 chart query identity', () => {
  it('shows stale status for periodic refresh failure, clears it on recovery', async () => {
    vi.useFakeTimers(); vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    const fetch = vi.spyOn(api, 'fleetHistory').mockResolvedValue(series(24)); const wrapper = chart()
    await flushPromises(); expect(wrapper.find('[data-testid="chart"]').exists()).toBe(true)
    fetch.mockRejectedValue(new Error('refresh failed')); await vi.advanceTimersByTimeAsync(1000); await flushPromises()
    expect(wrapper.text()).toContain('Chart is stale'); expect(wrapper.find('[data-testid="chart"]').exists()).toBe(true)
    fetch.mockResolvedValue(series(25)); await vi.advanceTimersByTimeAsync(1000); await flushPromises()
    expect(wrapper.text()).not.toContain('stale'); expect(wrapper.text()).toContain('25')
  })
  it('late cancelled range responses cannot overwrite the successful query', async () => {
    const old = deferred<HistoryResult>()
    vi.spyOn(api, 'fleetHistory').mockReturnValueOnce(old.promise).mockResolvedValue(series(1))
    const wrapper = chart(); await wrapper.setProps({ range: '1h' }); await flushPromises()
    expect(wrapper.text()).toContain('1')
    old.resolve(series(99)); await flushPromises(); expect(wrapper.text()).not.toContain('99')
  })
  it('device changes fail explicitly instead of showing old data; unmount aborts owned work', async () => {
    vi.spyOn(api, 'fleetHistory').mockResolvedValue(series(24)); const wrapper = chart(); await flushPromises()
    vi.spyOn(api, 'deviceHistory').mockRejectedValue(new Error('new device unavailable'))
    await wrapper.setProps({ deviceId: 'other' }); await flushPromises()
    expect(wrapper.text()).toContain('Could not load the chart'); expect(wrapper.find('[data-testid="chart"]').exists()).toBe(false)
    const pending = deferred<HistoryResult>(); const fetch = vi.spyOn(api, 'fleetHistory').mockReturnValue(pending.promise)
    await wrapper.setProps({ deviceId: undefined, range: '7d' }); wrapper.unmount()
    expect(fetch.mock.calls.at(-1)![1]!.aborted).toBe(true)
    pending.resolve(series(7)); await flushPromises()
  })
})

describe('FE-10 local appearance boundary', () => {
  it('restores only validated local appearance for read-only, never for admins', async () => {
    localStorage.setItem('bsmm.localAppearance', JSON.stringify({ theme: 'light', accent: '#06B6D4', density: 'compact', reduce_motion: true, dashboard: { widgets: [] }, unknown: 'ignored' }))
    vi.spyOn(api, 'settings').mockResolvedValue(config())
    const session = useSession(); session.state = 'ready'; session.me = { name: 'public', via: 'public', scope: 'read' }
    const settings = useSettings(); await settings.load()
    expect(settings.look).toEqual({ theme: 'light', accent: '#06B6D4', density: 'compact', reduceMotion: true })
    expect(settings.data!.ui.dashboard).toBeNull(); expect(settings.localOnly).toBe(true)
    session.me = { name: 'admin', via: 'session', scope: 'admin' }; await settings.load()
    expect(settings.look.theme).toBe('dark'); expect(settings.localOnly).toBe(false)
  })
  it('401 does not persist an override; failed non-UI writes are not local success', async () => {
    const session = useSession(); session.state = 'ready'; session.me = { name: 'admin', via: 'session', scope: 'admin' }
    const settings = useSettings(); settings.data = config()
    const update = vi.spyOn(api, 'updateSettings').mockRejectedValue(new ApiError(401, 'auth_required', 'Expired'))
    await expect(settings.patch({ ui: { theme: 'light' } })).rejects.toMatchObject({ status: 401 })
    expect(localStorage.getItem('bsmm.localAppearance')).toBeNull(); expect(settings.look.theme).toBe('dark')
    session.me = { name: 'public', via: 'public', scope: 'read' }
    update.mockRejectedValue(new ApiError(403, 'forbidden', 'Read only'))
    await expect(settings.patch({ general: { instance_name: 'new' } })).rejects.toMatchObject({ status: 403 })
    expect(settings.localOnly).toBe(false)
  })
  it('known read-only appearance changes never attempt forbidden requests', async () => {
    const session = useSession(); session.state = 'ready'; session.me = { name: 'public', via: 'public', scope: 'read' }
    const settings = useSettings(); settings.data = config()
    const update = vi.spyOn(api, 'updateSettings').mockRejectedValue(new ApiError(401, 'auth_required', 'Public cannot write'))
    await settings.patch({ ui: { theme: 'light', accent: '#06B6D4', density: 'compact', reduce_motion: true } })
    expect(update).not.toHaveBeenCalled(); expect(session.state).toBe('ready')
    expect(settings.localOnly).toBe(true)
    vi.spyOn(api, 'settings').mockResolvedValue(config()); await settings.load()
    expect(settings.look).toEqual({ theme: 'light', accent: '#06B6D4', density: 'compact', reduceMotion: true })
  })
})
