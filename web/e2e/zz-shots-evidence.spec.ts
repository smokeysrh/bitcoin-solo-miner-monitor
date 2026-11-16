import { expect, test, type APIRequestContext, type BrowserContext, type Locator, type Page, type TestInfo } from '@playwright/test'
import { poolChangeText } from '../src/lib/poolChangeText'

// EVIDENCE ONLY (never merge): screenshots of every Hashling moment (card #2362) on the dashboard and, for M01..M17, on the
// wall display, against a demo server (`--demo --offline`). Demo scenario buttons/API are used where one exists (offline,
// online, hot, block, pool_change). Everything else is driven through the real live stream: a test-only wrapper around
// EventSource (added here by an init script, nothing in shipped code) lets the test deliver a stream message to the page's
// own handlers, so the pop-ups go through the same code as a real event. API answers are replaced only where a moment needs
// a state the demo cannot be put in (no miners yet, an unfinished checklist, a notification channel).
// The last test fails on purpose so that CI keeps and uploads the screenshots.

const SCENARIO_WAIT_MS = 180_000
const POPUP_WAIT_MS = 20_000
const SYNTHETIC_ID_BASE = 9_000_000

type Surface = 'dash' | 'wall'
type Inject = [topic: string, payload: unknown]
interface Dev { id: string; name: string }

/** Test-only: a real EventSource that also lets the test deliver messages to the page's own stream handlers. */
async function tapEventSource(context: BrowserContext): Promise<void> {
  await context.addInitScript(() => {
    const w = window as unknown as { __inject: (topic: string, payload: unknown) => void; __dropDeviceTopic?: boolean }
    const Real = window.EventSource
    const instances: EventSource[] = []
    function Tapped(url: string | URL, init?: EventSourceInit): EventSource {
      const es = new Real(url, init)
      const add = es.addEventListener.bind(es) as (type: string, listener: unknown, options?: unknown) => void
      es.addEventListener = ((type: string, listener: unknown, options?: unknown) => {
        if (type === 'device' && w.__dropDeviceTopic) return // lets a test keep the fleet empty
        add(type, listener, options)
      }) as unknown as typeof es.addEventListener
      instances.push(es)
      return es
    }
    Tapped.prototype = Real.prototype
    window.EventSource = Tapped as unknown as typeof EventSource
    w.__inject = (topic, payload) => {
      for (const es of instances) es.dispatchEvent(new MessageEvent(topic, { data: JSON.stringify(payload) }))
    }
  })
}

async function inject(page: Page, ...messages: Inject[]): Promise<void> {
  await page.evaluate((list) => {
    const w = window as unknown as { __inject: (topic: string, payload: unknown) => void }
    for (const [topic, payload] of list) w.__inject(topic, payload)
  }, messages)
}

let seq = SYNTHETIC_ID_BASE
interface EventFields { device_id?: string | null; body?: string | null; data?: Record<string, unknown> }
const eventMessage = (type: string, severity: string, f: EventFields = {}): Inject => [
  'event',
  { id: ++seq, ts: Date.now() / 1000, type, severity, device_id: f.device_id ?? null, title: 'evidence event', body: f.body ?? null, data: f.data ?? {}, dedupe_key: null, ack_ts: null },
]
const alertsMessage = (kind: string, severity: string, device: string | null, suffix = device ?? 'fleet'): Inject => [
  'alerts',
  { active: [{ key: `rule_${kind}:${suffix}`, rule_id: `rule_${kind}`, since: ++seq, title: 'evidence alert', body: null, device_id: device, severity }] },
]

async function devices(request: APIRequestContext): Promise<Dev[]> {
  const list = (await (await request.get('/api/v1/devices')).json()) as Dev[]
  expect(list.length).toBeGreaterThanOrEqual(3)
  return list.map(({ id, name }) => ({ id, name }))
}

