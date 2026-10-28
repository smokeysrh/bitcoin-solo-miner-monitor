import { expect, test } from '@playwright/test'

// Run against a task-owned --demo --offline server, never a saved installation.
test('Next 10 minutes is visible on dashboard, calculator and kiosk', async ({ page, request }) => {
  const failures: string[] = []
  page.on('pageerror', (e) => failures.push(e.message))
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url())
    if (url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') return route.abort()
    return route.continue()
  })
  const health = await request.get('/api/v1/overview')
  expect(health.ok()).toBeTruthy()
  const overview = await health.json()
  expect(overview.odds.horizons.ten_minutes.seconds).toBe(600)
  await page.goto('/')
  await expect(page.getByTestId('widget-odds').getByText('Next 10 minutes')).toBeVisible()
  await page.goto('/odds')
  await expect(page.getByText('Next 10 minutes', { exact: true })).toBeVisible()
  await expect(page.getByText(/Bitcoin targets 10-minute blocks, but the exact future block time is unknown/).first()).toBeVisible()
  await page.getByTestId('whatif-ths').fill('0')
  await expect(page.getByTestId('odds-horizons').locator('li').filter({ hasText: 'Next 10 minutes' })).toContainText('0%')
  const whatif = await request.get('/api/v1/odds?hashrate_ths=0')
  expect((await whatif.json()).horizons.ten_minutes.probability).toBe(0)
  await page.goto('/kiosk')
  await page.getByRole('button', { name: 'Show odds', exact: true }).click()
  await expect(page.getByText('Next 10 minutes', { exact: true })).toBeVisible()
  expect(failures).toEqual([])
})
