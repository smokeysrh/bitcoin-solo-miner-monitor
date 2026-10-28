import { test, expect, type Page } from '@playwright/test'

// No production mutations: require a loopback demo before installing per-test fake transports.
test.use({ browserName: 'firefox', serviceWorkers: 'block', viewport: { width: 1440, height: 1000 } })
test.beforeEach(async ({ page, baseURL, request }) => {
  const base = new URL(baseURL!)
  expect(['127.0.0.1', 'localhost']).toContain(base.hostname)
  const meta = await request.get(`${base.origin}/api/v1/meta`)
  expect((await meta.json()).demo).toBe(true)
  await page.context().route('**/*', async (route) => {
    const req = route.request()
    if (new URL(req.url()).origin !== base.origin || !['GET', 'HEAD'].includes(req.method())) return route.abort()
    return route.continue()
  })
  // Deliberately controlled SSE: exercise the production LiveStream event handlers, never a miner.
  await page.addInitScript(() => {
    class FixtureSource extends EventTarget {
      static all: FixtureSource[] = []
      readyState = 1
      onerror = null
      constructor() { super(); FixtureSource.all.push(this) }
      close() { this.readyState = 2 }
    }
    Object.defineProperty(window, 'EventSource', { value: FixtureSource })
    window.addEventListener('fixture-device', (event) => {
      for (const source of FixtureSource.all) if (source.readyState === 1) source.dispatchEvent(new MessageEvent('device', { data: JSON.stringify((event as CustomEvent).detail) }))
    })
  })
})

async function auth(page: Page, publicRead = false, initialAdmin = true) {
  let admin = initialAdmin
  await page.route('**/api/v1/meta', async (r) => {
    const meta = await (await r.fetch()).json()
    await r.fulfill({ json: { ...meta, auth: { ...meta.auth, mode: 'password', public_read: publicRead } } })
  })
  await page.route('**/api/v1/auth/me', (r) => r.fulfill(admin
    ? { json: { name: 'Fixture admin', scope: 'admin', via: 'session' } }
    : publicRead ? { json: { name: 'public', scope: 'read', via: 'public' } }
      : { status: 401, json: { error: { code: 'auth_required', message: 'Sign in' } } }))
  await page.route('**/api/v1/auth/login', (r) => { admin = true; return r.fulfill({ json: { ok: true } }) })
  await page.route('**/api/v1/auth/logout', (r) => { admin = false; return r.fulfill({ json: { ok: true } }) })
}

async function settingsFixture(page: Page, readOnly = false) {
  const response = await page.request.get('/api/v1/settings')
  const data = await response.json()
  data.ui.theme = 'dark'; data.ui.density = 'comfortable'; data.ui.reduce_motion = false; data.ui.dashboard = null
  const patches: Record<string, Record<string, unknown>>[] = []
  await page.route('**/api/v1/settings', (r) => {
    if (r.request().method() === 'PATCH') {
      const change = r.request().postDataJSON()
      patches.push(change)
      if (readOnly) return r.fulfill({ status: 403, json: { error: { code: 'forbidden', message: 'Read only' } } })
      for (const key of Object.keys(change)) Object.assign(data[key], change[key])
    }
    return r.fulfill({ json: data })
  })
  return { data, patches }
}

test('FE-01 public monitoring retains an accessible sign-in and reauthentication', async ({ page }) => {
  await auth(page, true, false)
  await page.goto('/')
  await expect(page.getByTestId('widget-hero')).toBeVisible()
  await expect(page.getByTestId('add-miner')).toBeHidden()
  await page.goto('/login')
  await expect(page.getByTestId('login-password')).toBeVisible()
  await page.getByTestId('login-password').fill('synthetic-only')
  await page.getByTestId('login-submit').click()
  await expect(page.getByTestId('add-miner')).toBeVisible()
  await page.getByRole('button', { name: 'More options' }).click()
  await page.getByRole('menuitem', { name: 'Sign out' }).click()
  await expect(page.getByTestId('login-password')).toBeVisible()
  await page.reload()
  await expect(page.getByTestId('login-password')).toBeVisible()
  await page.goto('/')
  await page.getByRole('link', { name: 'Sign in', exact: true }).click()
  await expect(page.getByTestId('login-password')).toBeVisible()
  await page.getByRole('button', { name: 'Continue public monitoring' }).click()
  await expect(page.getByTestId('widget-hero')).toBeVisible()
  await expect(page.getByTestId('add-miner')).toBeHidden()
})

