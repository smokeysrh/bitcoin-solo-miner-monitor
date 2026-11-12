import { expect, test, type Page } from '@playwright/test'

// EVIDENCE ONLY (issue 98). Not for merge: it saves full-page screenshots of the Solo blocks page from the demo server,
// then fails on purpose so CI's failure-only artifact upload keeps test-results/evidence/*.png.

const PAGE_ROUTE = '/solo-blocks'
const DEMO_BLOCK_COUNT = 20

test.beforeEach(async ({ page, request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', view_miners: 'grid' } } })
  await page.addInitScript(() => localStorage.clear())
})

async function openList(page: Page): Promise<void> {
  await page.goto(PAGE_ROUTE)
  await expect(page.getByTestId('solo-block')).toHaveCount(DEMO_BLOCK_COUNT)
}

test('evidence: Solo blocks on desktop', async ({ page }) => {
  await openList(page)
  await page.screenshot({ path: 'test-results/evidence/98-solo-blocks-desktop.png', fullPage: true })
  expect('evidence-only').toBe('intentional failure')
})

test('evidence: Solo blocks with one block marked as yours (the demo response is changed in flight)', async ({ page }) => {
  await page.route('**/api/v1/blocks/solo', async (route) => {
    const response = await route.fetch()
    const json = await response.json()
    json.blocks[1].yours = true
    await route.fulfill({ response, json })
  })
  await openList(page)
  await expect(page.getByTestId('solo-block').nth(1)).toContainText('Yours')
  await page.screenshot({ path: 'test-results/evidence/98-solo-blocks-desktop-yours.png', fullPage: true })
  expect('evidence-only').toBe('intentional failure')
})

test('evidence: Solo blocks in the phone layout @phone', async ({ page }) => {
  await openList(page)
  await page.screenshot({ path: 'test-results/evidence/98-solo-blocks-phone.png', fullPage: true })
  expect('evidence-only').toBe('intentional failure')
})
