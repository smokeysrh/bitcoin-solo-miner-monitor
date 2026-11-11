import { expect, test, type Page } from '@playwright/test'

// Issue 76: the wall display is a real control in the desktop top bar and in the phone bottom navigation,
// reachable without opening the three-dot menu or the "More" sheet.

const PAGE_ROUTE = '/miners'
const OVERFLOW_TOLERANCE_PX = 2
const DESKTOP_WIDTHS = [1024, 1440]

test.beforeEach(async ({ page, request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', view_miners: 'grid' } } })
  await page.addInitScript(() => localStorage.clear())
})

/** Horizontal overflow of the page and of the top bar itself, in CSS pixels. */
async function overflow(page: Page): Promise<{ page: number; header: number }> {
  return page.evaluate(() => {
    const header = document.querySelector('header')
    return {
      page: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      header: header ? header.scrollWidth - header.clientWidth : 0,
    }
  })
}

for (const width of DESKTOP_WIDTHS) {
  test(`desktop ${width}px: Wall display is visible in the top bar, fits, and opens /kiosk`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(PAGE_ROUTE)
    // API bootstrap finishes after page load; wait for the shell that owns the top bar.
    await expect(page.getByTestId('open-palette')).toBeVisible()

    const wall = page.getByRole('link', { name: 'Wall display', exact: true })
    await expect(wall).toBeVisible() // no menu was opened
    const box = await wall.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x + box!.width).toBeLessThanOrEqual(width)

    const over = await overflow(page)
    expect(over.page).toBeLessThanOrEqual(OVERFLOW_TOLERANCE_PX)
    expect(over.header).toBeLessThanOrEqual(OVERFLOW_TOLERANCE_PX)

    await wall.click()
    await expect(page).toHaveURL(/\/kiosk$/)
    await expect(page.getByTestId('kiosk')).toBeVisible()
  })
}

test('desktop: Wall display shows its text label on a wide screen', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(PAGE_ROUTE)
  await expect(page.getByTestId('open-palette')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Wall display', exact: true }).getByText('Wall display')).toBeVisible()
})

test('desktop: Wall display is reachable and opened with the keyboard', async ({ page }) => {
  await page.goto(PAGE_ROUTE)
  await expect(page.getByTestId('open-palette')).toBeVisible()
  const wall = page.getByRole('link', { name: 'Wall display', exact: true })
  await wall.focus()
  await expect(wall).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/kiosk$/)
})

test('desktop: the three-dot menu still offers Wall display', async ({ page }) => {
  await page.goto(PAGE_ROUTE)
  await page.getByRole('button', { name: 'More options' }).click()
  await expect(page.getByRole('menuitem', { name: 'Wall display' })).toBeVisible()
})

test('phone: Wall display is one tap away in the bottom navigation @phone', async ({ page }) => {
  await page.goto(PAGE_ROUTE)
  const nav = page.getByRole('navigation', { name: 'Main navigation' })
  await expect(nav).toBeVisible()
  const wall = nav.getByRole('link', { name: 'Wall display', exact: true })
  await expect(wall).toBeVisible() // the "More" sheet was not opened

  const viewport = page.viewportSize()
  expect(viewport).not.toBeNull()
  for (const link of await nav.getByRole('link').all()) {
    const box = await link.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport!.width)
  }
  expect((await overflow(page)).page).toBeLessThanOrEqual(OVERFLOW_TOLERANCE_PX)

  await wall.click()
  await expect(page).toHaveURL(/\/kiosk$/)
  await expect(page.getByTestId('kiosk')).toBeVisible()
})
