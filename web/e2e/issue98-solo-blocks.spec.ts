import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

// Issue 98: the Solo blocks page lists the latest blocks found by solo pools. The demo serves a fixed synthetic
// list (no outside call), so these tests need no network access.

const PAGE_ROUTE = '/solo-blocks'
const DEMO_BLOCK_COUNT = 20
const SOLO_POOL_NAMES = ['Solo CK', 'Public Pool', 'Braiins Solo', 'FutureBit Apollo Solo', 'SoloPool.com']
const BLOCK_LINK = /^https:\/\/mempool\.space\/block\/[0-9a-f]{64}$/
const OVERFLOW_TOLERANCE_PX = 2

test.beforeEach(async ({ page, request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', view_miners: 'grid' } } })
  await page.addInitScript(() => localStorage.clear())
})

/** Collects page errors and failed API calls so a quietly broken page cannot pass. */
function watch(page: Page): { errors: string[] } {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => m.type() === 'error' && errors.push(`console: ${m.text()}`))
  page.on('response', (r) => r.status() >= 400 && r.url().includes('/api/') && errors.push(`http ${r.status()} ${r.url()}`))
  return { errors }
}

async function heights(page: Page): Promise<number[]> {
  const texts = await page.getByTestId('solo-block-height').allTextContents()
  return texts.map((t) => Number(t.replace(/\D/g, '')))
}

test('desktop: lists the demo blocks newest first with pool, age and a mempool.space link', async ({ page }) => {
  const w = watch(page)
  await page.goto(PAGE_ROUTE)
  await expect(page.getByRole('heading', { name: 'Solo blocks', level: 2 })).toBeVisible()
  const items = page.getByTestId('solo-block')
  await expect(items).toHaveCount(DEMO_BLOCK_COUNT)
  await expect(page.getByRole('list', { name: /solo pools/i })).toBeVisible()

  const order = await heights(page)
  expect(order).toEqual([...order].sort((a, b) => b - a))
  expect(new Set(order).size).toBe(DEMO_BLOCK_COUNT)

  for (const item of await items.all()) {
    await expect(item).toContainText(/ago/)
    await expect(item.getByRole('link')).toHaveAttribute('href', BLOCK_LINK)
  }
  await expect(page.getByTestId('solo-blocks-partial')).toHaveCount(0)
  await expect(page.getByTestId('solo-blocks-page').getByRole('alert')).toHaveCount(0)
  expect(w.errors).toEqual([])
})

test('desktop: every demo block names one of the solo pools', async ({ page }) => {
  await page.goto(PAGE_ROUTE)
  await expect(page.getByTestId('solo-block')).toHaveCount(DEMO_BLOCK_COUNT)
  for (const item of await page.getByTestId('solo-block').all()) {
    const text = await item.innerText()
    expect(SOLO_POOL_NAMES.filter((name) => text.includes(name)), text).toHaveLength(1)
  }
})

test('desktop: the page is in the sidebar and has no colour-contrast problems', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('nav-solo-blocks').click()
  await expect(page).toHaveURL(/\/solo-blocks$/)
  await expect(page.getByTestId('solo-block')).toHaveCount(DEMO_BLOCK_COUNT)
  const results = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
  expect(results.violations).toEqual([])
})

test('desktop: a block that is yours is marked with words, and only that block', async ({ page }) => {
  // The demo has found no block, so the real demo response is changed in flight to flag the second block as yours.
  await page.route('**/api/v1/blocks/solo', async (route) => {
    const response = await route.fetch()
    const json = await response.json()
    json.blocks[1].yours = true
    await route.fulfill({ response, json })
  })
  await page.goto(PAGE_ROUTE)
  const items = page.getByTestId('solo-block')
  await expect(items).toHaveCount(DEMO_BLOCK_COUNT)
  await expect(items.nth(1)).toContainText('Yours')
  await expect(items.nth(1)).toHaveAttribute('data-yours', 'true')
  await expect(page.getByText('Yours', { exact: true })).toHaveCount(1)
})

test('desktop: a failed load is an error with a way to retry, not an empty list', async ({ page }) => {
  await page.route('**/api/v1/blocks/solo', (route) =>
    route.fulfill({ status: 502, json: { error: { code: 'solo_blocks_unavailable', message: 'Could not read solo-pool blocks from https://mempool.space: timed out', status: 502 } } }))
  await page.goto(PAGE_ROUTE)
  await expect(page.getByTestId('solo-blocks-page').getByRole('alert')).toContainText('timed out')
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
  await expect(page.getByTestId('solo-block')).toHaveCount(0)
  await expect(page.getByText('No solo-pool blocks')).toHaveCount(0)
})

test('phone: the list fits the screen and is one tap away in the More sheet @phone', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'More', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Solo blocks' }).click()
  await expect(page).toHaveURL(/\/solo-blocks$/)
  await expect(page.getByTestId('solo-block')).toHaveCount(DEMO_BLOCK_COUNT)

  const viewport = page.viewportSize()
  expect(viewport).not.toBeNull()
  const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(over).toBeLessThanOrEqual(OVERFLOW_TOLERANCE_PX)
  for (const item of await page.getByTestId('solo-block').all()) {
    const box = await item.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport!.width)
  }
})
