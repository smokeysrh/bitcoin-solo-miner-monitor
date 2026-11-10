import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { api, cancelPendingRequests, onUnauthorized } from '@/lib/api'
import type { DashboardLayout, Settings } from '@/lib/types'
import { useSettings } from '@/stores/settings'

type Json = Record<string, unknown>

interface Held {
  /** The request body as it was when the endpoint was called (a real client serializes it at that moment). */
  sent: Json
  release: () => void
}

function fixture(): Settings {
  // Only the fields this regression touches; no backend, credentials or private data.
  return {
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null },
  } as unknown as Settings
}

/** A settings endpoint that answers each request only when the test releases it. */
function heldEndpoint() {
  const held: Held[] = []
  vi.spyOn(api, 'updateSettings').mockImplementation((change: Json) => new Promise<Settings>((resolve) => {
    const sent = JSON.parse(JSON.stringify(change)) as Json
    held.push({ sent, release: () => resolve({ ...fixture(), ui: { ...fixture().ui, ...(sent.ui as Json) } } as unknown as Settings) })
  }))
  return held
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: unit tests must mock their endpoint') }))
})
afterEach(() => {
  cancelPendingRequests(); onUnauthorized(null)
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

describe('issue 22: a queued settings save keeps what was submitted', () => {
  it('sends the dashboard layout as it was when Done was pressed, not as the editor changed it afterwards', async () => {
    const settings = useSettings(); settings.data = fixture()
    const held = heldEndpoint()
    const theme = settings.patch({ ui: { theme: 'light' } })
    // The editor hands its reactive draft to patch(), then keeps editing the same placement objects.
    const draft = reactive<DashboardLayout>({ version: 1, widgets: [{ id: 'hashrate', span: 6 }] })
    const done = settings.patch({ ui: { dashboard: draft } })
    expect(held).toHaveLength(1)
    draft.widgets[0].span = 12
    expect(settings.data!.ui.dashboard!.widgets[0].span).toBe(6)

    held[0].release(); await flushPromises()
    expect(held).toHaveLength(2)
    held[1].release(); await flushPromises()
    await Promise.all([theme, done])

    expect(held[1].sent).toEqual({ ui: { dashboard: { version: 1, widgets: [{ id: 'hashrate', span: 6 }] } } })
    expect(settings.data!.ui.dashboard!.widgets[0].span).toBe(6)
    expect(settings.saving).toBe(false)
  })
})
