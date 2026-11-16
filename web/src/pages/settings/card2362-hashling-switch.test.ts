import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api } from '@/lib/api'
import { HASHLING_UI } from '@/lib/hashlingText'
import type { Me, Settings } from '@/lib/types'
import { mergeSettings, useSettings } from '@/stores/settings'
import { useSession } from '@/stores/session'
import AppearanceSettings from '@/pages/settings/AppearanceSettings.vue'

// Card #2362: Settings -> Appearance has a "Hashling pop-ups" switch, on by default. It is a server setting
// (`ui.hashling_popups`), like the theme and Reduce motion, so the wall display (another browser) follows it too.
// Like those, a session that may not change settings keeps its own choice on this device.

const LOCAL_UI_KEY = 'bsmm.localAppearance'
const ADMIN: Me = { name: 'owner', scope: 'admin', via: 'token' }
const CONTROL: Me = { name: 'operator', scope: 'control', via: 'token' }
const READ_ONLY: Me = { name: 'tv', scope: 'read', via: 'public' }

function config(hashlingPopups?: boolean): Settings {
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null, ...(hashlingPopups === undefined ? {} : { hashling_popups: hashlingPopups }) },
  } as unknown as Settings
}

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

async function openAppearance(me: Me, saved?: boolean): Promise<Wrapper> {
  const session = useSession()
  session.state = 'ready'
  session.me = me
  useSettings().data = config(saved)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(AppearanceSettings, { attachTo: document.body, global: { plugins: [router] } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

function hashlingSwitch(w: Wrapper) {
  const label = w.findAll('label').find((l) => l.text().includes(HASHLING_UI.U02))
  expect(label, 'a row labelled "Hashling pop-ups"').toBeTruthy()
  return w.get(`#${label!.attributes('for')}`)
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.spyOn(api, 'updateSettings').mockImplementation(async (body) => mergeSettings(config(), body))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks()
})

describe('card 2362: the Hashling pop-ups switch', () => {
  it('is in Appearance with its description, and is on for settings saved before it existed', async () => {
    const w = await openAppearance(ADMIN)
    expect(w.text()).toContain(HASHLING_UI.U02)
    expect(w.text()).toContain(HASHLING_UI.U03)
    expect(hashlingSwitch(w).attributes('aria-checked')).toBe('true')
  })

  it('shows what was saved', async () => {
    expect(hashlingSwitch(await openAppearance(ADMIN, false)).attributes('aria-checked')).toBe('false')
  })

  it('an admin saves the choice on the server', async () => {
    const w = await openAppearance(ADMIN)
    await hashlingSwitch(w).trigger('click')
    await flushPromises()
    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.updateSettings).mock.calls[0]![0]).toEqual({ ui: { hashling_popups: false } })
    expect(useSettings().data!.ui.hashling_popups).toBe(false)
    expect(hashlingSwitch(w).attributes('aria-checked')).toBe('false')
  })

  it.each([
    ['control token', CONTROL],
    ['read-only viewer', READ_ONLY],
  ])('a %s keeps the choice on this device and sends no settings save', async (_who, me) => {
    const w = await openAppearance(me)
    await hashlingSwitch(w).trigger('click')
    await flushPromises()
    expect(api.updateSettings).not.toHaveBeenCalled()
    expect(JSON.parse(localStorage.getItem(LOCAL_UI_KEY) ?? '{}')).toMatchObject({ hashling_popups: false })
    expect(useSettings().data!.ui.hashling_popups).toBe(false)
  })

  it('a device choice is applied again after a reload', async () => {
    localStorage.setItem(LOCAL_UI_KEY, JSON.stringify({ hashling_popups: false }))
    const session = useSession()
    session.state = 'ready'
    session.me = CONTROL
    vi.spyOn(api, 'settings').mockResolvedValue(config(true))
    const loaded = await useSettings().load()
    expect(loaded.ui.hashling_popups).toBe(false)
  })
})
