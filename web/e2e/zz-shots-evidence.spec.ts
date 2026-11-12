import { expect, test } from '@playwright/test'

// EVIDENCE ONLY, never merge. Saves full-page screenshots of the pages touched by the copy pass, then fails on
// purpose so CI uploads web/test-results. Runs against the task-owned --demo --offline server (process.env.BASE).
// The desktop project runs the untagged tests; the phone project runs the @phone twins.
for (const tag of ['', ' @phone']) {
  test.describe(`evidence screenshots${tag}`, () => {
    test.beforeEach(async ({ page, request }) => {
      await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', view_miners: 'grid' } } })
      await page.addInitScript(() => localStorage.clear())
    })

    test(`odds page${tag}`, async ({ page }, testInfo) => {
      await page.goto('/odds')
      await expect(page.getByTestId('odds-hero')).toBeVisible()
      await expect(page.getByTestId('odds-horizons')).toBeVisible()
      await expect(page.getByText('Payout vs. cost').first()).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath('odds.png'), fullPage: true })
    })

    test(`dashboard with the Electricity & value widget${tag}`, async ({ page }, testInfo) => {
      await page.goto('/')
      await expect(page.getByTestId('hero-hashrate')).toContainText(/\d/)
      await expect(page.getByTestId('widget-odds')).toBeVisible()
      await expect(page.getByTestId('widget-money')).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath('dashboard.png'), fullPage: true })
      // The checklist hides itself once setup is done; only capture it when the demo shows it.
      const checklist = page.getByTestId('widget-checklist')
      if (await checklist.count()) await checklist.screenshot({ path: testInfo.outputPath('checklist.png') })
    })
  })
}

for (const tag of ['', ' @phone']) {
  test(`evidence-only failure${tag}`, () => {
    throw new Error('evidence-only: forces the existing failure artifact upload; never merge')
  })
}
