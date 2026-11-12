import { expect, test, type Page } from '@playwright/test'

// EVIDENCE ONLY (issue #99), never merged. Against the demo server it shows the dashboard node card and the discovery result for
// nodes that refuse the app, and saves full-page PNGs. The demo fleet has no refusing node, so the two API answers that would carry
// one (/overview's node and the scan result) are replaced here; nothing touches a real network or node. The test ends with an
// intentional failure so CI's failure-only artifact upload keeps test-results/evidence/*.png.

const SHOT_DIR = 'test-results/evidence'

const NEEDS_LOGIN = {
  reason: 'needs_login', title: 'This node needs a login',
  message: 'The node rejected the login: wrong RPC user name or password',
  next_step: 'Umbrel: open the Bitcoin Node app, choose Connect, then RPC; it lists the user name and password. '
    + "Start9 / RaspiBlitz / myNode: the RPC user and password are shown in the node's own Connect or Credentials page.",
  hints: [], ask_user_for: ['rpc_user', 'rpc_password'], api_steps: [],
}
const NOT_ALLOWED = {
  reason: 'computer_not_allowed', title: 'This node does not allow this computer',
  message: "The node refused this computer (192.168.1.20) before it even looked at the login. This is the node's allow-list (rpcallowip), not your user name or password.",
  next_step: "Add rpcallowip=192.168.1.0/24 to the node's bitcoin.conf (on Umbrel, look in the Bitcoin Node app's advanced settings; elsewhere edit bitcoin.conf) and restart the node.",
  hints: [], ask_user_for: ['rpc_user', 'rpc_password'], api_steps: [],
}

function refusedNode(refusal: typeof NOT_ALLOWED) {
  return {
    kind: 'bitcoin_core', reachable: false, error: refusal.message, refusal, version: null, subversion: null, chain: null, blocks: null,
    headers: null, initial_block_download: null, verification_progress: null, connections: null, connections_in: null, connections_out: null,
    mempool_tx_count: null, mempool_bytes: null, mempool_max_bytes: null, min_relay_fee_sat_vb: null, size_on_disk: null, pruned: null,
    uptime_s: null, network_active: null, best_block_hash: null, difficulty: null, network_hashrate_hs: null, warnings: [], checked_at: 1,
  }
}

function scanWithRefusingNodes() {
  const node = (host: string, refusal: typeof NOT_ALLOWED) => ({
    kind: 'bitcoin_core', url: `http://${host}:8332`, name: `Bitcoin node on ${host}`, needs_credentials: true,
    reason: 'Port 8332 (Bitcoin RPC) is open', verified: false, refusal,
  })
  return {
    id: 'evidence-scan', cidrs: ['192.168.1.0/24'], status: 'finished', phase: 'done', started_at: 1, finished_at: 2,
    total_hosts: 254, scanned_hosts: 254, progress: 1, miners: [], error: null,
    sources: [node('192.168.1.79', NOT_ALLOWED), node('192.168.1.80', NEEDS_LOGIN)],
  }
}

async function capture(page: Page, label: string): Promise<void> {
  await page.route('**/api/v1/overview', async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    body.network = { ...body.network, node: refusedNode(NOT_ALLOWED) }
    await route.fulfill({ response, json: body })
  })
  await page.route('**/api/v1/discovery', (route) => (route.request().method() === 'POST' ? route.fulfill({ json: scanWithRefusingNodes() }) : route.fallback()))

  await page.goto('/')
  const card = page.getByTestId('widget-nodepool')
  await card.scrollIntoViewIfNeeded()
  await expect(page.getByTestId('node-refusal')).toContainText('This node does not allow this computer')
  await page.screenshot({ path: `${SHOT_DIR}/99-node-card-${label}.png`, fullPage: true })

  await page.getByTestId('add-miner').click()
  await page.getByTestId('start-scan').click()
  await expect(page.getByTestId('source-refusal')).toHaveCount(2)
  await page.screenshot({ path: `${SHOT_DIR}/99-discovery-result-${label}.png`, fullPage: true })
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear())
})

test('evidence 99: refusing node on the node card and in the discovery result (desktop)', async ({ page }) => {
  await capture(page, 'desktop')
  expect('evidence-only').toBe('intentional failure')
})

test('evidence 99: refusing node on the node card and in the discovery result @phone', async ({ page }) => {
  await capture(page, 'phone')
  expect('evidence-only').toBe('intentional failure')
})
