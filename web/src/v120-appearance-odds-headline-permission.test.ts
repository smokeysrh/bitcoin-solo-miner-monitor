import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api } from '@/lib/api'
import type { Settings } from '@/lib/types'
import { mergeSettings, useSettings } from '@/stores/settings'
import { useSession } from '@/stores/session'
import AppearanceSettings from '@/pages/settings/AppearanceSettings.vue'

// v1.2.0 (PR #95): the odds headline is saved in `ui.kiosk`, which only an admin may change (PATCH /api/v1/settings).
// A public-read viewer would get a 401 (and be sent to sign-in); a read-only token would get a 403. Settings -> Appearance
// must therefore not offer it to them. The real AppearanceSettings runs here; only the network call is replaced.

const SETTING = '[data-testid="kiosk-odds-headline-setting"]'
const KIOSK = { rotate_s: 20, panels: ['odds', 'network'], show_clock: false }

function config(): Settings {
  return {
    general: { instance_name: 'Fixture fleet', onboarding_done: true },
    polling: { interval_s: 5, timeout_s: 3 },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null, kiosk: KIOSK },
  } as unknown as Settings
}

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

async function openAppearance(me: { name: string; scope: 'read' | 'control' | 'admin'; via: string }): Promise<Wrapper> {
  const session = useSession()
  session.state = 'ready'
  session.me = me
  useSettings().data = config()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(AppearanceSettings, { attachTo: document.body, global: { plugins: [router] } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(api, 'updateSettings').mockImplementation(async (body) => mergeSettings(config(), body))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.restoreAllMocks()
})

describe('PR 95: Settings -> Appearance odds headline needs admin rights', () => {
  it.each([
    { who: 'public-read viewer', me: { name: 'tv', scope: 'read' as const, via: 'public' } },
    { who: 'read-only token', me: { name: 'viewer', scope: 'read' as const, via: 'token' } },
  ])('does not let a $who change it, and sends no settings save', async ({ me }) => {
    const wrapper = await openAppearance(me)
    const control = wrapper.find(SETTING)
    if (control.exists()) {
      // offered: it must be disabled, and a change attempt must go nowhere
      expect((control.element as HTMLSelectElement).disabled, 'the odds headline control is disabled').toBe(true)
      await control.setValue('year')
      await flushPromises()
    }
    expect(api.updateSettings).not.toHaveBeenCalled()
  })

  it('still lets an admin change it (the control is not over-gated)', async () => {
    const wrapper = await openAppearance({ name: 'owner', scope: 'admin', via: 'token' })
    const select = wrapper.get(SETTING).element as HTMLSelectElement
    expect(select.disabled).toBe(false)
    await wrapper.get(SETTING).setValue('year')
    await flushPromises()
    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.updateSettings).mock.calls[0]![0]).toEqual({ ui: { kiosk: { ...KIOSK, odds_headline: 'year' } } })
  })
})
