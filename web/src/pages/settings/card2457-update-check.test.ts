import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { cancelPendingRequests, onUnauthorized } from '@/lib/api'
import { updateCheckText } from '@/lib/updateCheckText'
import type { Me, Settings, UpdateStatus } from '@/lib/types'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import AboutSettings from './AboutSettings.vue'

// Card #2457: Settings > About has a switch for the daily update check, with a note on what a check sends. The switch
// only changes the automatic check: the "Check for updates" button keeps working. The real page and stores run; only the
// network (fetch) is replaced, so the requests the page makes are what is asserted.

const ADMIN: Me = { name: 'owner', scope: 'admin', via: 'token' }
const READ_TOKEN: Me = { name: 'viewer', scope: 'read', via: 'token' }
const CONTROL_TOKEN: Me = { name: 'operator', scope: 'control', via: 'token' }
const INFO = { version: '9.9.9', uptime_s: 90, platform: 'TestOS', python: '3.11', devices: 3, stream_subscribers: 1, demo: false, offline_mode: false }
const DIAGNOSTICS = { ok: true, checks: [], lan_networks: [], listening: '' }
const NEVER_CHECKED: UpdateStatus = { current: '9.9.9', latest: null, update_available: false, url: null, checked_at: null, error: null }
const CHECKED_NOW: UpdateStatus = { current: '9.9.9', latest: null, update_available: false, url: null, checked_at: 1_700_000_000, error: null }
const NEWER: UpdateStatus = { current: '9.9.9', latest: '99.0.0', update_available: true, url: 'https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/v99.0.0', checked_at: 1_700_000_000, error: null }

interface Sent { method: string; path: string; body: unknown }
let sent: Sent[] = []
let wrapper: ReturnType<typeof mount> | undefined
let statusReply: UpdateStatus
let buttonReply: UpdateStatus

/** A plain stand-in for the real switch (a reka-ui widget): a button that reports its state and emits the change. */
const SwitchStub = {
  props: ['modelValue', 'disabled', 'id'],
  emits: ['update:modelValue'],
  template: '<button :id="id" type="button" role="switch" :aria-checked="String(modelValue)" :disabled="disabled" @click="$emit(\'update:modelValue\', !modelValue)" />',
}

/**
 * A complete settings document, as a real server always sends it: the settings store's computed values (`look`, units)
 * read `ui` and `units` on every update. `undefined` leaves out `network.check_for_updates`, as an older server does.
 */
function settingsWith(checkForUpdates: boolean | undefined): Settings {
  const network: Record<string, unknown> = {
    use_public_apis: true, mempool_url: 'https://mempool.space', price_source: 'mempool',
    manual_btc_price: null, difficulty_growth_per_year: 0.4, avg_block_fees_btc: null,
  }
  if (checkForUpdates !== undefined) network.check_for_updates = checkForUpdates
  const settings: Omit<Settings, 'network'> = {
    general: { instance_name: 'HashHurdr', onboarding_done: true, first_run_at: null },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD', locale: null },
    polling: { interval_s: 10, offline_interval_s: 60, timeout_s: 5, concurrency: 8, offline_after_failures: 3 },
    energy: { price_per_kwh: 0.1, psu_overhead_pct: 0 },
    mining: { addresses: [] },
    retention: { raw_days: 7, minute_days: 30, hour_days: 365, event_days: 90 },
    alerts: { temp_warn_c: 75, temp_crit_c: 85, vr_temp_warn_c: 85, hashrate_drop_pct: 30, reject_rate_pct: 5, offline_after_s: 120, quiet_hours: null },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', view_miners: 'grid', reduce_motion: false, sound_on_block: false, simple_mode: false, dashboard: null, kiosk: null },
    auth: { mode: 'password', public_read: false },
  }
  return { ...settings, network } as unknown as Settings // network is cast: the missing-setting case omits a required field
}

function respond(method: string, path: string, body: unknown): unknown {
  if (method === 'GET' && path === '/system/info') return INFO
  if (method === 'GET' && path === '/system/update') return statusReply
  if (method === 'GET' && path === '/system/diagnostics') return DIAGNOSTICS
  if (method === 'POST' && path === '/system/update/check') return buttonReply
  if (method === 'PATCH' && path === '/settings') return settingsWith((body as { network: { check_for_updates: boolean } }).network.check_for_updates)
  throw new Error(`Unexpected transport: ${method} ${path}`)
}

beforeEach(() => {
  setActivePinia(createPinia())
  sent = []
  statusReply = NEVER_CHECKED
  buttonReply = CHECKED_NOW
  vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const path = new URL(url, 'http://localhost').pathname.replace(/^\/api\/v1/, '')
    const body: unknown = typeof init?.body === 'string' ? JSON.parse(init.body) : null
    sent.push({ method, path, body })
    return Promise.resolve(new Response(JSON.stringify(respond(method, path, body)), { status: 200 }))
  }))
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  cancelPendingRequests(); onUnauthorized(null)
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

