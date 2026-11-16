import { expect, test, type Page } from '@playwright/test'
import { HASHLING_MOMENTS, HASHLING_UI } from '../src/lib/hashlingText'

// Card #2362: Hashling's pop-ups, driven by the demo scenario buttons. Run against a task-owned `--demo --offline` server
// (the shared preflight enforces it). The demo keeps settings in memory, so the test puts the switch back where it found it.
//
// A demo miner needs a few poll intervals to drop out (and one slow offline poll to return), so the waits below are long.
const OFFLINE_WAIT_MS = 120_000
const BACK_WAIT_MS = 120_000
/** Longer than Hashling's coalescing window, so a pop-up that would come back has had time to. */
const QUIET_PERIOD_MS = 7_000

/** Hashling pop-ups for the given moments. Matching by moment keeps the checks steady if the demo also sets a new best share. */
const moments = (page: Page, ...ids: string[]) => page.locator(ids.map((id) => `[data-testid="hashling-popup"][data-moment="${id}"]`).join(', '))
const TROUBLE = ['M01', 'M02', 'M02N', 'M1XN'] as const
const BACK = ['M16', 'M16N', 'M17'] as const

test.beforeEach(async ({ page, request }) => {
  await request.patch('/api/v1/settings', { data: { ui: { theme: 'dark', hashling_popups: true, reduce_motion: false } } })
  // Empty memory at the start of a test, but kept across the reloads inside it (sessionStorage survives a reload).
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('hashling-e2e')) {
      localStorage.clear()
      sessionStorage.setItem('hashling-e2e', '1')
    }
  })
})

test('a miner going offline, coming back and a found block show the matching Hashling, once, and can be dismissed with the keyboard', async ({ page, request }) => {
  test.setTimeout(OFFLINE_WAIT_MS + BACK_WAIT_MS + 120_000)
  await request.post('/api/v1/demo/scenario', { data: { scenario: 'online' } })
  await page.goto('/')
  await expect(page.getByTestId('demo-banner')).toBeVisible()
  await expect(page.getByTestId('live-badge').first()).toContainText('Live')
  // a healthy dashboard has no Hashling on it
  await expect(moments(page, ...TROUBLE, ...BACK)).toHaveCount(0)

  await test.step('a miner goes offline: Hashling on alert, dismissed with Escape', async () => {
    await page.getByRole('button', { name: 'Take a miner offline' }).click()
    const offline = moments(page, 'M02')
    await expect(offline).toBeVisible({ timeout: OFFLINE_WAIT_MS })
    await expect(offline).toContainText(HASHLING_MOMENTS.M02.title ?? '')
    await expect(offline.getByRole('img')).toHaveAttribute('alt', HASHLING_UI.U01a)
    // it never takes the keyboard focus
    await expect(offline.locator(':focus')).toHaveCount(0)
    await page.keyboard.press('Escape')
    await expect(offline).toHaveCount(0)
  })

  await test.step('after a reload it does not come back', async () => {
    await page.reload()
    await expect(page.getByTestId('live-badge').first()).toContainText('Live')
    await page.waitForTimeout(QUIET_PERIOD_MS)
    await expect(moments(page, ...TROUBLE)).toHaveCount(0)
  })

  await test.step('the miner comes back: Hashling with a thumbs-up', async () => {
    await page.getByRole('button', { name: 'Bring it back' }).click()
    const back = moments(page, 'M16', 'M17')
    await expect(back).toBeVisible({ timeout: BACK_WAIT_MS })
    await expect(back.getByRole('img')).toHaveAttribute('alt', HASHLING_UI.U01e)
    await page.keyboard.press('Escape')
    await expect(back).toHaveCount(0)
  })

  await test.step('a found block: the celebration dialog wears the found-block Hashling, and there is no second pop-up', async () => {
    await page.getByRole('button', { name: 'Find a block' }).click()
    const dialog = page.getByTestId('celebration')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('You found a block')
    await expect(dialog).toContainText(HASHLING_MOMENTS.M13.line)
    await expect(dialog.getByRole('img', { name: HASHLING_UI.U01c })).toBeVisible()
    await expect(moments(page, 'M13')).toHaveCount(0)
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  })

  await test.step('after a reload none of it comes back', async () => {
    await page.reload()
    await expect(page.getByTestId('live-badge').first()).toContainText('Live')
    await page.waitForTimeout(QUIET_PERIOD_MS)
    await expect(moments(page, ...TROUBLE, ...BACK, 'M13')).toHaveCount(0)
    await expect(page.getByTestId('celebration')).toBeHidden()
  })
})

test('the Hashling pop-ups switch is in Appearance, on by default, and saves', async ({ page, request }) => {
  await page.goto('/settings/appearance')
  const toggle = page.getByRole('switch', { name: HASHLING_UI.U02 })
  await expect(toggle).toBeVisible()
  await expect(toggle).toHaveAttribute('aria-checked', 'true')
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-checked', 'false')
  await expect.poll(async () => ((await (await request.get('/api/v1/settings')).json()) as { ui: { hashling_popups: boolean } }).ui.hashling_popups).toBe(false)
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-checked', 'true')
  await expect.poll(async () => ((await (await request.get('/api/v1/settings')).json()) as { ui: { hashling_popups: boolean } }).ui.hashling_popups).toBe(true)
})
