import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test'
import { updateCheckText } from '../src/lib/updateCheckText'

// EVIDENCE ONLY (never merge): screenshots of Settings > About for card #2457 (the automatic update check switch), desktop,
// dark and light, against a demo server. Demo mode skips update checks, so the page shows "Update checks are off in this
// mode." and a disabled button there; those shots are the real demo page. A second set replaces only the update status
// answers (GET /system/update and POST /system/update/check) with what a normal install returns, to show the switch ON,
// the switch OFF with its status line, and the button still working while the switch is off. Nothing leaves the machine.
// The last test fails on purpose so that CI keeps and uploads the screenshots.

const THEMES = ['dark', 'light'] as const
type Theme = (typeof THEMES)[number]
const FRAMES_TO_SETTLE = 2
const CHECKED_AT_S = 1_700_000_000
const NORMAL_STATUS = { current: '1.5.0', latest: null, update_available: false, url: null, checked_at: CHECKED_AT_S, error: null }
const NEVER_CHECKED_STATUS = { ...NORMAL_STATUS, checked_at: null }

/** Waits until finished (non-looping) animations are done and two frames have painted. */
async function settle(page: Page): Promise<void> {
  await page.waitForFunction(() =>
    document.getAnimations().every((a) => a.effect?.getComputedTiming().iterations === Infinity || (a.playState !== 'running' && !a.pending)),
  )
  await page.evaluate(
    (frames: number) => new Promise<void>((resolve) => {
      const next = (left: number): void => { if (left === 0) resolve(); else requestAnimationFrame(() => next(left - 1)) }
      next(frames)
    }),
    FRAMES_TO_SETTLE,
  )
}

async function reset(request: APIRequestContext): Promise<void> {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark' }, network: { check_for_updates: true } } })
}

async function openAbout(page: Page, request: APIRequestContext, theme: Theme): Promise<void> {
  await request.patch('/api/v1/settings', { data: { ui: { theme }, network: { check_for_updates: true } } })
  await page.goto('/settings/about')
  await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
  await expect(page.getByTestId('version')).toBeVisible()
  await expect(page.getByRole('switch', { name: updateCheckText.label })).toHaveAttribute('aria-checked', 'true')
  await expect(page.getByText(updateCheckText.note)).toBeVisible()
}

async function shot(page: Page, info: TestInfo, name: string): Promise<void> {
  await page.getByTestId('update-check-setting').scrollIntoViewIfNeeded()
  await settle(page)
  await page.screenshot({ path: info.outputPath(name) })
}

test.afterEach(async ({ request }) => { await reset(request) })

for (const theme of THEMES) {
  test(`demo page, ${theme}: switch on, then off`, async ({ page, request }, info) => {
    await openAbout(page, request, theme)
    await expect(page.getByText('Update checks are off in this mode.')).toBeVisible()
    await shot(page, info, `demo-${theme}-switch-on.png`)

    await page.getByRole('switch', { name: updateCheckText.label }).click()
    await expect(page.getByRole('switch', { name: updateCheckText.label })).toHaveAttribute('aria-checked', 'false')
    await expect.poll(async () => (await (await request.get('/api/v1/settings')).json()).network.check_for_updates).toBe(false)
    await shot(page, info, `demo-${theme}-switch-off.png`)
  })

  test(`normal install (update status answers replaced), ${theme}: on, off with its line, button still works`, async ({ page, request }, info) => {
    await page.route('**/api/v1/system/update', (route) => route.fulfill({ json: route.request().method() === 'GET' ? NORMAL_STATUS : NEVER_CHECKED_STATUS }))
    await openAbout(page, request, theme)
    await expect(page.getByText('You are up to date.')).toBeVisible()
    await shot(page, info, `normal-${theme}-switch-on.png`)

    // from here on the "server" has never checked, as after switching off on a fresh install
    await page.unroute('**/api/v1/system/update')
    await page.route('**/api/v1/system/update', (route) => route.fulfill({ json: NEVER_CHECKED_STATUS }))
    await page.route('**/api/v1/system/update/check', (route) => route.fulfill({ json: NORMAL_STATUS }))
    await page.reload()
    await page.getByRole('switch', { name: updateCheckText.label }).click()
    await expect(page.getByRole('switch', { name: updateCheckText.label })).toHaveAttribute('aria-checked', 'false')
    await expect(page.getByText(updateCheckText.off)).toBeVisible()
    const button = page.getByRole('button', { name: 'Check for updates' })
    await expect(button).toBeEnabled()
    await shot(page, info, `normal-${theme}-switch-off.png`)

    await button.click()
    await expect(page.getByText('You are up to date.')).toBeVisible()
    await expect(page.getByRole('switch', { name: updateCheckText.label })).toHaveAttribute('aria-checked', 'false')
    await shot(page, info, `normal-${theme}-switch-off-after-button.png`)
  })
}

test('evidence-only: forces the existing failure artifact upload; never merge', () => {
  expect(true, 'evidence-only: forces the existing failure artifact upload; never merge').toBe(false)
})
