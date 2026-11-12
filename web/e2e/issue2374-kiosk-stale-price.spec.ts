import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

// Issue 2374 (follow-up to 2366): the wall display says, in words, that the bitcoin price is not updating. The demo's
// price is always fresh, so the real demo overview is changed in flight to mark its price source stale, the same way
// issue98-solo-blocks.spec.ts changes a demo response. Nothing is saved: only the settings the page needs
// (one panel, theme) are set and then restored. Run against a task-owned `--demo --offline` server.

const NOTE = 'kiosk-price-stale'
const NOTE_TEXT = 'Price not updating (last updated 2h ago)'
const SECONDS_PER_HOUR = 3600
const STALE_PRICE_AGE_S = 2 * SECONDS_PER_HOUR + 30 // reads as "2h ago" however long the test takes
const THEMES = ['dark', 'amoled', 'light']

interface OverviewJson {
  network: { field_sources?: Record<string, unknown> }
}

/** Marks the price source stale in the demo overview, leaving every other field as the demo served it. */
async function serveStalePrice(page: Page): Promise<void> {
  await page.route('**/api/v1/overview', async (route) => {
    const response = await route.fetch()
    const json = (await response.json()) as OverviewJson
    const staleSince = Date.now() / 1000 - STALE_PRICE_AGE_S
    json.network.field_sources = { ...json.network.field_sources, prices: { source: 'mempool_space', ts: staleSince, stale: true } }
    await route.fulfill({ response, json })
  })
}

test.describe('issue 2374: wall display stale price note', () => {
  let original: { kiosk: unknown; theme: string } = { kiosk: null, theme: 'dark' }

  test.beforeEach(async ({ page, request }) => {
    const before = await request.get('/api/v1/settings')
    expect(before.ok()).toBeTruthy()
    const ui = ((await before.json()) as { ui: { kiosk: unknown; theme: string } }).ui
    original = { kiosk: ui.kiosk, theme: ui.theme }
    // network panel only, no clock, and a rotation long enough that the panel never changes mid-check
    const set = await request.patch('/api/v1/settings', { data: { ui: { kiosk: { rotate_s: 600, panels: ['network'], show_clock: false } } } })
    expect(set.ok()).toBeTruthy()
    await page.addInitScript(() => localStorage.clear())
    await page.emulateMedia({ reducedMotion: 'reduce' }) // no slide-in while axe reads the colours
  })

  test.afterEach(async ({ request }) => {
    const restore = await request.patch('/api/v1/settings', { data: { ui: original } })
    expect(restore.ok()).toBeTruthy()
  })

  for (const theme of THEMES) {
    test(`a stale price is labelled in words and passes axe in the ${theme} theme`, async ({ page, request }) => {
      const set = await request.patch('/api/v1/settings', { data: { ui: { theme } } })
      expect(set.ok()).toBeTruthy()
      await serveStalePrice(page)
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.goto('/kiosk')
      await expect(page.getByTestId('kiosk')).toBeVisible()
      const panel = page.locator('section[aria-label="network"]')
      await expect(panel).toBeVisible()
      await expect(panel).toHaveCSS('transform', 'none')
      await expect(panel).toHaveCSS('opacity', '1')

      // the old price stays visible, with the note next to it
      await expect(page.getByTestId('kiosk-price-value')).toContainText(/\d/)
      await expect(page.getByTestId(NOTE)).toHaveText(NOTE_TEXT)

      // the note's colour contrast, and the definition-list structure it sits in (it is a second <dd> in the price's group)
      const results = await new AxeBuilder({ page })
        .include('[data-testid="kiosk-network"] dl')
        .withRules(['color-contrast', 'definition-list', 'dlitem'])
        .analyze()
      expect(results.violations).toEqual([])
    })
  }
})
