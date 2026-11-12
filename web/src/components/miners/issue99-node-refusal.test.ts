import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { api } from '@/lib/api'
import type { NodeRefusal } from '@/lib/types'
import DiscoveryPanel from './DiscoveryPanel.vue'

// The discovery result says why a found node refuses the app, right on its row, in words.

function refusedNode(host: string, refusal: NodeRefusal) {
  return {
    kind: 'bitcoin_core', url: `http://${host}:8332`, name: `Bitcoin node on ${host}`, needs_credentials: true,
    reason: 'Port 8332 (Bitcoin RPC) is open', verified: false, refusal,
  }
}
const FORBIDDEN: NodeRefusal = {
  reason: 'computer_not_allowed', title: 'This node does not allow this computer',
  message: "The node refused this computer (192.168.9.15) before it even looked at the login.",
  next_step: "Add rpcallowip=192.168.9.0/24 to the node's bitcoin.conf and restart the node.",
  hints: [], ask_user_for: ['rpc_user', 'rpc_password'], api_steps: [],
}
const NEEDS_LOGIN: NodeRefusal = {
  reason: 'needs_login', title: 'This node needs a login',
  message: 'The node asked for a login (RPC user name and password) and none was given.',
  next_step: 'Umbrel: open the Bitcoin Node app, choose Connect, then RPC; it lists the user name and password.',
  hints: [], ask_user_for: ['rpc_user', 'rpc_password'], api_steps: [],
}
const finished = {
  id: 'fixture-scan', cidrs: ['192.168.9.0/24'], status: 'finished' as const, phase: 'done', started_at: 1, finished_at: 2,
  total_hosts: 254, scanned_hosts: 254, progress: 1, miners: [], error: null,
  sources: [refusedNode('192.168.9.79', FORBIDDEN), refusedNode('192.168.9.80', NEEDS_LOGIN)],
}

let wrapper: ReturnType<typeof mount> | undefined
beforeEach(() => {
  setActivePinia(createPinia())
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: mock discovery endpoints') }))
  vi.spyOn(api, 'suggestRanges').mockResolvedValue(['192.168.9.0/24'])
  vi.spyOn(api, 'startDiscovery').mockResolvedValue(finished)
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

async function scan() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  wrapper = mount(DiscoveryPanel, { global: { plugins: [router] } })
  await flushPromises()
  await wrapper.get('[data-testid="start-scan"]').trigger('click')
  await flushPromises()
  return wrapper
}

describe('discovery result: a found node that refuses the app', () => {
  it('shows the reason and the next step on that node\'s own row', async () => {
    const panel = await scan()
    const rows = panel.findAll('[data-testid="source-refusal"]')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain(FORBIDDEN.title)
    expect(rows[0]!.text()).toContain(FORBIDDEN.next_step)
    expect(rows[1]!.text()).toContain(NEEDS_LOGIN.title)
    expect(rows[1]!.text()).toContain(NEEDS_LOGIN.next_step)
    // each explanation sits inside the row of the node it is about
    expect(rows[0]!.element.closest('li')!.textContent).toContain('192.168.9.79')
    expect(rows[1]!.element.closest('li')!.textContent).toContain('192.168.9.80')
  })

  it('is readable without colour or a mouse: a text label, a hidden icon, and the setup button is still a real button', async () => {
    const panel = await scan()
    const row = panel.get('[data-testid="source-refusal"]')
    expect(row.text()).toContain('What to do')
    expect(row.get('svg').attributes('aria-hidden')).toBe('true')
    const setup = panel.findAll('button').filter((b) => b.text().startsWith('Set up'))
    expect(setup).toHaveLength(2) // still the way to enter the login
  })

  it('shows no refusal text for a node that was not asked or a pool', async () => {
    vi.mocked(api.startDiscovery).mockResolvedValue({
      ...finished,
      sources: [{ kind: 'public_pool', url: 'http://192.168.9.4:2019', name: 'Public Pool on 192.168.9.4', needs_credentials: false, reason: 'x', verified: true }],
    })
    const panel = await scan()
    expect(panel.find('[data-testid="source-refusal"]').exists()).toBe(false)
    expect(panel.text()).toContain('Public Pool on 192.168.9.4')
  })
})