const popup = (page: Page, ...ids: string[]): Locator => page.locator(ids.map((id) => `[data-testid="hashling-popup"][data-moment="${id}"]`).join(', '))

async function clearPopups(page: Page): Promise<void> {
  for (let i = 0; i < 12; i++) {
    const open = page.locator('[data-testid="hashling-popup"] button')
    if ((await open.count()) === 0) return
    await open.first().click()
  }
}

async function open(page: Page, surface: Surface, path?: string): Promise<void> {
  await page.goto(path ?? (surface === 'wall' ? '/kiosk' : '/'))
  await expect(page.getByTestId('live-badge').first()).toContainText('Live')
}

async function shot(page: Page, info: TestInfo, surface: Surface, id: string, slug: string): Promise<void> {
  await page.screenshot({ path: info.outputPath(`${surface}-${id}-${slug}.png`) })
}

/** Show a moment, wait for it, take the picture, put it away. */
async function capture(page: Page, info: TestInfo, surface: Surface, id: string, slug: string, fire: () => Promise<void>): Promise<void> {
  await clearPopups(page)
  await fire()
  await expect(popup(page, id)).toBeVisible({ timeout: POPUP_WAIT_MS })
  await shot(page, info, surface, id, slug)
  await clearPopups(page)
}

async function scenario(request: APIRequestContext, name: string): Promise<void> {
  const r = await request.post('/api/v1/demo/scenario', { data: { scenario: name } })
  expect(r.ok(), `demo scenario ${name}`).toBe(true)
}

const NAMES: Record<string, string> = { M16: 'miner-back', M17: 'every-miner-hashing' }

test.beforeEach(async ({ page, request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', hashling_popups: true, reduce_motion: false } } })
  await tapEventSource(page.context())
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('shots-init')) {
      localStorage.clear()
      sessionStorage.setItem('shots-init', '1')
    }
  })
})

test('real demo scenarios on the dashboard and the wall display (pool change, offline, back, block)', async ({ page, context, request }, info) => {
  test.setTimeout(900_000)
  await scenario(request, 'online')
  await scenario(request, 'cool')
  await open(page, 'dash')
  const wall = await context.newPage()
  await open(wall, 'wall')

  // pool or payout changed (M01), then Accept (M24) on the miner page
  await scenario(request, 'pool_change')
  for (const [p, surface] of [[page, 'dash'], [wall, 'wall']] as const) {
    await expect(popup(p, 'M01')).toBeVisible({ timeout: POPUP_WAIT_MS })
    await shot(p, info, surface, 'M01', 'pool-change')
  }
  await clearPopups(page)
  await clearPopups(wall)
  const changed = await page.evaluate(async () => {
    const list = (await (await fetch('/api/v1/devices')).json()) as Array<{ id: string; pool_change?: unknown }>
    return list.find((d) => d.pool_change)?.id ?? null
  })
  expect(changed, 'a miner with an open pool change').not.toBeNull()
  await page.goto(`/miners/${changed}`)
  await page.getByTestId('accept-pool-change').click()
  await page.getByRole('button', { name: poolChangeText.confirmLabel }).click()
  await expect(popup(page, 'M24')).toBeVisible({ timeout: POPUP_WAIT_MS })
  await shot(page, info, 'dash', 'M24', 'pool-change-accepted')
  await clearPopups(page)
  await open(page, 'dash')

  // a miner goes offline (M02)
  await scenario(request, 'offline')
  for (const [p, surface] of [[page, 'dash'], [wall, 'wall']] as const) {
    await expect(popup(p, 'M02')).toBeVisible({ timeout: SCENARIO_WAIT_MS })
    await shot(p, info, surface, 'M02', 'offline')
  }
  await clearPopups(page)
  await clearPopups(wall)

  // and comes back: every miner is hashing (M17), or the single "back" pop-up (M16)
  await scenario(request, 'online')
  for (const [p, surface] of [[page, 'dash'], [wall, 'wall']] as const) {
    const back = popup(p, 'M16', 'M17')
    await expect(back).toBeVisible({ timeout: SCENARIO_WAIT_MS })
    const id = (await back.getAttribute('data-moment')) ?? 'M16'
    await shot(p, info, surface, id, NAMES[id] ?? 'back')
  }
  await clearPopups(page)
  await clearPopups(wall)

  // a found block (M13): the dialog wears Hashling on the dashboard, the pop-up carries it on the wall display
  await scenario(request, 'block')
  await expect(page.getByTestId('celebration')).toBeVisible({ timeout: POPUP_WAIT_MS })
  await shot(page, info, 'dash', 'M13', 'block-found')
  await expect(popup(wall, 'M13')).toBeVisible({ timeout: POPUP_WAIT_MS })
  await shot(wall, info, 'wall', 'M13', 'block-found')
  await page.keyboard.press('Escape')
})

