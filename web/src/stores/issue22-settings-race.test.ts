import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { api, cancelPendingRequests, onUnauthorized } from '@/lib/api'
import type { Settings } from '@/lib/types'
import { useSettings } from '@/stores/settings'

type Json = Record<string, unknown>
type Section = Record<string, unknown>

interface Call {
  change: Json
  done: boolean
  finish: () => void
}

const MAX_SETTLE_ROUNDS = 10

function fixture(): Settings {
  // Only the fields this regression touches; no backend, credentials or private data.
  return {
    safety: { allow_control: true, allow_tuning: false, max_temp_c: 75 },
    auth: { mode: 'password', public_read: false },
    units: { temperature: 'c', hashrate: 'auto', currency: 'USD' },
    ui: { theme: 'dark', accent: '#F7931A', density: 'comfortable', reduce_motion: false, simple_mode: false, dashboard: null },
  } as unknown as Settings
}

/**
 * A stand-in for the settings endpoint. Like the real server it applies a request when it arrives and answers with
 * the whole settings document as it stood after that request. Each answer is held until the test releases it.
 */
function fakeServer(shouldFail: (change: Json) => boolean = () => false) {
  let state: Json = JSON.parse(JSON.stringify(fixture()))
  const calls: Call[] = []
  vi.spyOn(api, 'updateSettings').mockImplementation((change: Json) => new Promise<Settings>((resolve, reject) => {
    const fails = shouldFail(change)
    if (!fails) {
      for (const [key, value] of Object.entries(change)) state = { ...state, [key]: { ...(state[key] as Section), ...(value as Section) } }
    }
    const snapshot: Json = JSON.parse(JSON.stringify(state))
    const call: Call = {
      change,
      done: false,
      finish: () => (fails ? reject(new Error('save failed')) : resolve(snapshot as unknown as Settings)),
    }
    calls.push(call)
  }))
  /** Answer the most recently issued unanswered request first, until nothing is outstanding. */
  async function settleNewestFirst(): Promise<void> {
    await flushPromises()
    for (let round = 0; round < MAX_SETTLE_ROUNDS; round++) {
      const open = calls.filter((c) => !c.done)
      if (open.length === 0) return
      const call = open[open.length - 1]
      call.done = true
      call.finish()
      await flushPromises()
    }
  }
  return { calls, settleNewestFirst, server: () => state }
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

describe('issue 22: overlapping settings saves', () => {
  it('keeps both of two quick saves to different fields when answers finish in reverse order', async () => {
    const settings = useSettings(); settings.data = fixture()
    const fake = fakeServer()
    const first = settings.patch({ safety: { allow_control: false } })
    const second = settings.patch({ auth: { public_read: true } })
    await fake.settleNewestFirst()
    await Promise.all([first, second])
    expect(fake.server()).toMatchObject({ safety: { allow_control: false }, auth: { public_read: true } })
    expect(settings.data!.safety.allow_control).toBe(false)
    expect(settings.data!.auth.public_read).toBe(true)
    expect(settings.data).toEqual(fake.server())
    expect(settings.saving).toBe(false)
  })

  it('lets the newer save to the same field win when the older answer arrives last', async () => {
    const settings = useSettings(); settings.data = fixture()
    const fake = fakeServer()
    const on = settings.patch({ safety: { allow_tuning: true } })
    const off = settings.patch({ safety: { allow_tuning: false } })
    await fake.settleNewestFirst()
    await Promise.all([on, off])
    expect(fake.server()).toMatchObject({ safety: { allow_tuning: false } })
    expect(settings.data!.safety.allow_tuning).toBe(false)
    expect(settings.data).toEqual(fake.server())
    expect(settings.saving).toBe(false)
  })

  it('rolls back only the failed save when the older save fails after the newer one succeeds', async () => {
    const settings = useSettings(); settings.data = fixture()
    const fake = fakeServer((change) => 'safety' in change)
    const failing = settings.patch({ safety: { allow_control: false } })
    const succeeding = settings.patch({ auth: { public_read: true } })
    const failed = expect(failing).rejects.toThrow('save failed')
    await fake.settleNewestFirst()
    await failed; await succeeding
    expect(settings.data!.safety.allow_control).toBe(true)
    expect(settings.data!.auth.public_read).toBe(true)
    expect(settings.data).toEqual(fake.server())
    expect(settings.saving).toBe(false)
  })

  it('keeps the older successful save when the newer save fails', async () => {
    const settings = useSettings(); settings.data = fixture()
    const fake = fakeServer((change) => 'auth' in change)
    const succeeding = settings.patch({ safety: { allow_control: false } })
    const failing = settings.patch({ auth: { public_read: true } })
    const failed = expect(failing).rejects.toThrow('save failed')
    await fake.settleNewestFirst()
    await succeeding; await failed
    expect(settings.data!.safety.allow_control).toBe(false)
    expect(settings.data!.auth.public_read).toBe(false)
    expect(settings.data).toEqual(fake.server())
    expect(settings.saving).toBe(false)
  })

  it('returns a failed same-field save to the value the earlier save confirmed', async () => {
    const settings = useSettings(); settings.data = fixture()
    const fake = fakeServer((change) => (change.safety as Section | undefined)?.max_temp_c === 90)
    const confirmed = settings.patch({ safety: { max_temp_c: 80 } })
    const failing = settings.patch({ safety: { max_temp_c: 90 } })
    const failed = expect(failing).rejects.toThrow('save failed')
    await fake.settleNewestFirst()
    await confirmed; await failed
    expect(settings.data!.safety.max_temp_c).toBe(80)
    expect(settings.data).toEqual(fake.server())
  })

  it('discards both overlapping saves after the session ends', async () => {
    const settings = useSettings(); settings.data = fixture()
    const fake = fakeServer()
    const first = settings.patch({ safety: { allow_control: false } })
    const second = settings.patch({ auth: { public_read: true } })
    const rejected = Promise.all([expect(first).rejects.toBeInstanceOf(Error), expect(second).rejects.toBeInstanceOf(Error)])
    settings.clear()
    await fake.settleNewestFirst()
    await rejected
    expect(settings.data).toBeNull(); expect(settings.saving).toBe(false)
  })
})
