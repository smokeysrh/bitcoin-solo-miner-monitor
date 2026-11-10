import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api, ApiError, cancelPendingRequests, onUnauthorized } from '@/lib/api'
import { pendingConfirm } from '@/composables/useConfirm'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import AlertsPage from '@/pages/AlertsPage.vue'
import AboutSettings from '@/pages/settings/AboutSettings.vue'
import NotificationsSettings from '@/pages/settings/NotificationsSettings.vue'
import SecuritySettings from '@/pages/settings/SecuritySettings.vue'
import SourcesSettings from '@/pages/settings/SourcesSettings.vue'

// Issue #26: a failed load must never look like "nothing here" / "All clear".
// Only the HTTP-facing api methods are mocked; the real pages, stores and ErrorState render.

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((yes) => { resolve = yes })
  return { promise, resolve }
}

const failure = (message: string) => new ApiError(500, 'server_error', message)
const tabsStub = { props: ['tabs', 'label', 'modelValue'], template: '<div><slot name="activity" /></div>' }
const stubs = { Select: true, Switch: true, ToggleRow: true, Dialog: true, RuleDialog: true, CopyButton: true, Tabs: tabsStub }

const wrappers: { unmount: () => void }[] = []
// every .vue import shares the shim's component type, so any page fits this parameter
async function mountPage(page: typeof AlertsPage) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(page, { global: { plugins: [router], stubs } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
async function tryAgain(wrapper: Awaited<ReturnType<typeof mountPage>>): Promise<void> {
  const button = wrapper.findAll('button').find((b) => b.text().includes('Try again'))
  expect(button, 'a Try again button is offered').toBeDefined()
  await button!.trigger('click')
  await flushPromises()
}
function signIn(scope: 'read' | 'admin', via: 'none' | 'public'): void {
  const session = useSession()
  session.state = 'ready'
  session.me = { name: scope === 'admin' ? 'local' : 'public', scope, via }
}

beforeEach(() => {
  setActivePinia(createPinia())
  signIn('admin', 'none')
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  pendingConfirm.value = null
  cancelPendingRequests(); onUnauthorized(null)
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

const source = { id: 's1', kind: 'bitcoin_core', name: 'Home node', url: 'http://node.local:8332', enabled: true, options: {}, health: null }
const channel = { id: 'c1', kind: 'ntfy', name: 'Phone', enabled: true, config: {}, min_severity: 'info' }
const token = { id: 't1', name: 'agent-one', scope: 'read', created_at: 1, last_used_at: null, expires_at: null }

describe('issue 26: node & pool sources', () => {
  it('a failed list is an error with retry, not "Nothing connected yet"; retry recovers', async () => {
    vi.spyOn(api, 'sourceKinds').mockResolvedValue([])
    const sources = vi.spyOn(api, 'sources').mockRejectedValue(failure('sources unavailable'))
    const wrapper = await mountPage(SourcesSettings)
    expect(wrapper.text()).toContain('sources unavailable')
    expect(wrapper.text()).not.toContain('Nothing connected yet')
    expect(wrapper.find('[data-testid="source-list"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="add-source"]').attributes('disabled')).toBeDefined()
    sources.mockResolvedValue({ sources: [source], implicit: [] } as never)
    await tryAgain(wrapper)
    expect(wrapper.find('[data-testid="source-list"]').text()).toContain('Home node')
    expect(wrapper.text()).not.toContain('sources unavailable')
  })

  it('a genuinely empty list still says nothing is connected', async () => {
    vi.spyOn(api, 'sourceKinds').mockResolvedValue([])
    vi.spyOn(api, 'sources').mockResolvedValue({ sources: [], implicit: [] })
    const wrapper = await mountPage(SourcesSettings)
    expect(wrapper.text()).toContain('Nothing connected yet')
  })

  it('a failed metadata request does not hide the inventory, and a failed refresh keeps the last list', async () => {
    vi.spyOn(api, 'sourceKinds').mockRejectedValue(failure('kinds unavailable'))
    const sources = vi.spyOn(api, 'sources').mockResolvedValue({ sources: [source], implicit: [] } as never)
    const wrapper = await mountPage(SourcesSettings)
    expect(wrapper.find('[data-testid="source-list"]').text()).toContain('Home node')
    sources.mockRejectedValue(failure('sources unavailable'))
    await tryAgain(wrapper)
    expect(wrapper.find('[data-testid="source-list"]').text()).toContain('Home node')
    expect(wrapper.text()).not.toContain('Nothing connected yet')
  })
})

describe('issue 26: notification channels', () => {
  it('a failed list is an error with retry, not "No channels yet"; retry recovers', async () => {
    vi.spyOn(api, 'channelTypes').mockResolvedValue([])
    const channels = vi.spyOn(api, 'channels').mockRejectedValue(failure('channels unavailable'))
    const wrapper = await mountPage(NotificationsSettings)
    expect(wrapper.text()).toContain('channels unavailable')
    expect(wrapper.text()).not.toContain('No channels yet')
    expect(wrapper.find('[data-testid="channel-list"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="add-channel"]').attributes('disabled')).toBeDefined()
    channels.mockResolvedValue([channel] as never)
    await tryAgain(wrapper)
    expect(wrapper.find('[data-testid="channel-list"]').text()).toContain('Phone')
    expect(wrapper.text()).not.toContain('channels unavailable')
  })

  it('a genuinely empty list still says there are no channels', async () => {
    vi.spyOn(api, 'channelTypes').mockResolvedValue([])
    vi.spyOn(api, 'channels').mockResolvedValue([])
    const wrapper = await mountPage(NotificationsSettings)
    expect(wrapper.text()).toContain('No channels yet')
  })

  it('a failed metadata request does not hide the inventory, and a failed refresh keeps the last list', async () => {
    vi.spyOn(api, 'channelTypes').mockRejectedValue(failure('types unavailable'))
    const channels = vi.spyOn(api, 'channels').mockResolvedValue([channel] as never)
    const wrapper = await mountPage(NotificationsSettings)
    expect(wrapper.find('[data-testid="channel-list"]').text()).toContain('Phone')
    channels.mockRejectedValue(failure('channels unavailable'))
    await tryAgain(wrapper)
    expect(wrapper.find('[data-testid="channel-list"]').text()).toContain('Phone')
    expect(wrapper.text()).not.toContain('No channels yet')
  })
})

describe('issue 26: API tokens', () => {
  it.each([403, 500])('a failed %i token list is an error with retry, not "No tokens yet"', async (status) => {
    const tokens = vi.spyOn(api, 'tokens').mockRejectedValue(new ApiError(status, 'failed', 'tokens unavailable'))
    const wrapper = await mountPage(SecuritySettings)
    expect(wrapper.text()).toContain('tokens unavailable')
    expect(wrapper.text()).not.toContain('No tokens yet')
    tokens.mockResolvedValue([token] as never)
    await tryAgain(wrapper)
    expect(wrapper.find('[data-testid="token-list"]').text()).toContain('agent-one')
  })

  it('a genuinely empty inventory still says there are no tokens', async () => {
    vi.spyOn(api, 'tokens').mockResolvedValue([])
    const wrapper = await mountPage(SecuritySettings)
    expect(wrapper.text()).toContain('No tokens yet')
  })

  it('a failed refresh after a revoke keeps the last list, drops the revoked token and says the list may be out of date', async () => {
    const other = { ...token, id: 't2', name: 'agent-two' }
    const tokens = vi.spyOn(api, 'tokens').mockResolvedValue([token, other] as never)
    vi.spyOn(api, 'deleteToken').mockResolvedValue({ ok: true })
    const wrapper = await mountPage(SecuritySettings)
    tokens.mockRejectedValue(failure('tokens unavailable'))
    await wrapper.find('[aria-label="Revoke agent-one"]').trigger('click')
    await flushPromises()
    pendingConfirm.value!.resolve(true)
    await flushPromises()
    const list = wrapper.find('[data-testid="token-list"]')
    expect(list.text()).toContain('agent-two')
    expect(list.text()).not.toContain('agent-one')
    expect(wrapper.text()).toContain('out of date')
    expect(wrapper.text()).not.toContain('No tokens yet')
  })

  it('does not request the admin-only inventory for a known non-admin', async () => {
    signIn('read', 'public')
    const tokens = vi.spyOn(api, 'tokens').mockRejectedValue(new ApiError(403, 'forbidden', 'Admin only'))
    const wrapper = await mountPage(SecuritySettings)
    expect(tokens).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('No tokens yet')
  })
})

describe('issue 26: about and health', () => {
  const info = { version: '9.9.9', uptime_s: 90, platform: 'TestOS', python: '3.11', devices: 3, stream_subscribers: 1, demo: false, offline_mode: false }
  const update = { update_available: false, disabled: false, error: null, latest: null, url: null }
  const diagnostics = { ok: true, checks: [{ id: 'one', status: 'pass', message: 'All checks fine', fix: null }], lan_networks: [], listening: '' }

  it('a failed health check is an error with retry, not an endless skeleton', async () => {
    vi.spyOn(api, 'systemInfo').mockResolvedValue(info as never)
    vi.spyOn(api, 'updateStatus').mockResolvedValue(update as never)
    const run = vi.spyOn(api, 'diagnostics').mockRejectedValue(failure('checks unavailable'))
    const wrapper = await mountPage(AboutSettings)
    expect(wrapper.findAll('.skeleton')).toHaveLength(0)
    expect(wrapper.text()).toContain('checks unavailable')
    run.mockResolvedValue(diagnostics as never)
    await tryAgain(wrapper)
    expect(wrapper.find('[data-testid="checks"]').text()).toContain('All checks fine')
    expect(wrapper.text()).not.toContain('checks unavailable')
  })

  it('failed system details are reported, not left as blanks; retry recovers', async () => {
    const systemInfo = vi.spyOn(api, 'systemInfo').mockRejectedValue(failure('details unavailable'))
    vi.spyOn(api, 'updateStatus').mockResolvedValue(update as never)
    vi.spyOn(api, 'diagnostics').mockResolvedValue(diagnostics as never)
    const wrapper = await mountPage(AboutSettings)
    expect(wrapper.text()).toContain('details unavailable')
    expect(wrapper.text()).not.toContain('Miners watched')
    systemInfo.mockResolvedValue(info as never)
    await tryAgain(wrapper)
    expect(wrapper.text()).toContain('Miners watched')
    expect(wrapper.text()).not.toContain('details unavailable')
  })
})

describe('issue 26: alerts page health claim', () => {
  const overview = { summary: { updated_at: 1 }, odds: null, network: {}, alerts: [], events: [], blocks_found: [], leaderboard: [] }
  function mockPageData(): void {
    vi.spyOn(api, 'devices').mockResolvedValue([])
    vi.spyOn(api, 'pool').mockResolvedValue({ pools: [] })
    vi.spyOn(api, 'recentBlocks').mockResolvedValue([])
    vi.spyOn(api, 'events').mockResolvedValue({ events: [], next_before_id: null })
    vi.spyOn(api, 'rules').mockResolvedValue([])
    vi.spyOn(api, 'ruleTypes').mockResolvedValue([])
    vi.spyOn(api, 'channels').mockResolvedValue([])
  }

  it('does not say "All clear" while the first overview is still loading', async () => {
    mockPageData()
    const pending = deferred<never>()
    vi.spyOn(api, 'overview').mockReturnValue(pending.promise)
    void useLive().reload()
    const wrapper = await mountPage(AlertsPage)
    expect(wrapper.text()).not.toContain('All clear')
    pending.resolve(overview as never)
    await flushPromises()
    expect(wrapper.text()).toContain('All clear')
  })

  it('does not say "All clear" after a failed overview; retry recovers', async () => {
    mockPageData()
    const fetch = vi.spyOn(api, 'overview').mockRejectedValue(failure('overview unavailable'))
    await useLive().reload()
    const wrapper = await mountPage(AlertsPage)
    expect(wrapper.text()).not.toContain('All clear')
    expect(wrapper.text()).toContain('overview unavailable')
    fetch.mockResolvedValue(overview as never)
    await tryAgain(wrapper)
    expect(wrapper.text()).toContain('All clear')
  })

  it('says "All clear" for a successfully loaded empty overview', async () => {
    mockPageData()
    vi.spyOn(api, 'overview').mockResolvedValue(overview as never)
    await useLive().reload()
    const wrapper = await mountPage(AlertsPage)
    expect(wrapper.text()).toContain('All clear')
  })
})