test('real hot scenario (M04) on the dashboard and the wall display', async ({ page, context, request }, info) => {
  test.setTimeout(600_000)
  await scenario(request, 'cool')
  await open(page, 'dash')
  const wall = await context.newPage()
  await open(wall, 'wall')
  await scenario(request, 'hot')
  try {
    for (const [p, surface] of [[page, 'dash'], [wall, 'wall']] as const) {
      await expect(popup(p, 'M04')).toBeVisible({ timeout: SCENARIO_WAIT_MS })
      await shot(p, info, surface, 'M04', 'hot')
    }
  } finally {
    await scenario(request, 'cool')
  }
})

/** Moments with no demo scenario: delivered through the page's own stream handlers (see the top of this file). */
test('stream moments on the dashboard and the wall display', async ({ page, request }, info) => {
  test.setTimeout(600_000)
  const [a, b, c] = await devices(request)
  const overview = (await (await request.get('/api/v1/overview')).json()) as { network: { sources: unknown[] } }
  const node = { id: 'evidence-node', kind: 'bitcoin_core', name: 'Home node', ok: false, error: 'No answer', last_ok: null, last_poll: null, implicit: false }
  const network: Inject = ['network', { ...overview.network, sources: [...overview.network.sources, node] }]
  const added = (d: Dev): Inject => eventMessage('device_added', 'info', { device_id: d.id })
  const offline = (d: Dev): Inject => eventMessage('device_offline', 'critical', { device_id: d.id })
  const online = (d: Dev): Inject => eventMessage('device_online', 'success', { device_id: d.id })

  // Order matters: the good-news "back" moments come before any outage, so M17 is shown on its own later.
  const moments: Array<[id: string, slug: string, messages: () => Inject[]]> = [
    ['M16', 'miner-back', () => [online(a)]],
    ['M16N', 'miners-back', () => [online(a), online(b)]],
    ['M15', 'miner-added', () => [added(a)]],
    ['M15N', 'miners-added', () => [added(a), added(b), added(c)]],
    ['M14', 'best-share', () => [eventMessage('new_best_share', 'success', { device_id: b.id })]],
    ['M12', 'not-hashing', () => [eventMessage('device_degraded', 'warning', { device_id: a.id, body: 'Not hashing' })]],
    ['M11', 'needs-attention', () => [eventMessage('device_degraded', 'warning', { device_id: c.id, body: 'Fault reported: overcurrent' })]],
    ['M08', 'fallback-pool', () => [eventMessage('pool_failover', 'warning', { device_id: b.id })]],
    ['M03', 'fan-stopped', () => [alertsMessage('fan_failure', 'critical', a.id)]],
    ['M04', 'hot-synthetic', () => [alertsMessage('temp_high', 'warning', b.id)]],
    ['M05', 'hashrate-drop', () => [alertsMessage('hashrate_drop', 'warning', c.id)]],
    ['M06', 'total-hashrate-drop', () => [alertsMessage('fleet_hashrate_drop', 'warning', null)]],
    ['M07', 'rejected-shares', () => [alertsMessage('reject_rate_high', 'warning', a.id)]],
    ['M09', 'node-unreachable', () => [network, alertsMessage('node_down', 'warning', null, node.id)]],
    ['M10', 'node-behind', () => [network, alertsMessage('node_behind', 'warning', null, 'node')]],
    ['M02', 'offline-synthetic', () => [offline(a)]],
    ['M17', 'every-miner-hashing-synthetic', () => [online(a)]],
    ['M02N', 'offline-several', () => [offline(a), offline(b), offline(c)]],
    ['M1XN', 'several-things', () => [offline(a), eventMessage('pool_failover', 'warning', { device_id: b.id }), alertsMessage('temp_high', 'warning', c.id)]],
  ]

  for (const surface of ['dash', 'wall'] as const) {
    await open(page, surface)
    for (const [id, slug, messages] of moments) {
      await capture(page, info, surface, id, slug, () => inject(page, ...messages()))
    }
  }
})

