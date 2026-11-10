import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

// Issue #80 (and #81 for the chart panel): the wall display chart must be readable from across a room.
// These geometry checks are the recorded visual check. Run against a task-owned --demo --offline server.
// The test changes no settings, so there is nothing to restore.

interface Box {
  left: number
  top: number
  right: number
  bottom: number
}
interface Measured {
  width: number
  height: number
  scrollWidth: number
  legend: Box | null
  chart: Box | null
  summary: Box | null
  items: Box[]
  labels: string[]
  values: string[]
  labelFont: number[]
  valueFont: number[]
}

const TOLERANCE_PX = 1
const MIN_WIDTH_SHARE = 0.9
const MIN_HEIGHT_SHARE = 0.5
const SIZES = [
  { name: '1280x720 (16:9)', width: 1280, height: 720, minLabelFont: 18 },
  { name: '1920x1080 (16:9)', width: 1920, height: 1080, minLabelFont: 28 },
  { name: '3840x2160 (4K)', width: 3840, height: 2160, minLabelFont: 56 },
  { name: '1080x1920 (portrait)', width: 1080, height: 1920, minLabelFont: 28 },
  { name: '1440x900 (16:10)', width: 1440, height: 900, minLabelFont: 20 },
]

const inside = (b: Box, w: number, h: number): boolean =>
  b.left >= -TOLERANCE_PX && b.top >= -TOLERANCE_PX && b.right <= w + TOLERANCE_PX && b.bottom <= h + TOLERANCE_PX
const overlap = (a: Box, b: Box): boolean =>
  a.left < b.right - TOLERANCE_PX && b.left < a.right - TOLERANCE_PX && a.top < b.bottom - TOLERANCE_PX && b.top < a.bottom - TOLERANCE_PX

test.use({ reducedMotion: 'reduce' })

for (const size of SIZES) {
  test(`issue 80: wall display chart is large and labelled at ${size.name}`, async ({ page }) => {
    await page.setViewportSize({ width: size.width, height: size.height })
    await page.goto('/kiosk')
    await expect(page.getByTestId('kiosk')).toBeVisible()
    await page.getByRole('button', { name: 'Show chart', exact: true }).click()
    const legend = page.getByTestId('kiosk-chart-legend')
    await expect(legend).toBeVisible()
    await expect(page.locator('section[aria-label="chart"] [role="img"] canvas').first()).toBeVisible()

    // let the panel transition settle, then measure in one evaluation so the panel cannot rotate away
    await page.evaluate(() => new Promise<void>((done) => requestAnimationFrame(() => requestAnimationFrame(() => done()))))
    const m = await page.evaluate((): Measured => {
      const box = (el: Element | null): Box | null => {
        if (!el) return null
        const r = el.getBoundingClientRect()
        return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
      }
      const all = (sel: string): Element[] => Array.from(document.querySelectorAll(sel))
      return {
        width: window.innerWidth,
        height: window.innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        legend: box(document.querySelector('[data-testid="kiosk-chart-legend"]')),
        chart: box(document.querySelector('section[aria-label="chart"] [role="img"]')),
        summary: box(document.querySelector('section[aria-label="chart"] summary')),
        items: all('[data-testid="kiosk-series-item"]').map((e) => box(e)!),
        labels: all('[data-testid="kiosk-series-label"]').map((e) => e.textContent?.trim() ?? ''),
        values: all('[data-testid="kiosk-series-value"]').map((e) => e.textContent?.trim() ?? ''),
        labelFont: all('[data-testid="kiosk-series-label"]').map((e) => parseFloat(getComputedStyle(e).fontSize)),
        valueFont: all('[data-testid="kiosk-series-value"]').map((e) => parseFloat(getComputedStyle(e).fontSize)),
      }
    })

    expect(m.width).toBe(size.width)
    // no horizontal scrollbar
    expect(m.scrollWidth).toBeLessThanOrEqual(m.width)
    // both series are named with their units and show a current number
    expect(m.labels).toEqual(['Hashrate (TH/s)', 'Power (W)'])
    expect(m.values).toHaveLength(2)
    for (const v of m.values) expect(v).toMatch(/\d/)
    // the panel fits the screen: nothing is clipped
    expect(m.legend).not.toBeNull()
    expect(m.chart).not.toBeNull()
    expect(m.summary).not.toBeNull()
    for (const b of [m.legend!, m.chart!, m.summary!, ...m.items]) expect(inside(b, m.width, m.height)).toBe(true)
    // the chart uses most of the screen
    expect((m.chart!.right - m.chart!.left) / m.width).toBeGreaterThanOrEqual(MIN_WIDTH_SHARE)
    expect((m.chart!.bottom - m.chart!.top) / m.height).toBeGreaterThanOrEqual(MIN_HEIGHT_SHARE)
    // labels do not overlap each other or the chart
    expect(m.items).toHaveLength(2)
    expect(overlap(m.items[0]!, m.items[1]!)).toBe(false)
    expect(overlap(m.legend!, m.chart!)).toBe(false)
    // text is sized for the screen and the current value stands out from its label
    for (const f of m.labelFont) expect(f).toBeGreaterThanOrEqual(size.minLabelFont)
    m.valueFont.forEach((f, i) => expect(f).toBeGreaterThan(m.labelFont[i]!))

    const results = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
    expect(results.violations).toEqual([])
  })
}

test('issue 80: wall display chart text grows with the screen', async ({ page }) => {
  const fonts: number[] = []
  for (const size of [SIZES[0]!, SIZES[1]!, SIZES[2]!]) {
    await page.setViewportSize({ width: size.width, height: size.height })
    await page.goto('/kiosk')
    await page.getByRole('button', { name: 'Show chart', exact: true }).click()
    const label = page.getByTestId('kiosk-series-label').first()
    await expect(label).toBeVisible()
    fonts.push(await label.evaluate((e) => parseFloat(getComputedStyle(e).fontSize)))
  }
  expect(fonts[1]!).toBeGreaterThan(fonts[0]!)
  expect(fonts[2]!).toBeGreaterThan(fonts[1]!)
})
