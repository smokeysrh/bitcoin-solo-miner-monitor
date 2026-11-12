import { expect, test, type Page } from '@playwright/test'

// v1.2.0 (PR #95): the wall display's sticky footer must be inside the screen-fit budget of the panel above it.
// Issue #81 requires that nothing is clipped or overlaps at these screen sizes. The footer (panel buttons, Previous/Next,
// Lock) is taller than the old dots and wraps on narrow screens, so a panel that ignores its real height either scrolls
// the page or ends up underneath the footer. Real browser geometry, controls visible right after choosing the panel.
// Nothing here changes a setting; run against a task-owned --demo --offline server (the shared preflight enforces it).

const SIZES = [
  { label: '1280x720', width: 1280, height: 720 },
  { label: '1920x1080', width: 1920, height: 1080 },
  { label: '3840x2160', width: 3840, height: 2160 },
  { label: 'portrait 1080x1920', width: 1080, height: 1920 },
] as const
// Overview, Miners and Chart are the panels sized from the page's vertical budget; the other two centre content that has no height of its own.
const PANELS = ['overview', 'miners', 'chart'] as const
type PanelName = (typeof PANELS)[number]

const EDGE_PX = 1 // sub-pixel tolerance for edges that touch
const SCROLL_TOLERANCE_PX = 1 // the page may be at most this much taller than the screen

interface Rect { left: number; top: number; right: number; bottom: number }
interface Fit { viewportHeight: number; scrollHeight: number; scrollY: number; footer: Rect; content: Rect }

async function openPanel(page: Page, size: { width: number; height: number }, panel: PanelName): Promise<void> {
  await page.emulateMedia({ reducedMotion: 'reduce' }) // no transition offsets while measuring
  await page.setViewportSize({ width: size.width, height: size.height })
  await page.goto('/kiosk')
  await expect(page.getByTestId('kiosk')).toBeVisible()
  await page.getByRole('button', { name: `Show ${panel}`, exact: true }).click()
  const section = page.locator(`section[aria-label="${panel}"]`)
  await expect(section).toBeVisible()
  await expect(page.locator('section[aria-label]')).toHaveCount(1)
  await expect.poll(() => section.evaluate((el) => el.getAnimations().length)).toBe(0) // panel transition finished
  if (panel === 'miners') await expect(section.getByText(/°[CF]$/).first()).toBeVisible() // tiles carry telemetry
  else await expect(section.locator('[role="img"] canvas').first()).toBeVisible()
  await page.evaluate(async () => {
    await document.fonts.ready
  })
  await page.mouse.move(size.width / 2, size.height / 2) // the controls fade after a few idle seconds; wake them so a slow load cannot hide them
  const footer = page.locator('[data-testid="kiosk"] > footer')
  await expect(footer).toBeVisible()
  await expect(footer).toHaveCSS('opacity', '1') // the controls are showing, not faded out
}

/** The footer and the panel's main block (the overview figures, the miners grid, or the chart container) in one evaluation, so the panel cannot rotate away. */
async function measure(page: Page, panel: PanelName): Promise<Fit> {
  return page.evaluate((panelName) => {
    const rect = (el: Element): Rect => {
      const r = el.getBoundingClientRect()
      return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
    }
    const section = document.querySelector(`section[aria-label="${panelName}"]`)
    if (!section) throw new Error(`no ${panelName} section`)
    const footer = document.querySelector('[data-testid="kiosk"] > footer')
    if (!footer) throw new Error('no wall display footer')
    // overview: the figures row, the last block on the panel; miners: the grid that holds the tiles; chart: the container that gives the chart its height
    const content =
      panelName === 'overview'
        ? section.querySelector(':scope > dl')
        : panelName === 'miners'
          ? section.querySelector('[data-testid^="miner-tile-"]')?.parentElement
          : section.querySelector(':scope > div')
    if (!content) throw new Error(`no ${panelName} content block`)
    return {
      viewportHeight: window.innerHeight,
      scrollHeight: document.documentElement.scrollHeight,
      scrollY: window.scrollY,
      footer: rect(footer),
      content: rect(content),
    }
  }, panel)
}

const overlaps = (a: Rect, b: Rect): boolean => a.left < b.right - EDGE_PX && b.left < a.right - EDGE_PX && a.top < b.bottom - EDGE_PX && b.top < a.bottom - EDGE_PX

for (const panel of PANELS) {
  for (const size of SIZES) {
    test(`v1.2.0 ${panel} panel leaves room for the footer at ${size.label}`, async ({ page }) => {
      await openPanel(page, size, panel)
      const fit = await measure(page, panel)

      expect(fit.scrollY, 'the page has not been scrolled, so box positions are page positions').toBe(0)
      expect(fit.scrollHeight, `the page is no taller than the ${fit.viewportHeight}px screen`).toBeLessThanOrEqual(fit.viewportHeight + SCROLL_TOLERANCE_PX)
      expect(
        overlaps(fit.footer, fit.content),
        `the footer (top ${fit.footer.top.toFixed(1)}, bottom ${fit.footer.bottom.toFixed(1)}) does not cover the ${panel} block (top ${fit.content.top.toFixed(1)}, bottom ${fit.content.bottom.toFixed(1)})`,
      ).toBe(false)
    })
  }
}
