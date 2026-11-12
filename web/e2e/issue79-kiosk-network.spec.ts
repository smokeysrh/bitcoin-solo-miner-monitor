import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Issue 79 (and the "use more of the screen" part of issue 81): the wall display's Bitcoin network panel leads with the
// next halving, then the next difficulty change; block height, difficulty and price are secondary. This is the wall
// display visual check: real geometry and computed type sizes at four screen shapes, against a task-owned
// `--demo --offline` backend (never a saved installation).

interface Shape {
  name: string
  width: number
  height: number
  /** Smallest computed font size (px) allowed for each kind of text at this size. */
  min: { halving: number; epoch: number; secondary: number; mainLabel: number; secondaryLabel: number; estimate: number }
}

// The sizes grow with the screen. The smallest ones are never below what the old panel used (48px values, 11px labels).
const SHAPES: Shape[] = [
  { name: '1280x720', width: 1280, height: 720, min: { halving: 112, epoch: 62, secondary: 48, mainLabel: 20, secondaryLabel: 16, estimate: 18 } },
  { name: '1920x1080', width: 1920, height: 1080, min: { halving: 168, epoch: 94, secondary: 62, mainLabel: 31, secondaryLabel: 23, estimate: 27 } },
  { name: '3840x2160', width: 3840, height: 2160, min: { halving: 335, epoch: 188, secondary: 125, mainLabel: 62, secondaryLabel: 46, estimate: 54 } },
  { name: 'portrait 1080x1920', width: 1080, height: 1920, min: { halving: 200, epoch: 115, secondary: 52, mainLabel: 31, secondaryLabel: 23, estimate: 27 } },
]

const KEYS = ['halving', 'epoch', 'height', 'difficulty', 'price'] as const
const SECONDARY = ['height', 'difficulty', 'price'] as const
const ids = (key: (typeof KEYS)[number]): string[] => [`kiosk-${key}-label`, `kiosk-${key}-value`]

interface Box { id: string; left: number; right: number; top: number; bottom: number; fontPx: number; text: string }

async function measure(page: Page, testIds: string[]): Promise<Box[]> {
  return page.evaluate((list) => list.flatMap((id) => {
    const el = document.querySelector<HTMLElement>(`[data-testid="${id}"]`)
    if (!el) return []
    const r = el.getBoundingClientRect()
    return [{ id, left: r.left, right: r.right, top: r.top, bottom: r.bottom, fontPx: Number.parseFloat(getComputedStyle(el).fontSize), text: el.innerText }]
  }), testIds)
}

const overlaps = (a: Box, b: Box): boolean => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1

/** Opens the wall display and waits until the network panel has finished sliding in, so boxes are measured at rest. */
async function openNetworkPanel(page: Page): Promise<void> {
  await page.goto('/kiosk')
  await expect(page.getByTestId('kiosk')).toBeVisible()
  const panel = page.locator('section[aria-label="network"]')
  await expect(panel).toBeVisible()
  await expect(panel).toHaveCSS('transform', 'none')
  await expect(panel).toHaveCSS('opacity', '1')
}

