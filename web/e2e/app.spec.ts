import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

/** Fails the test if the page logs an error or any API call fails unexpectedly. */
function watch(page: Page): { errors: string[] } {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => m.type() === 'error' && errors.push(`console: ${m.text()}`))
  page.on('response', (r) => r.status() >= 400 && r.url().includes('/api/') && errors.push(`http ${r.status()} ${r.url()}`))
  return { errors }
}

test.beforeEach(async ({ page, request }) => {
  // every test starts from the same appearance and the default dashboard. Some of it lives on the server
  // (the demo keeps settings in memory), so a leftover "table" layout from an earlier run must not leak in.
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', view_miners: 'grid' } } })
  await page.addInitScript(() => localStorage.clear())
})

test('dashboard shows live fleet data from the demo', async ({ page }) => {
  const w = watch(page)
  await page.goto('/')
  await expect(page.getByTestId('hero-hashrate')).toContainText(/\d/)
  await expect(page.getByTestId('hero-hashrate')).toContainText(/H\/s/)
  await expect(page.locator('[data-testid^="miner-tile-"]')).toHaveCount(5)
  await expect(page.getByTestId('widget-odds')).toBeVisible()
  await expect(page.getByTestId('odds-year')).toContainText(/^1 in /)
  await expect(page.getByTestId('demo-banner')).toBeVisible()
  expect(w.errors).toEqual([])
})

test('the live badge reports a working stream', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('live-badge').first()).toContainText('Live')
})

test('open a miner, switch tabs, charts draw', async ({ page }) => {
  const w = watch(page)
  await page.goto('/miners')
  await page.locator('[data-testid^="miner-tile-"]').first().click()
  await expect(page).toHaveURL(/\/miners\/dev_/)
  await expect(page.getByTestId('detail-hashrate')).toContainText(/\d/)
  await page.getByRole('tab', { name: 'Charts' }).click()
  await expect(page.locator('canvas').first()).toBeVisible()
  await page.getByRole('tab', { name: 'Pools' }).click()
  await expect(page.getByTestId('pool-list')).toBeVisible()
  await page.getByRole('tab', { name: 'Settings' }).click()
  await expect(page.getByTestId('device-name')).not.toHaveValue('')
  await expect(page.getByTestId('model-evidence')).toContainText(/\w+=|boardVersion/) // why the app named this model
  await page.getByRole('tab', { name: 'Raw data' }).click()
  await expect(page.getByText('Raw reply')).toBeVisible()
  expect(w.errors).toEqual([])
})

test('rename a miner and see it everywhere', async ({ page }) => {
  await page.goto('/miners')
  await page.locator('[data-testid^="miner-tile-"]').first().click()
  await page.getByRole('tab', { name: 'Settings' }).click()
  const original = await page.getByTestId('device-name').inputValue()
  await page.getByTestId('device-name').fill('Renamed by test')
  await page.getByTestId('save-device').click()
  await expect(page.getByTestId('device-title')).toHaveText('Renamed by test')
  await page.goto('/miners')
  await expect(page.getByText('Renamed by test').first()).toBeVisible()
  // leave the demo as we found it, so the suite can run again and screenshots stay clean
  await page.locator('[data-testid^="miner-tile-"]', { hasText: 'Renamed by test' }).click()
  await page.getByRole('tab', { name: 'Settings' }).click()
  await page.getByTestId('device-name').fill(original)
  await page.getByTestId('save-device').click()
  await expect(page.getByTestId('device-title')).toHaveText(original)
})

test('restarting a miner asks first, then confirms', async ({ page }) => {
  await page.goto('/miners')
  await page.locator('[data-testid^="miner-tile-"]').first().click()
  await page.getByTestId('restart').click()
  await expect(page.getByRole('dialog')).toContainText('Restart')
  await page.getByRole('button', { name: 'Restart', exact: true }).last().click()
  await expect(page.getByText(/is restarting/)).toBeVisible()
})

test('miners table view sorts and bulk-selects', async ({ page }) => {
  await page.goto('/miners')
  await page.getByRole('radio', { name: 'Table' }).click()
  await expect(page.getByTestId('miner-table')).toBeVisible()
  await page.getByRole('button', { name: /^Hashrate/ }).click()
  await page.getByTestId('select-mode').click()
  await page.getByLabel('Select all miners').check()
  await expect(page.getByTestId('bulk-bar')).toContainText('5 selected')
  await page.getByRole('button', { name: 'Flash' }).click()
  await expect(page.getByRole('dialog')).toContainText('Flash miners')
  await page.keyboard.press('Escape')
})

