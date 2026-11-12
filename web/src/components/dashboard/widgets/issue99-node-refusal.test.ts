import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { NodeRefusal } from '@/lib/types'
import NodePoolWidget from './NodePoolWidget.vue'

// The node card shows what a refusing node needs, in words (not colour alone), with the same text the API gives agents.

const live = vi.hoisted(() => ({ network: null as unknown }))
vi.mock('@/stores/live', () => ({ useLive: () => live }))
vi.mock('@/composables/useFmt', () => ({
  useFmt: () => ({ formatNumber: (n: number | null) => String(n ?? '–'), hashrate: () => '0 H/s', formatAgo: () => 'now' }),
}))
vi.mock('@/composables/useNowSec', () => ({ useNowSec: () => ({ value: 0 }) }))

const REFUSALS: Record<'needs_login' | 'computer_not_allowed', NodeRefusal> = {
  needs_login: {
    reason: 'needs_login', title: 'This node needs a login',
    message: 'The node rejected the login: wrong RPC user name or password',
    next_step: 'Umbrel: open the Bitcoin Node app, choose Connect, then RPC; it lists the user name and password.',
    hints: [], ask_user_for: ['rpc_user', 'rpc_password'], api_steps: [],
  },
  computer_not_allowed: {
    reason: 'computer_not_allowed', title: 'This node does not allow this computer',
    message: "The node refused this computer (192.168.9.15) before it even looked at the login. This is the node's allow-list (rpcallowip), not your user name or password.",
    next_step: "Add rpcallowip=192.168.9.0/24 to the node's bitcoin.conf and restart the node.",
    hints: [], ask_user_for: ['rpc_user', 'rpc_password'], api_steps: [],
  },
}

function refusedNode(refusal: NodeRefusal | null, error: string) {
  return {
    kind: 'bitcoin_core', reachable: false, error, version: null, subversion: null, chain: null, blocks: null, headers: null,
    initial_block_download: null, verification_progress: null, connections: null, connections_in: null, connections_out: null,
    mempool_tx_count: null, mempool_bytes: null, mempool_max_bytes: null, min_relay_fee_sat_vb: null, size_on_disk: null,
    pruned: null, uptime_s: null, network_active: null, best_block_hash: null, difficulty: null, network_hashrate_hs: null,
    warnings: [], checked_at: 1, refusal,
  }
}

let wrapper: ReturnType<typeof mount> | undefined
async function show(node: unknown) {
  live.network = { node, pools: [], node_behind_by: null }
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
  await router.push('/')
  wrapper = mount(NodePoolWidget, { global: { plugins: [router] } })
  return wrapper
}

beforeEach(() => { live.network = null })
afterEach(() => { wrapper?.unmount(); wrapper = undefined })

describe('node card: a node that refuses the app', () => {
  it.each([
    ['needs_login', 'Needs login'],
    ['computer_not_allowed', 'Not allowed'],
  ] as const)('says why (%s) and what to do, in words', async (reason, badge) => {
    const refusal = REFUSALS[reason]
    const card = await show(refusedNode(refusal, refusal.message))
    const block = card.get('[data-testid="node-refusal"]')
    expect(block.text()).toContain(refusal.title)
    expect(block.text()).toContain(refusal.next_step)
    expect(block.text()).toContain('What to do')
    expect(card.text()).toContain(badge)
    expect(card.text()).not.toContain('Unreachable') // a refusal is not "unreachable"
    expect(card.text().split(refusal.message).length - 1).toBeLessThanOrEqual(1) // the raw error is not repeated next to the explanation
  })

  it('names an unreadable cookie file as a cookie problem, not as an unreachable node', async () => {
    const cookie: NodeRefusal = {
      reason: 'cookie_unreadable', title: "The node's cookie file can't be read",
      message: 'The node was not contacted: cannot read the RPC cookie file (FileNotFoundError).',
      next_step: 'Start the node: Bitcoin Core only keeps its cookie file while it runs.',
      hints: [], ask_user_for: [], api_steps: [],
    }
    const card = await show(refusedNode(cookie, cookie.message))
    expect(card.get('[data-testid="node-refusal"]').text()).toContain(cookie.next_step)
    expect(card.text()).toContain('Cookie unreadable')
    expect(card.text()).not.toContain('Unreachable')
  })

  it('does not rely on colour alone: a text heading labels the group and the icon is hidden from screen readers', async () => {
    const card = await show(refusedNode(REFUSALS.computer_not_allowed, REFUSALS.computer_not_allowed.message))
    const block = card.get('[data-testid="node-refusal"]')
    expect(block.attributes('role')).toBe('group')
    const labelId = block.attributes('aria-labelledby')
    expect(labelId).toBeTruthy()
    expect(card.get(`[id="${labelId}"]`).text()).toBe(REFUSALS.computer_not_allowed.title)
    expect(block.get('svg').attributes('aria-hidden')).toBe('true')
  })

  it('shows nothing extra for a node that connects', async () => {
    const ok = { ...refusedNode(null, ''), reachable: true, error: null, refusal: null, blocks: 972174, headers: 972174, verification_progress: 1, connections: 18, mempool_tx_count: 4200 }
    const card = await show(ok)
    expect(card.find('[data-testid="node-refusal"]').exists()).toBe(false)
    expect(card.text()).toContain('Synced')
  })
})
