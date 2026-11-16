import { expect, test, type APIRequestContext, type Locator, type Page, type TestInfo } from '@playwright/test'

// EVIDENCE ONLY (card #2456): screenshots of the sidebar version text. Never part of the PR, never merge.
// Files go to web/test-results (the existing failure artifact); the last test fails on purpose so that upload runs.

const THEMES = ['dark', 'amoled', 'light'] as const

const SIDEBAR_EXPANDED_PX = 264
const SIDEBAR_COLLAPSED_PX = 76
const VERSION_TEST_ID = 'sidebar-version'
const START_PAGE = '/miners'

async function currentTheme(request: APIRequestContext): Promise<string> {
  const res = await request.get('/api/v1/settings')
  expect(res.ok()).toBeTruthy()
  const body = (await res.json()) as { ui: { theme: string } }
  return body.ui.theme
}

async function saveTheme(request: APIRequestContext, theme: string): Promise<void> {
  const res = await request.patch('/api/v1/settings', { data: { ui: { theme } } })
  expect(res.ok(), `saving theme ${theme}`).toBeTruthy()
}

async function runningVersion(request: APIRequestContext): Promise<string> {
  const res = await request.get('/api/v1/meta')
  expect(res.ok()).toBeTruthy()
  return ((await res.json()) as { version: string }).version
}

/** Web fonts loaded; the sidebar has reached the width of its state (the grid column animates). */
async function settle(page: Page, sidebar: Locator | null, width: number): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready
  })
  if (sidebar) {
    await expect.poll(async () => Math.round((await sidebar.boundingBox())?.width ?? 0)).toBe(width)
  }
}

async function shot(page: Page, testInfo: TestInfo, name: string, target: Locator | null): Promise<void> {
  const path = testInfo.outputPath(`${name}.png`)
  // 'disabled' also finishes finite transitions; the live badge pulse is infinite and is frozen.
  if (target) await target.screenshot({ path, animations: 'disabled' })
  else await page.screenshot({ path, animations: 'disabled' })
  await testInfo.attach(name, { path, contentType: 'image/png' })
}

for (const theme of THEMES) {
  test(`evidence desktop 1440x900, ${theme}: sidebar expanded and collapsed`, async ({ page, request }, testInfo) => {
    const version = await runningVersion(request)
    const previous = await currentTheme(request)
    try {
      await saveTheme(request, theme)
      await page.setViewportSize({ width: 1440, height: 900 })
      await page.addInitScript(() => localStorage.clear())
      await page.goto(START_PAGE)
      await expect(page.getByTestId('open-palette')).toBeVisible()
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)

      const sidebar = page.getByRole('complementary', { name: 'Main navigation' })
      const versionText = page.getByTestId(VERSION_TEST_ID)
      await expect(versionText).toBeVisible()
      await expect(versionText).toHaveText(`v${version}`)
      await settle(page, sidebar, SIDEBAR_EXPANDED_PX)
      await shot(page, testInfo, `${theme}-expanded-sidebar`, sidebar)
      await shot(page, testInfo, `${theme}-expanded-page`, null)

      await page.getByRole('button', { name: 'Collapse sidebar' }).click()
      await expect(page.getByRole('button', { name: 'Expand sidebar' })).toBeVisible()
      await expect(versionText).toHaveCount(0)
      await settle(page, sidebar, SIDEBAR_COLLAPSED_PX)
      await shot(page, testInfo, `${theme}-collapsed-sidebar`, sidebar)
      await shot(page, testInfo, `${theme}-collapsed-page`, null)
    } finally {
      await saveTheme(request, previous)
    }
  })

  test(`evidence phone 390x844, ${theme}: bottom navigation has no sidebar and no version @phone`, async ({ page, request }, testInfo) => {
    const previous = await currentTheme(request)
    try {
      await saveTheme(request, theme)
      await page.addInitScript(() => localStorage.clear())
      await page.goto(START_PAGE)
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
      await expect(page.locator('nav[aria-label="Main navigation"]:visible')).toBeVisible()
      await expect(page.getByTestId(VERSION_TEST_ID)).toHaveCount(0)
      await settle(page, null, 0)
      await shot(page, testInfo, `${theme}-phone-page`, null)
    } finally {
      await saveTheme(request, previous)
    }
  })
}

test('evidence-only: forces the existing failure artifact upload; never merge', () => {
  throw new Error('evidence-only: forces the existing failure artifact upload; never merge')
})