test('dashboard-only moments: setup, empty miners, checklist, notifications, odds joke (M18 to M23, M25)', async ({ page, context, request }, info) => {
  test.setTimeout(300_000)
  const [a] = await devices(request)

  // setup page: welcome (M18) and finished (M19)
  await open(page, 'dash', '/setup')
  await expect(page.getByTestId('setup-start')).toBeVisible()
  await shot(page, info, 'dash', 'M18', 'setup-welcome')
  await page.getByTestId('setup-start').click()
  await page.getByRole('button', { name: /I will add them later|Next/ }).click()
  await page.getByTestId('setup-energy-next').click()
  await page.getByRole('button', { name: 'Skip for now' }).click()
  await expect(page.getByTestId('setup-finish')).toBeVisible()
  await shot(page, info, 'dash', 'M19', 'setup-finished')

  // empty "No miners yet" (M20): the miner list answers empty and the stream's device updates are held back
  const empty = await context.newPage()
  await empty.addInitScript(() => {
    ;(window as unknown as { __dropDeviceTopic: boolean }).__dropDeviceTopic = true
  })
  await empty.route('**/api/v1/devices', (route) => route.fulfill({ json: [] }))
  await open(empty, 'dash', '/miners')
  await expect(empty.getByText('No miners yet').first()).toBeVisible()
  await shot(empty, info, 'dash', 'M20', 'empty-miners-page')
  await open(empty, 'dash', '/')
  await expect(empty.getByTestId('widget-miners').or(empty.getByText('No miners yet')).first()).toBeVisible()
  await shot(empty, info, 'dash', 'M20', 'empty-miners-widget')

  // getting-started checklist completed (M21): the answers change while the dashboard is open
  const checklist = await context.newPage()
  let finished = false
  const unfinished = [{ id: 'no-node', level: 'tip', title: 'Connect your node', body: 'evidence', action: null, device_id: null }]
  await checklist.route('**/api/v1/insights', (route) => route.fulfill({ json: { insights: finished ? [] : unfinished } }))
  await open(checklist, 'dash', '/')
  await expect(checklist.getByTestId('widget-checklist')).toBeVisible()
  finished = true
  const [view] = (await (await request.get('/api/v1/devices')).json()) as unknown[]
  await inject(checklist, ['device_removed', { id: a.id }], ['device', { id: a.id, view }])
  await expect(popup(checklist, 'M21')).toBeVisible({ timeout: POPUP_WAIT_MS })
  await shot(checklist, info, 'dash', 'M21', 'checklist-complete')

  // notifications switched on (M22) and a test that arrives (M23)
  const notes = await context.newPage()
  const channel = { id: 'evidence', kind: 'ntfy', name: 'My phone', enabled: false, config: {}, has_secret: false, min_severity: 'info', created_at: 1 }
  await notes.route('**/api/v1/notifications/channel-types', (route) => route.fulfill({ json: { channel_types: [] } }))
  await notes.route('**/api/v1/notifications/channels', (route) => route.fulfill({ json: { channels: [channel] } }))
  await notes.route('**/api/v1/notifications/channels/evidence', (route) => route.fulfill({ json: { channel: { ...channel, enabled: true } } }))
  await notes.route('**/api/v1/notifications/channels/evidence/test', (route) => route.fulfill({ json: { ok: true, error: null } }))
  await open(notes, 'dash', '/settings/notifications')
  await notes.getByRole('switch', { name: 'My phone enabled' }).click()
  await expect(popup(notes, 'M22')).toBeVisible({ timeout: POPUP_WAIT_MS })
  await shot(notes, info, 'dash', 'M22', 'notifications-on')
  await clearPopups(notes)
  await notes.getByRole('button', { name: 'Send test' }).click()
  await expect(popup(notes, 'M23')).toBeVisible({ timeout: POPUP_WAIT_MS })
  await shot(notes, info, 'dash', 'M23', 'test-notification')

  // the one joke on the Odds page (M25)
  await open(page, 'dash', '/odds')
  await expect(page.getByTestId('odds-hero')).toBeVisible()
  await shot(page, info, 'dash', 'M25', 'odds-joke')
})