test.describe('issue 79: wall display network panel', () => {
  let original: { kiosk: unknown; theme: string } = { kiosk: null, theme: 'dark' }

  test.beforeEach(async ({ page, request }) => {
    const before = await request.get('/api/v1/settings')
    expect(before.ok()).toBeTruthy()
    const ui = ((await before.json()) as { ui: { kiosk: unknown; theme: string } }).ui
    original = { kiosk: ui.kiosk, theme: ui.theme }
    // one panel only, no clock, and a rotation long enough that the panel never changes mid-measurement
    const set = await request.patch('/api/v1/settings', { data: { ui: { kiosk: { rotate_s: 600, panels: ['network'], show_clock: false } } } })
    expect(set.ok()).toBeTruthy()
    await page.addInitScript(() => localStorage.clear())
    await page.emulateMedia({ reducedMotion: 'reduce' }) // no slide-in while the boxes are measured
  })

  test.afterEach(async ({ request }) => {
    const restore = await request.patch('/api/v1/settings', { data: { ui: original } })
    expect(restore.ok()).toBeTruthy()
  })

  for (const shape of SHAPES) {
    test(`halving leads, nothing clipped or overlapping at ${shape.name}`, async ({ page }) => {
      await page.setViewportSize({ width: shape.width, height: shape.height })
      await openNetworkPanel(page)
      await expect(page.getByTestId('kiosk-halving-value')).toContainText(/\d/)
      await expect(page.getByTestId('kiosk-epoch-value')).toContainText(/\d/)
      await expect(page.getByTestId('kiosk-halving-estimate')).toContainText('Estimated')

      const texts = KEYS.flatMap(ids).concat(['kiosk-halving-estimate'])
      const boxes = await measure(page, texts)
      expect(boxes.map((b) => b.id).sort()).toEqual([...texts].sort())
      const by = (id: string): Box => boxes.find((b) => b.id === id)!

      // Wall display: plain labels, real numbers (never a zero or a dash standing in for missing data in the demo).
      expect(by('kiosk-halving-label').text).toBe('Next halving')
      expect(by('kiosk-epoch-label').text).toBe('Next difficulty change')
      for (const k of KEYS) expect(by(`kiosk-${k}-value`).text).toMatch(/\d/)

      // Everything that was changed lies fully inside the viewport, and the page has no sideways scroll.
      for (const b of boxes) {
        expect(b.left, `${b.id} left`).toBeGreaterThanOrEqual(0)
        expect(b.top, `${b.id} top`).toBeGreaterThanOrEqual(0)
        expect(b.right, `${b.id} right`).toBeLessThanOrEqual(shape.width)
        expect(b.bottom, `${b.id} bottom`).toBeLessThanOrEqual(shape.height)
      }
      const widths = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, inner: window.innerWidth }))
      expect(widths.scroll).toBeLessThanOrEqual(widths.inner)

      // No two pieces of text overlap.
      for (let i = 0; i < boxes.length; i++) {
        for (let j = i + 1; j < boxes.length; j++) expect(overlaps(boxes[i]!, boxes[j]!), `${boxes[i]!.id} overlaps ${boxes[j]!.id}`).toBe(false)
      }

      // Order from top to bottom: halving, then difficulty change, then the secondary row.
      expect(by('kiosk-halving-value').bottom).toBeLessThanOrEqual(by('kiosk-epoch-label').top)
      for (const k of SECONDARY) expect(by('kiosk-epoch-value').bottom).toBeLessThanOrEqual(by(`kiosk-${k}-label`).top)

      // Type: halving is the largest, the difficulty change is second, the rest are smaller; all meet the stated minimum.
      const halving = by('kiosk-halving-value').fontPx
      const epoch = by('kiosk-epoch-value').fontPx
      expect(halving).toBeGreaterThan(epoch)
      for (const k of SECONDARY) expect(epoch, `${k} value`).toBeGreaterThan(by(`kiosk-${k}-value`).fontPx)
      expect(halving).toBeGreaterThanOrEqual(shape.min.halving)
      expect(epoch).toBeGreaterThanOrEqual(shape.min.epoch)
      for (const k of SECONDARY) expect(by(`kiosk-${k}-value`).fontPx, `${k} value`).toBeGreaterThanOrEqual(shape.min.secondary)
      expect(by('kiosk-halving-label').fontPx).toBeGreaterThanOrEqual(shape.min.mainLabel)
      expect(by('kiosk-epoch-label').fontPx).toBeGreaterThanOrEqual(shape.min.mainLabel)
      for (const k of SECONDARY) expect(by(`kiosk-${k}-label`).fontPx, `${k} label`).toBeGreaterThanOrEqual(shape.min.secondaryLabel)
      expect(by('kiosk-halving-estimate').fontPx).toBeGreaterThanOrEqual(shape.min.estimate)
    })
  }

  test('type grows with the screen and both progress bars keep their names', async ({ page }) => {
    const sizes: number[] = []
    for (const shape of SHAPES.slice(0, 3)) {
      await page.setViewportSize({ width: shape.width, height: shape.height })
      await openNetworkPanel(page)
      await expect(page.getByTestId('kiosk-halving-value')).toContainText(/\d/)
      sizes.push((await measure(page, ['kiosk-halving-value']))[0]!.fontPx)
    }
    expect(sizes[0]!).toBeLessThan(sizes[1]!)
    expect(sizes[1]!).toBeLessThan(sizes[2]!)
    await expect(page.getByRole('progressbar', { name: 'Progress to the next halving' })).toBeVisible()
    await expect(page.getByRole('progressbar', { name: 'Progress to the next adjustment' })).toBeVisible()
  })

  for (const theme of ['dark', 'amoled', 'light']) {
    test(`panel text has 4.5:1 contrast in the ${theme} theme`, async ({ page, request }) => {
      const set = await request.patch('/api/v1/settings', { data: { ui: { theme } } })
      expect(set.ok()).toBeTruthy()
      await page.setViewportSize({ width: 1920, height: 1080 })
      await openNetworkPanel(page)
      await expect(page.getByTestId('kiosk-halving-value')).toContainText(/\d/)
      const results = await new AxeBuilder({ page }).include('[data-testid="kiosk-network"]').withRules(['color-contrast']).analyze()
      expect(results.violations).toEqual([])
    })
  }
})
