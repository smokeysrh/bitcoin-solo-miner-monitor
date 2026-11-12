import { expect, test, type Page } from '@playwright/test'

// EVIDENCE ONLY (card #2390): saves screenshots for review and then fails on purpose so the existing CI step uploads
// web/test-results. Never merge this file. Runs against the demo server at BASE, like the other specs.

test.beforeEach(async ({ page, request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', view_miners: 'grid' } } })
  await page.addInitScript(() => localStorage.clear())
})

test.afterEach(async ({ request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark' } } })
})

async function dashboardReady(page: Page): Promise<void> {
  await page.goto('/')
  await expect(page.getByTestId('hero-hashrate')).toContainText(/\d/)
  await expect(page.locator('[data-testid^="miner-tile-"]').first()).toBeVisible()
}

test('evidence: dashboard with the sidebar header (desktop, dark)', async ({ page }, testInfo) => {
  await dashboardReady(page)
  await expect(page.locator('aside img[src="/brand/hashhurdr-lockup-horizontal-dark.svg"]')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('dashboard.png'), fullPage: true })
})

test('evidence: dashboard with the sidebar header (desktop, light theme)', async ({ page, request }, testInfo) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'light' } } })
  await dashboardReady(page)
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await expect(page.locator('aside img[src="/brand/hashhurdr-lockup-horizontal-light.svg"]')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('dashboard-light.png'), fullPage: true })
})

test('evidence: settings about page shows the name and version', async ({ page }, testInfo) => {
  await page.goto('/settings/about')
  await expect(page.getByTestId('version')).toContainText(/\d/)
  await page.screenshot({ path: testInfo.outputPath('settings.png'), fullPage: true })
})

test('evidence: wall display', async ({ page }, testInfo) => {
  await page.goto('/kiosk')
  await expect(page.getByTestId('kiosk')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('kiosk.png'), fullPage: true })
})

test('evidence: dashboard on a phone with the top bar logo @phone', async ({ page }, testInfo) => {
  await dashboardReady(page)
  await page.screenshot({ path: testInfo.outputPath('dashboard-phone.png'), fullPage: true })
})

test('evidence: force the artifact upload', async () => {
  throw new Error('evidence-only: forces the existing failure artifact upload; never merge')
})
