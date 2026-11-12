import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api } from '@/lib/api'
import type { Me, Settings } from '@/lib/types'
import { mergeSettings, useSettings } from '@/stores/settings'
import { useSession } from '@/stores/session'
import AppearanceSettings from '@/pages/settings/AppearanceSettings.vue'

// Card #2372: PATCH /api/v1/settings only accepts an admin. A control token is not read-only, but it still cannot
// write settings, so its theme and accent choices must stay on this device (the same path read-only viewers use)
// instead of going to the server and coming back as a forbidden toast. Admin and open (no password) mode are admins
// and keep saving to the server. The real store and Appearance page run here; only the network calls are replaced.

const LOCAL_UI_KEY = 'bsmm.localAppearance'
const VIOLET = '#A78BFA'

const PUBLIC_READ: Me = { name: 'tv', scope: 'read', via: 'public' }
const READ_TOKEN: Me = { name: 'viewer', scope: 'read', via: 'token' }
const CONTROL_TOKEN: Me = { name: 'operator', scope: 'control', via: 'token' }
const ADMIN_TOKEN: Me = { name: 'owner', scope: 'admin', via: 'token' }
const OPEN_MODE: Me = { name: 'admin', scope: 'admin', via: 'none' }

const KEEP_ON_DEVICE: { who: string; me: Me }[] = [
  { who: 'public-read viewer', me: PUBLIC_READ },
  { who: 'read-only token', me: READ_TOKEN },
  { who: 'control token', me: CONTROL_TOKEN },
]
const SAVE_TO_SERVER: { who: string; me: Me }[] = [
  { who: 'admin token', me: ADMIN_TOKEN },
  { who: 'open (no password) mode', me: OPEN_MODE },
]

function config(): Settings {
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null },
  } as unknown as Settings
}

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

function signIn(me: Me): void {
  const session = useSession()
  session.state = 'ready'
  session.me = me
}

async function openAppearance(me: Me): Promise<Wrapper> {
  signIn(me)
  useSettings().data = config()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(AppearanceSettings, { attachTo: document.body, global: { plugins: [router] } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

const stored = (): Record<string, unknown> => JSON.parse(localStorage.getItem(LOCAL_UI_KEY) ?? '{}') as Record<string, unknown>

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.spyOn(api, 'updateSettings').mockImplementation(async (body) => mergeSettings(config(), body))
  vi.spyOn(api, 'settings').mockResolvedValue(config())
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks()
  localStorage.clear()
})

describe('card 2372: Appearance theme and accent for sessions that cannot write settings', () => {
  it.each(KEEP_ON_DEVICE)('keeps a $who theme and accent choice on this device and sends no settings save', async ({ me }) => {
    const wrapper = await openAppearance(me)
    await wrapper.get('[data-testid="theme-light"]').trigger('click')
    await wrapper.get('button[aria-label="Violet"]').trigger('click')
    await flushPromises()
    expect(api.updateSettings).not.toHaveBeenCalled()
    const settings = useSettings()
    expect(settings.data?.ui.theme).toBe('light')
    expect(settings.data?.ui.accent).toBe(VIOLET)
    expect(stored()).toMatchObject({ theme: 'light', accent: VIOLET })
    expect(settings.localOnly).toBe(true)
  })

  it.each(SAVE_TO_SERVER)('still saves a $who theme and accent choice to the server (not over-gated)', async ({ me }) => {
    const wrapper = await openAppearance(me)
    await wrapper.get('[data-testid="theme-light"]').trigger('click')
    await flushPromises()
    await wrapper.get('button[aria-label="Violet"]').trigger('click')
    await flushPromises()
    expect(api.updateSettings).toHaveBeenCalledTimes(2)
    expect(vi.mocked(api.updateSettings).mock.calls[0]![0]).toEqual({ ui: { theme: 'light' } })
    expect(vi.mocked(api.updateSettings).mock.calls[1]![0]).toEqual({ ui: { accent: VIOLET } })
    expect(localStorage.getItem(LOCAL_UI_KEY)).toBeNull()
    expect(useSettings().localOnly).toBe(false)
  })
})

describe('card 2372: settings store appearance path by role', () => {
  it('shows a control token the look it kept on this device after a reload', async () => {
    localStorage.setItem(LOCAL_UI_KEY, JSON.stringify({ theme: 'amoled', accent: VIOLET }))
    signIn(CONTROL_TOKEN)
    const settings = useSettings()
    await settings.load()
    expect(settings.data?.ui.theme).toBe('amoled')
    expect(settings.data?.ui.accent).toBe(VIOLET)
    expect(settings.localOnly).toBe(true)
  })

  it.each(SAVE_TO_SERVER)('does not apply a device-only look over the server settings of a $who', async ({ me }) => {
    localStorage.setItem(LOCAL_UI_KEY, JSON.stringify({ theme: 'amoled', accent: VIOLET }))
    signIn(me)
    const settings = useSettings()
    await settings.load()
    expect(settings.data?.ui.theme).toBe('dark')
    expect(settings.localOnly).toBe(false)
  })

  it('still sends a control token a non-appearance change to the server, which owns that refusal', async () => {
    signIn(CONTROL_TOKEN)
    const settings = useSettings()
    settings.data = config()
    await settings.patch({ general: { instance_name: 'Renamed' } })
    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.updateSettings).mock.calls[0]![0]).toEqual({ general: { instance_name: 'Renamed' } })
    expect(localStorage.getItem(LOCAL_UI_KEY)).toBeNull()
  })
})