test('FE-02 logout unmounts protected content without another navigation', async ({ page }) => {
  await auth(page)
  await page.goto('/')
  await expect(page.getByTestId('widget-hero')).toBeVisible()
  await page.getByRole('button', { name: 'More options' }).click()
  await page.getByRole('menuitem', { name: 'Sign out' }).click()
  await expect(page.getByTestId('login-password')).toBeVisible()
  await expect(page.getByTestId('widget-hero')).toBeHidden()
  await expect(page.getByTestId('add-miner')).toBeHidden()
})

test('FE-02 mid-page 401 invalidates permission affordances and preserves safe next', async ({ page }) => {
  await auth(page)
  await page.goto('/settings/general')
  await page.getByLabel('Name of this setup').fill('private draft')
  await page.route('**/api/v1/settings', (r) => r.fulfill({ status: 401, json: { error: { code: 'auth_required', message: 'Expired' } } }))
  await page.getByRole('radio', { name: '°F', exact: true }).click()
  await expect(page.getByTestId('login-password')).toBeVisible()
  await expect(page.getByLabel('Name of this setup')).toBeHidden()
  await expect(page).toHaveURL(/login\?next=.*settings/)
})

test('FE-03 leaving customization cannot replace the layout with an empty draft', async ({ page }) => {
  const fixture = await settingsFixture(page)
  await page.goto('/')
  await expect(page.getByTestId('widget-hero')).toBeVisible()
  await page.getByTestId('customize').click()
  await page.getByRole('button', { name: 'Hide Fleet hashrate' }).click()
  await page.locator('nav').getByRole('link', { name: 'Miners', exact: true }).first().click()
  await page.locator('nav').getByRole('link', { name: 'Dashboard', exact: true }).first().click()
  await expect(page.getByTestId('customize')).toBeVisible()
  await expect(page.getByTestId('widget-hero')).toBeVisible()
  expect(fixture.patches).toHaveLength(0)
  await page.getByTestId('customize').click()
  await page.getByTestId('customize-done').click()
  await expect.poll(() => fixture.patches.length).toBe(1)
  expect((fixture.patches[0]!.ui!.dashboard as { widgets: unknown[] }).widgets.length).toBeGreaterThan(0)
})

test('FE-04 unrelated saves preserve both dirty section drafts and explicit discard', async ({ page }) => {
  await settingsFixture(page)
  await page.goto('/settings/general')
  const name = page.getByLabel('Name of this setup')
  const polling = page.getByLabel('Online miners', { exact: true })
  await name.fill('UNSAVED NAME')
  await polling.fill('19')
  await page.getByRole('radio', { name: '°F', exact: true }).click()
  await expect(name).toHaveValue('UNSAVED NAME')
  await expect(polling).toHaveValue('19')
  await page.getByRole('button', { name: 'Discard', exact: true }).first().click()
  await expect(name).not.toHaveValue('UNSAVED NAME')
  await expect(polling).toHaveValue('19')
})

test('FE-05 failed observations are unknown, successful empty is healthy', async ({ page }) => {
  let failed = true
  await page.route('**/api/v1/insights', (r) => r.fulfill(failed
    ? { status: 500, json: { error: { code: 'fixture', message: 'Synthetic insights failure' } } }
    : { json: { insights: [] } }))
  await page.goto('/')
  await expect(page.getByText('Could not load observations')).toBeVisible()
  await expect(page.getByText('Nothing to suggest. Your setup looks healthy.')).toBeHidden()
  failed = false
  await page.getByRole('button', { name: 'Retry observations' }).click()
  await expect(page.getByText('Nothing to suggest. Your setup looks healthy.')).toBeVisible()
})

