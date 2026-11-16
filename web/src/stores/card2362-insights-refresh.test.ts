import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { api } from '@/lib/api'
import type { Insight } from '@/lib/types'
import { useInsights } from '@/stores/insights'

// Card #2362: the getting-started checklist judges completion from these answers, so a forced refresh (asked for after
// the fleet or the sources changed) must be answered by a request made after the change, never by an older one in flight.

const insight = (id: string): Insight => ({ id, level: 'tip', title: id, body: '', action: null, device_id: null })
const EMPTY_FLEET = [insight('no-miners')]
const WITH_A_MINER = [insight('no-node'), insight('no-channel')]

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => { resolve = res })
  return { promise, resolve }
}

beforeEach(() => {
  setActivePinia(createPinia())
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('card 2362: refreshing the insights', () => {
  it('a forced refresh asked for while an older request is in flight is answered by a new request', async () => {
    const older = deferred<Insight[]>()
    const newer = deferred<Insight[]>()
    const request = vi.spyOn(api, 'insights').mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise)
    const insights = useInsights()
    void insights.refresh()
    const forced = insights.refresh(true)
    expect(request).toHaveBeenCalledTimes(1)

    older.resolve(EMPTY_FLEET)
    await flushPromises()
    expect(request).toHaveBeenCalledTimes(2)

    let answered = false
    void forced.then(() => { answered = true })
    await flushPromises()
    expect(answered).toBe(false) // still waiting for the request made after the change

    newer.resolve(WITH_A_MINER)
    await forced
    expect(insights.items.map((i) => i.id)).toEqual(['no-node', 'no-channel'])
  })

  it('a plain refresh while one is in flight still shares it', async () => {
    const only = deferred<Insight[]>()
    const request = vi.spyOn(api, 'insights').mockReturnValue(only.promise)
    const insights = useInsights()
    void insights.refresh()
    void insights.refresh()
    expect(request).toHaveBeenCalledTimes(1)
    only.resolve(EMPTY_FLEET)
    await flushPromises()
    expect(request).toHaveBeenCalledTimes(1)
    expect(insights.loaded).toBe(true)
  })

  it('a forced refresh with nothing in flight is one request', async () => {
    const request = vi.spyOn(api, 'insights').mockResolvedValue(WITH_A_MINER)
    const insights = useInsights()
    await insights.refresh(true)
    expect(request).toHaveBeenCalledTimes(1)
    expect(insights.error).toBeNull()
  })
})
