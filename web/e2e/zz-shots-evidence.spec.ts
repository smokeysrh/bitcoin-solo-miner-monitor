import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test'
import { writeFileSync } from 'node:fs'

// EVIDENCE ONLY (card #2393): screenshots of the Night Shift retheme for review. Never part of a pull request.
// Runs against the demo server at BASE like the other specs: the `desktop` project runs the tests without @phone,
// the `phone` project runs the @phone one. The last test fails on purpose so the existing CI uploads web/test-results.

const THEMES = [
  { stored: 'dark', name: 'dark' },
  { stored: 'amoled', name: 'black' }, // the app's stored name for the kit's black theme
  { stored: 'light', name: 'light' },
] as const
const WALL = { width: 1920, height: 1080 }
const KIOSK_PANELS = ['overview', 'miners', 'odds', 'network', 'chart'] as const
const LONG_ROTATE_S = 600 // the panel never changes mid-shot

async function setTheme(page: Page, request: APIRequestContext, stored: string): Promise<void> {
  const set = await request.patch('/api/v1/settings', { data: { ui: { theme: stored, view_miners: 'grid' } } })
  expect(set.ok()).toBeTruthy()
  await page.addInitScript(() => localStorage.clear())
  await page.emulateMedia({ reducedMotion: 'reduce' })
}

/** Waits for the brand fonts, then writes the full-page shot into the test's output folder. */
async function shoot(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready
  })
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true })
}

test.afterEach(async ({ request }) => {
  const restore = await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark' } } })
  expect(restore.ok()).toBeTruthy()
})

for (const theme of THEMES) {
  test(`${theme.name}: dashboard on desktop`, async ({ page, request }, testInfo) => {
    await setTheme(page, request, theme.stored)
    await page.goto('/')
    await expect(page.getByTestId('hero-hashrate')).toContainText(/\d/)
    await expect(page.locator('[data-testid^="miner-tile-"]')).toHaveCount(5)
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme.stored)
    await shoot(page, testInfo, `${theme.name}-dashboard`)
    // proof that the bundled kit fonts are what the page actually loaded
    const loaded = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => `${f.family} ${f.weight} ${f.stretch}`))
    writeFileSync(testInfo.outputPath(`${theme.name}-fonts-loaded.json`), JSON.stringify(loaded, null, 2))
  })

  test(`${theme.name}: dashboard on a phone @phone`, async ({ page, request }, testInfo) => {
    await setTheme(page, request, theme.stored)
    await page.goto('/')
    await expect(page.getByTestId('hero-hashrate')).toContainText(/\d/)
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme.stored)
    await shoot(page, testInfo, `${theme.name}-dashboard-phone`)
  })

  test(`${theme.name}: miner detail`, async ({ page, request }, testInfo) => {
    await setTheme(page, request, theme.stored)
    await page.goto('/miners')
    await page.locator('[data-testid^="miner-tile-"]').first().click()
    await expect(page).toHaveURL(/\/miners\/dev_/)
    await expect(page.getByTestId('detail-hashrate')).toContainText(/\d/)
    await shoot(page, testInfo, `${theme.name}-miner`)
  })

  test(`${theme.name}: odds and costs`, async ({ page, request }, testInfo) => {
    await setTheme(page, request, theme.stored)
    await page.goto('/odds')
    await expect(page.getByText('Next 10 minutes', { exact: true })).toBeVisible()
    await shoot(page, testInfo, `${theme.name}-odds`)
  })

  test(`${theme.name}: settings, appearance and customize`, async ({ page, request }, testInfo) => {
    await setTheme(page, request, theme.stored)
    await page.goto('/settings/appearance')
    await expect(page.getByTestId(`theme-${theme.stored}`)).toBeVisible()
    await shoot(page, testInfo, `${theme.name}-settings`)
  })
}

test('black: wall display, every panel', async ({ page, request }, testInfo) => {
  const before = await request.get('/api/v1/settings')
  expect(before.ok()).toBeTruthy()
  const original = ((await before.json()) as { ui: { kiosk: Record<string, unknown> | null } }).ui.kiosk
  try {
    const kiosk = { ...(original ?? { panels: [...KIOSK_PANELS], show_clock: true }), rotate_s: LONG_ROTATE_S }
    const set = await request.patch('/api/v1/settings', { data: { ui: { theme: 'amoled', kiosk } } })
    expect(set.ok()).toBeTruthy()
    await page.addInitScript(() => localStorage.clear())
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.setViewportSize(WALL)
    await page.goto('/kiosk')
    await expect(page.getByTestId('kiosk')).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'amoled')
    for (const panel of KIOSK_PANELS) {
      const button = page.getByRole('button', { name: `Show ${panel}`, exact: true })
      await button.click()
      await expect(button).toHaveAttribute('aria-current', 'true')
      if (panel === 'chart') await expect(page.locator('section[aria-label="chart"] [role="img"] canvas').first()).toBeVisible()
      await shoot(page, testInfo, panel === 'overview' ? 'black-kiosk' : `black-kiosk-${panel}`)
    }
  } finally {
    const restore = await request.patch('/api/v1/settings', { data: { ui: { kiosk: original } } })
    expect(restore.ok()).toBeTruthy()
  }
})

test('evidence-only: forces the existing failure artifact upload; never merge', () => {
  throw new Error('evidence-only: forces the existing failure artifact upload; never merge')
})