test('FE-06 edited saved channel requires save before a test can send', async ({ page }) => {
  const channel = { id: 'fixture-channel', kind: 'ntfy', name: 'Fixture phone', config: { topic: 'old-topic' }, enabled: true, min_severity: 'info', has_secret: true }
  const sends: string[] = []
  let failSave = true
  await page.route('**/api/v1/notifications/channels', (r) => r.fulfill({ json: { channels: [channel] } }))
  await page.route('**/api/v1/notifications/channels/fixture-channel', (r) => {
    if (failSave) return r.fulfill({ status: 500, json: { error: { code: 'fixture', message: 'Synthetic save failed' } } })
    Object.assign(channel, r.request().postDataJSON()); return r.fulfill({ json: { channel } })
  })
  await page.route('**/api/v1/notifications/**/test', (r) => { sends.push(channel.config.topic); return r.fulfill({ json: { ok: true } }) })
  await page.goto('/settings/notifications')
  await page.getByRole('button', { name: 'Edit Fixture phone' }).click()
  await page.getByRole('button', { name: 'Send a test', exact: true }).click()
  await expect(page.getByTestId('channel-test-result')).toContainText('Delivered')
  expect(sends).toEqual(['old-topic'])
  await page.getByRole('dialog').getByLabel('Topic', { exact: false }).fill('new-topic')
  await expect(page.getByTestId('channel-test-result')).toBeHidden()
  await expect(page.getByRole('button', { name: 'Send a test', exact: true })).toBeDisabled()
  await expect(page.getByText('Save your changes before sending a test.')).toBeVisible()
  expect(sends).toEqual(['old-topic'])
  await page.getByTestId('channel-save').click()
  await expect(page.getByText('Synthetic save failed')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Send a test', exact: true })).toBeDisabled()
  expect(channel.config.topic).toBe('old-topic')
  failSave = false
  await page.getByTestId('channel-save').click()
  await page.getByRole('button', { name: 'Send test', exact: true }).click()
  await expect.poll(() => sends).toEqual(['old-topic', 'new-topic'])
})

test('FE-07 failed new range never presents the old chart as that range', async ({ page }) => {
  await page.goto('/')
  const widget = page.locator('section').filter({ has: page.getByTestId('widget-hashrate-chart') }).last()
  await expect(widget.locator('canvas')).toBeVisible()
  await page.route('**/api/v1/fleet/history?**', (r) => r.fulfill({ status: 500, json: { error: { code: 'fixture', message: 'Synthetic range failure' } } }))
  await widget.getByRole('radio', { name: '1h', exact: true }).click()
  await expect(widget.getByText('Could not load the chart')).toBeVisible()
  await expect(widget.locator('canvas')).toBeHidden()
})

test('FE-08 SSE rename survives saving only local notes', async ({ page }) => {
  const devices = await (await page.request.get('/api/v1/devices')).json()
  const device = { ...devices[0] }
  const patches: unknown[] = []
  await page.route(`**/api/v1/devices/${device.id}`, (r) => {
    if (r.request().method() === 'PATCH') { const change = r.request().postDataJSON(); patches.push(change); Object.assign(device, change) }
    return r.fulfill({ json: device })
  })
  await page.goto(`/miners/${device.id}?tab=settings`)
  await page.getByLabel('Notes', { exact: true }).fill('LOCAL NOTES')
  device.name = 'OTHER SESSION RENAME'
  await page.evaluate((view) => window.dispatchEvent(new CustomEvent('fixture-device', { detail: { id: view.id, view } })), device)
  await expect(page.getByTestId('device-title')).toHaveText('OTHER SESSION RENAME')
  await page.getByTestId('save-device').click()
  await expect.poll(() => patches.length).toBe(1)
  expect(patches).toEqual([{ notes: 'LOCAL NOTES' }])
  expect(device.name).toBe('OTHER SESSION RENAME')
  await expect(page.getByTestId('device-name')).toHaveValue('OTHER SESSION RENAME')
})

test('FE-09 setup retries and retests reuse the created channel', async ({ page }) => {
  await settingsFixture(page)
  const creates: unknown[] = []; const tests: string[] = []
  const updates: unknown[] = []
  await page.route('**/api/v1/notifications/channels/fixture-1', (r) => { updates.push(r.request().postDataJSON()); return r.fulfill({ json: { channel: { id: 'fixture-1' } } }) })
  await page.route('**/api/v1/notifications/channels', (r) => { creates.push(r.request().postDataJSON()); return r.fulfill({ json: { channel: { id: `fixture-${creates.length}` } } }) })
  await page.route('**/api/v1/notifications/channels/*/test', (r) => { tests.push(new URL(r.request().url()).pathname); return r.fulfill({ json: { ok: tests.length !== 1, error: 'Synthetic delivery failure' } }) })
  await page.goto('/setup')
  await page.getByTestId('setup-start').click()
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  await page.getByTestId('setup-energy-next').click()
  await page.getByTestId('setup-topic').fill('fixture-topic')
  await page.getByRole('button', { name: 'Set up and send a test', exact: true }).click()
  await expect(page.getByText('Synthetic delivery failure')).toBeVisible()
  await page.getByRole('button', { name: /Set up and send a test|Send another test/ }).click()
  await expect(page.getByText('Test sent. If it arrived, you are all set.')).toBeVisible()
  await page.getByRole('button', { name: 'Send another test', exact: true }).click()
  await expect.poll(() => tests.length).toBe(3)
  expect(creates).toHaveLength(1)
  expect(new Set(tests).size).toBe(1)
  await page.getByTestId('setup-topic').fill('changed-topic')
  await page.getByRole('button', { name: 'Set up and send a test', exact: true }).click()
  await expect.poll(() => tests.length).toBe(4)
  expect(creates).toHaveLength(1)
  expect(updates).toEqual([{ config: { topic: 'changed-topic' } }])
  expect(new Set(tests).size).toBe(1)
})

test('FE-10 read-only appearance survives reload without changing server preferences', async ({ page }) => {
  await auth(page, true, false)
  const fixture = await settingsFixture(page, true)
  await page.goto('/settings/appearance')
  await page.getByTestId('theme-light').click()
  await page.getByRole('button', { name: 'Cyan', exact: true }).click()
  await page.getByRole('radio', { name: 'Compact', exact: true }).click()
  await page.getByRole('switch', { name: 'Reduce motion' }).click()
  await expect(page.getByTestId('theme-light')).toHaveAttribute('aria-checked', 'true')
  await page.reload()
  await expect(page.getByTestId('theme-light')).toHaveAttribute('aria-checked', 'true')
  await expect(page.getByRole('radio', { name: 'Compact', exact: true })).toHaveAttribute('aria-checked', 'true')
  await expect(page.getByRole('switch', { name: 'Reduce motion' })).toBeChecked()
  await expect(page.getByRole('button', { name: 'Cyan', exact: true })).toHaveAttribute('aria-pressed', 'true')
  expect(fixture.data.ui.theme).toBe('dark')
  expect(fixture.data.ui.density).toBe('comfortable')
  expect(fixture.data.ui.reduce_motion).toBe(false)
  expect(fixture.patches).toEqual([])
})

test('FE-07 periodic history failure labels retained data stale and recovers', async ({ page }) => {
  await page.clock.install()
  await page.goto('/')
  const widget = page.locator('section').filter({ has: page.getByTestId('widget-hashrate-chart') }).last()
  await expect(widget.locator('canvas')).toBeVisible()
  let fail = true
  await page.route('**/api/v1/fleet/history?**', (r) => fail
    ? r.fulfill({ status: 500, json: { error: { code: 'fixture', message: 'Refresh unavailable' } } })
    : r.continue())
  await page.clock.runFor(30_100)
  await expect(widget.getByText(/Chart is stale. Last updated:/)).toBeVisible()
  await expect(widget.locator('canvas')).toBeVisible()
  fail = false
  await page.clock.runFor(30_100)
  await expect(widget.getByText(/Chart is stale/)).toBeHidden()
  await expect(widget.locator('canvas')).toBeVisible()
})

test('FE-08 concurrent edits of the same miner field require explicit discard', async ({ page }) => {
  const devices = await (await page.request.get('/api/v1/devices')).json()
  const device = { ...devices[0] }
  const patches: unknown[] = []
  await page.route(`**/api/v1/devices/${device.id}`, (r) => {
    if (r.request().method() === 'PATCH') { patches.push(r.request().postDataJSON()); Object.assign(device, r.request().postDataJSON()) }
    return r.fulfill({ json: device })
  })
  await page.goto(`/miners/${device.id}?tab=settings`)
  await page.getByTestId('device-name').fill('LOCAL RENAME')
  device.name = 'REMOTE RENAME'
  await page.evaluate((view) => window.dispatchEvent(new CustomEvent('fixture-device', { detail: { id: view.id, view } })), device)
  await expect(page.getByTestId('device-title')).toHaveText('REMOTE RENAME')
  await page.getByTestId('save-device').click()
  await expect(page.getByText('An edited field changed in another session. Discard to load the latest values before editing again.')).toBeVisible()
  expect(patches).toEqual([])
  await page.getByRole('button', { name: 'Discard', exact: true }).click()
  await expect(page.getByTestId('device-name')).toHaveValue('REMOTE RENAME')
  await page.getByTestId('device-name').fill('EXPLICIT NEW RENAME')
  await page.getByTestId('save-device').click()
  await expect.poll(() => patches).toEqual([{ name: 'EXPLICIT NEW RENAME' }])
})