async function openAbout(me: Me, checkForUpdates: boolean | 'missing' = true) {
  const session = useSession()
  session.state = 'ready'; session.me = me
  useSettings().data = settingsWith(checkForUpdates === 'missing' ? undefined : checkForUpdates)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  wrapper = mount(AboutSettings, { global: { plugins: [router], stubs: { Switch: SwitchStub } } })
  await flushPromises()
  return wrapper
}
const writes = () => sent.filter((s) => s.method !== 'GET')
const checkButton = (w: ReturnType<typeof mount>) => w.findAll('button').find((b) => b.text().includes('Check for updates'))!
const theSwitch = (w: ReturnType<typeof mount>) => w.get('button[role="switch"]')

describe('the final wording is in one place', () => {
  it('holds the approved strings', () => {
    expect(updateCheckText.label).toBe('Check for updates automatically')
    expect(updateCheckText.description).toBe('HashHurdr looks for a newer version once a day. Switch this off and it only checks when you press the button.')
    expect(updateCheckText.note).toBe('Each check is one anonymous request to GitHub, which sees your IP address and the app name and version. What comes back is the newest version number and a release link. Nothing installs by itself.')
    expect(updateCheckText.off).toBe('Automatic checks are off. The Check for updates button still works.')
  })
})

describe('the switch for the automatic update check', () => {
  it('shows the label, the description and what a check sends, with the switch on', async () => {
    const w = await openAbout(ADMIN)
    const text = w.text()
    expect(text).toContain(updateCheckText.label)
    expect(text).toContain(updateCheckText.description)
    expect(text).toContain(updateCheckText.note)
    expect(theSwitch(w).attributes('aria-checked')).toBe('true')
    expect(w.find(`label[for="${theSwitch(w).attributes('id')}"]`).text()).toContain(updateCheckText.label)
    expect(text).not.toContain(updateCheckText.off)
  })

  it('is on when the server has not sent the setting yet (the default is on)', async () => {
    const w = await openAbout(ADMIN, 'missing')
    expect(theSwitch(w).attributes('aria-checked')).toBe('true')
  })

  it('an admin turning it off saves only that setting and makes no update check', async () => {
    const w = await openAbout(ADMIN)
    await theSwitch(w).trigger('click')
    await flushPromises()
    expect(writes()).toEqual([{ method: 'PATCH', path: '/settings', body: { network: { check_for_updates: false } } }])
    expect(theSwitch(w).attributes('aria-checked')).toBe('false')
  })

  it('off: shows the off-state line and leaves the button working', async () => {
    const w = await openAbout(ADMIN, false)
    expect(theSwitch(w).attributes('aria-checked')).toBe('false')
    expect(w.text()).toContain(updateCheckText.off)
    expect(w.text()).not.toContain('You are up to date.')
    const button = checkButton(w)
    expect(button.attributes('disabled')).toBeUndefined()
    await button.trigger('click')
    await flushPromises()
    expect(writes()).toEqual([{ method: 'POST', path: '/system/update/check', body: null }])
  })

  it('off: after a button press the page shows that result instead of claiming nothing was checked', async () => {
    const w = await openAbout(ADMIN, false)
    await checkButton(w).trigger('click')
    await flushPromises()
    expect(w.text()).toContain('You are up to date.')
    expect(w.text()).not.toContain(updateCheckText.off)
  })

  it('off: a newer release found earlier is still announced', async () => {
    statusReply = NEWER
    const w = await openAbout(ADMIN, false)
    expect(w.text()).toContain('Version 99.0.0 is available.')
  })

  it('on: opening the page does not show the off-state line and a check result reads as before', async () => {
    statusReply = CHECKED_NOW
    const w = await openAbout(ADMIN, true)
    expect(w.text()).toContain('You are up to date.')
    expect(w.text()).not.toContain(updateCheckText.off)
  })

  it.each([
    ['read token', READ_TOKEN],
    ['control token', CONTROL_TOKEN],
  ])('a %s sees the switch but cannot change it', async (_who, me) => {
    const w = await openAbout(me, true)
    const control = theSwitch(w)
    expect(control.attributes('aria-checked')).toBe('true')
    expect(control.attributes('disabled')).toBeDefined()
    await control.trigger('click')
    await flushPromises()
    expect(writes()).toEqual([])
  })

  it('shows the release link the server sends for a newer version and no release text', async () => {
    statusReply = { ...NEWER, notes: 'RELEASE-TEXT-FROM-AN-OLD-SERVER' } as UpdateStatus
    const w = await openAbout(ADMIN)
    expect(w.text()).not.toContain('RELEASE-TEXT-FROM-AN-OLD-SERVER')
    const link = w.find('a[href$="/releases/tag/v99.0.0"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('rel')).toBe('noopener noreferrer')
  })
})
