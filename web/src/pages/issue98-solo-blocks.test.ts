import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api, ApiError, cancelPendingRequests, onUnauthorized } from '@/lib/api'
import { NAV } from '@/lib/nav'
import type { SoloBlock, SoloBlocksResult } from '@/lib/types'
import SoloBlocksPage from '@/pages/SoloBlocksPage.vue'

// Issue #98: the Solo blocks page. Only the HTTP-facing api method is mocked; the real page, ErrorState,
// StaleNotice and formatters render. The server owns the order, the 20-block limit and the "yours" rule
// (tests/test_issue98_solo_blocks.py); the page must show exactly what it is given and never turn a failure
// into an empty list.

const DAY = 86_400
const wrappers: { unmount: () => void }[] = []

const hashOf = (height: number): string => height.toString(16).padStart(64, '0')
function blk(height: number, pool: string, ageS: number, yours = false): SoloBlock {
  const hash = hashOf(height)
  return { hash, height, ts: Date.now() / 1000 - ageS, pool_slug: pool.toLowerCase().replace(/\W/g, ''), pool_name: pool, tx_count: 2000, url: `https://mempool.space/block/${hash}`, yours }
}
const POOLS = [{ slug: 'solock', name: 'Solo CK' }, { slug: 'publicpool', name: 'Public Pool' }]
function result(over: Partial<SoloBlocksResult> = {}): SoloBlocksResult {
  return {
    available: true, message: null, source: 'https://mempool.space', fetched_at: Date.now() / 1000, stale: false, error: null, failed_pools: [],
    pools: POOLS, limit: 20,
    blocks: [blk(959_001, 'Solo CK', 3 * DAY + 3600), blk(957_382, 'Public Pool', 20 * DAY + 3600, true), blk(950_210, 'Solo CK', 80 * DAY + 3600)],
    ...over,
  }
}
const failure = (message: string) => new ApiError(502, 'solo_blocks_unavailable', message)

async function mountPage() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:rest(.*)*', component: { template: '<div />' } }] })
  await router.push('/solo-blocks')
  await router.isReady()
  const wrapper = mount(SoloBlocksPage, { global: { plugins: [router] } })
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

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: tests must mock their endpoint') }))
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  cancelPendingRequests(); onUnauthorized(null)
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

describe('issue 98: Solo blocks page', () => {
  it('is in the navigation next to the other monitoring pages', () => {
    expect(NAV.find((n) => n.name === 'solo-blocks')).toMatchObject({ to: '/solo-blocks', label: 'Solo blocks', group: 'monitor' })
  })

  it('lists the blocks in the order given with height, age, pool and a mempool.space link, as a real list', async () => {
    vi.spyOn(api, 'soloBlocks').mockResolvedValue(result())
    const wrapper = await mountPage()
    const list = wrapper.get('[data-testid="solo-block-list"]')
    expect(list.element.tagName).toBe('OL')
    expect(list.attributes('aria-label')).toBeTruthy()
    const items = wrapper.findAll('[data-testid="solo-block"]')
    expect(items).toHaveLength(3)
    expect(items.map((i) => i.get('[data-testid="solo-block-height"]').text())).toEqual(['959,001', '957,382', '950,210'])
    expect(items[0]!.text()).toContain('Solo CK')
    expect(items[0]!.text()).toContain('3d ago')
    expect(items[1]!.text()).toContain('Public Pool')
    expect(items[2]!.text()).toContain('2mo ago')
    const link = items[0]!.get('a')
    expect(link.attributes('href')).toBe(`https://mempool.space/block/${hashOf(959_001)}`)
    expect(link.attributes('rel')).toContain('noopener')
    expect(link.attributes('aria-label')).toBe('Block 959,001 on mempool.space')
  })

  it('highlights the user\'s own block with words, not only colour, and nothing else', async () => {
    vi.spyOn(api, 'soloBlocks').mockResolvedValue(result())
    const wrapper = await mountPage()
    const items = wrapper.findAll('[data-testid="solo-block"]')
    expect(items.map((i) => i.text().includes('Yours'))).toEqual([false, true, false])
    expect(items.map((i) => i.attributes('data-yours'))).toEqual(['false', 'true', 'false'])
  })

  it('a successful empty result says there are none yet', async () => {
    vi.spyOn(api, 'soloBlocks').mockResolvedValue(result({ blocks: [] }))
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('No solo-pool blocks')
    expect(wrapper.find('[data-testid="solo-block-list"]').exists()).toBe(false)
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('a failed load is an error with retry, never an empty list; retry recovers', async () => {
    const load = vi.spyOn(api, 'soloBlocks').mockRejectedValue(failure('Could not read solo-pool blocks from https://mempool.space: timed out'))
    const wrapper = await mountPage()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('timed out')
    expect(wrapper.text()).not.toContain('No solo-pool blocks')
    expect(wrapper.find('[data-testid="solo-block-list"]').exists()).toBe(false)
    load.mockResolvedValue(result())
    await tryAgain(wrapper)
    expect(wrapper.findAll('[data-testid="solo-block"]')).toHaveLength(3)
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('timed out')
  })

  it('outside lookups off shows the plain message and a way to Settings, not an error or an empty list', async () => {
    vi.spyOn(api, 'soloBlocks').mockResolvedValue(result({ available: false, blocks: [], message: 'Outside lookups are turned off. Turn on “Use mempool.space” in Settings > Node & pool to list solo-pool blocks.' }))
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('Outside lookups are turned off')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('No solo-pool blocks')
    expect(wrapper.find('[data-testid="solo-block-list"]').exists()).toBe(false)
    expect(wrapper.find('a[href="/settings/sources"]').exists()).toBe(true)
  })

  it('a list that could not be refreshed stays visible under a stale notice; retry clears it', async () => {
    const load = vi.spyOn(api, 'soloBlocks').mockResolvedValue(result({ stale: true, error: 'Could not read solo-pool blocks from https://mempool.space: connection refused' }))
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('could not be loaded or refreshed')
    expect(wrapper.text()).toContain('connection refused')
    expect(wrapper.findAll('[data-testid="solo-block"]')).toHaveLength(3)
    load.mockResolvedValue(result())
    await tryAgain(wrapper)
    expect(wrapper.text()).not.toContain('could not be loaded or refreshed')
    expect(wrapper.findAll('[data-testid="solo-block"]')).toHaveLength(3)
  })

  it('a client-side failed retry after a good load keeps the list and shows the stale notice', async () => {
    const load = vi.spyOn(api, 'soloBlocks').mockResolvedValue(result({ stale: true, error: 'old failure' }))
    const wrapper = await mountPage()
    load.mockRejectedValue(failure('still down'))
    await tryAgain(wrapper)
    expect(wrapper.findAll('[data-testid="solo-block"]')).toHaveLength(3)
    expect(wrapper.text()).toContain('still down')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('names the pools that could not be read, so a partial list does not look complete', async () => {
    vi.spyOn(api, 'soloBlocks').mockResolvedValue(result({ failed_pools: ['Public Pool'] }))
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('Public Pool')
    expect(wrapper.get('[data-testid="solo-blocks-partial"]').text()).toContain('Public Pool')
    expect(wrapper.findAll('[data-testid="solo-block"]')).toHaveLength(3)
  })
})