test('logo mark: open frame and blink frame', async ({ page }, info) => {
  test.setTimeout(120_000)
  // Time is frozen once the page has loaded, then the mark is hovered, so the 200 ms blink frame stays on screen for the picture.
  await page.clock.install({ time: new Date('2026-11-16T10:00:00') })
  await page.goto('/setup')
  const mark = page.getByTestId('logo-mark').first()
  await expect(mark).toBeVisible()
  await expect(mark).toHaveAttribute('data-blinking', 'false')
  await page.screenshot({ path: info.outputPath('logo-open.png'), clip: (await mark.boundingBox()) ?? undefined })
  await page.clock.pauseAt(new Date('2026-11-16T10:00:30'))
  await mark.hover()
  await expect(mark).toHaveAttribute('data-blinking', 'true')
  await page.screenshot({ path: info.outputPath('logo-blink.png'), clip: (await mark.boundingBox()) ?? undefined })
})

test('the settings switch, and reduced motion', async ({ page, context, request }, info) => {
  test.setTimeout(120_000)

  // the switch in Settings, on and off (and back on)
  await page.goto('/settings/appearance')
  const toggle = page.getByRole('switch', { name: 'Hashling pop-ups' })
  await expect(toggle).toHaveAttribute('aria-checked', 'true')
  await page.screenshot({ path: info.outputPath('settings-switch-on.png') })
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-checked', 'false')
  await page.screenshot({ path: info.outputPath('settings-switch-off.png') })
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-checked', 'true')

  // reduced motion: a logo that does not blink, and a pop-up that does not hop
  const still = await context.newPage()
  await still.emulateMedia({ reducedMotion: 'reduce' })
  await open(still, 'dash', '/setup')
  const stillMark = still.getByTestId('logo-mark').first()
  await stillMark.hover()
  await expect(stillMark).toHaveAttribute('data-blinking', 'false')
  await still.screenshot({ path: info.outputPath('reduced-motion-logo-hover.png'), clip: (await stillMark.boundingBox()) ?? undefined })
  const [a] = await devices(request)
  await open(still, 'dash', '/')
  await inject(still, eventMessage('new_best_share', 'success', { device_id: a.id }))
  await expect(popup(still, 'M14')).toBeVisible({ timeout: POPUP_WAIT_MS })
  await expect(popup(still, 'M14').locator('img')).not.toHaveClass(/hashling-hop/)
  await shot(still, info, 'dash', 'M14', 'reduced-motion-still-frame')
})

test('evidence-only: forces the existing failure artifact upload; never merge', () => {
  expect(true, 'evidence-only: forces the existing failure artifact upload; never merge').toBe(false)
})