test('command palette jumps to a page and to a miner', async ({ page }) => {
  await page.goto('/')
  // API bootstrap finishes after page load; wait for the shell that owns the shortcuts.
  await expect(page.getByTestId('open-palette')).toBeVisible()
  await page.keyboard.press('Control+k')
  await expect(page.getByTestId('palette-input')).toBeFocused()
  await page.keyboard.press('/')
  await expect(page.getByTestId('palette-input')).toHaveValue('/') // typing must not trigger the global slash shortcut
  await page.getByTestId('palette-input').fill('odds')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/odds$/)
  await expect(page.getByTestId('palette-input')).toHaveCount(0) // the first palette has finished closing
  await page.keyboard.press('/')
  await expect(page.getByTestId('palette-input')).toBeFocused()
  await page.getByTestId('palette-input').fill('gamma')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/miners\/dev_/)
})

test('theme and accent apply immediately', async ({ page }) => {
  await page.goto('/settings/appearance')
  await page.getByTestId('theme-light').click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.getByTestId('theme-amoled').click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'amoled')
  await page.getByRole('button', { name: 'Emerald' }).click()
  await expect.poll(() => page.evaluate(() => document.documentElement.style.getPropertyValue('--accent-base'))).toBe('#10B981')
  await page.getByTestId('theme-dark').click()
  await page.getByRole('button', { name: 'Bitcoin orange' }).click()
})

test('dashboard can be customised and the layout is remembered', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('widget-fees')).toBeVisible()
  await page.getByTestId('customize').click()
  await page.getByRole('button', { name: 'Hide Fees & price' }).click()
  await page.getByTestId('customize-done').click()
  await expect(page.getByTestId('widget-fees')).toHaveCount(0)
  await page.reload()
  await expect(page.getByTestId('widget-fees')).toHaveCount(0)
  // put it back
  await page.getByTestId('customize').click()
  await page.getByRole('button', { name: 'Reset' }).click()
  await page.getByTestId('customize-done').click()
  await expect(page.getByTestId('widget-fees')).toBeVisible()
})

test('what-if calculator changes the odds', async ({ page }) => {
  await page.goto('/odds')
  const before = await page.getByTestId('odds-hero').innerText()
  await page.getByTestId('whatif-ths').fill('1000')
  await expect.poll(async () => page.getByTestId('odds-hero').innerText()).not.toBe(before)
  await expect(page.getByTestId('odds-horizons')).toBeVisible()
})

test('alert rules list and toggle', async ({ page }) => {
  await page.goto('/alerts?tab=rules')
  const list = page.getByTestId('rule-list')
  await expect(list).toBeVisible()
  const first = list.getByRole('switch').first()
  const was = await first.getAttribute('aria-checked')
  await first.click()
  await expect(first).not.toHaveAttribute('aria-checked', was ?? 'x')
  await first.click()
})

test('demo scenario "find a block" celebrates', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Find a block' }).click()
  await expect(page.getByTestId('celebration')).toBeVisible()
  await expect(page.getByTestId('celebration')).toContainText('You found a block')
})

test('setup wizard walks through to the dashboard', async ({ page }) => {
  await page.goto('/setup')
  await page.getByTestId('setup-start').click()
  await page.getByRole('button', { name: /I will add them later|Next/ }).click()
  await page.getByTestId('setup-price').fill('0.17')
  await page.getByTestId('setup-energy-next').click()
  await page.getByRole('button', { name: 'Skip for now' }).click()
  await page.getByTestId('setup-finish').click()
  await expect(page).toHaveURL(/\/$/)
})

test('agents page offers a copyable prompt and MCP config', async ({ page }) => {
  await page.goto('/agents')
  await expect(page.getByTestId('agent-prompt')).toContainText('/llms.txt')
  await expect(page.getByText('solo-miner-monitor').first()).toBeVisible()
  await expect(page.getByTestId('tool-list')).toContainText('list_miners')
})

test('kiosk wall display rotates and exits', async ({ page }) => {
  await page.goto('/kiosk')
  await expect(page.getByTestId('kiosk')).toBeVisible()
  await page.keyboard.press('ArrowRight')
  await page.keyboard.press('Escape')
  await expect(page).toHaveURL(/\/$/)
})

test('unknown pages explain themselves @phone', async ({ page }) => {
  await page.goto('/definitely-not-a-page')
  await expect(page.getByText('That page does not exist')).toBeVisible()
})

test('phone: kiosk text has sufficient contrast in light theme @phone', async ({ page, request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'light' } } })
  await page.goto('/kiosk')
  await expect(page.getByTestId('kiosk')).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  const results = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
  expect(results.violations).toEqual([])
})

test('phone: bottom navigation works @phone', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: /Miners/ }).last().click()
  await expect(page).toHaveURL(/\/miners$/)
  await page.getByRole('button', { name: 'More', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('Settings')
})
test('phone: the miners table scrolls inside its card, the page does not @phone', async ({ page, request }) => {
  // an sr-only cell escaped the scroller once and widened the whole page by 300px
  await request.patch('/api/v1/settings', { data: { ui: { view_miners: 'table' } } })
  try {
    await page.goto('/miners')
    await expect(page.getByTestId('miner-table')).toBeVisible()
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(over).toBeLessThanOrEqual(2)
  } finally {
    await request.patch('/api/v1/settings', { data: { ui: { view_miners: 'grid' } } })
  }
})
