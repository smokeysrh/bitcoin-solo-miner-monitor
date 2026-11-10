import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext } from '@playwright/test'

// Wall display odds panel (issue 78 headline choice, issue 81 use of the screen). Run against a task-owned
// `--demo --offline` server: the demo keeps settings in memory and every test puts back what it changed.

interface Size {
  width: number
  height: number
}
const SIZES: Size[] = [
  { width: 1280, height: 720 },
  { width: 1920, height: 1080 },
  { width: 3840, height: 2160 },
  { width: 1080, height: 1920 }, // portrait wall display
]

/** One calm, single-panel wall display so nothing rotates away while it is measured. */
const ODDS_ONLY = { rotate_s: 3600, panels: ['odds'], show_clock: false }
const TEN_MINUTES_LABEL = 'Chance of a block in the next 10 minutes'
/** Rounding slack for sub-pixel layout. */
const PX = 1

async function savedKiosk(request: APIRequestContext): Promise<unknown> {
  const response = await request.get('/api/v1/settings')
  expect(response.ok()).toBeTruthy()
  return (await response.json()).ui.kiosk ?? null
}
async function saveKiosk(request: APIRequestContext, kiosk: unknown): Promise<void> {
  const response = await request.patch('/api/v1/settings', { data: { ui: { kiosk } } })
  expect(response.ok()).toBeTruthy()
}

let original: unknown = null
test.beforeEach(async ({ page, request }) => {
  original = await savedKiosk(request)
  await page.emulateMedia({ reducedMotion: 'reduce' })
})
test.afterEach(async ({ request }) => {
  await saveKiosk(request, original)
})

interface Measured {
  name: string
  left: number
  right: number
  top: number
  bottom: number
  fontPx: number
}

test('the chosen horizon is the big number and the setting is saved with the wall display options', async ({ page, request }) => {
  await page.goto('/settings/appearance')
  const control = page.getByLabel('Odds headline on the wall display')
  await expect(control).toHaveValue('year') // nothing saved yet: today's behaviour
  await control.selectOption('day')
  await expect(control).toHaveValue('day')
  await expect.poll(async () => ((await savedKiosk(request)) as { odds_headline?: string } | null)?.odds_headline).toBe('day')

  await page.goto('/kiosk')
  await page.getByRole('button', { name: 'Show odds', exact: true }).click()
  await expect(page.getByTestId('kiosk-odds-headline-label')).toHaveText('Chance of a block today')
})

test('an old saved wall display without the field still shows the yearly headline', async ({ page, request }) => {
  await saveKiosk(request, ODDS_ONLY)
  await page.goto('/kiosk')
  await expect(page.getByTestId('kiosk-odds-headline')).toContainText(/^1 in /)
  await expect(page.getByTestId('kiosk-odds-headline-label')).toHaveText('Chance of a block this year')
})

test('odds headline fits, never overlaps and grows with the screen at every wall display size', async ({ page, request }) => {
  await saveKiosk(request, { ...ODDS_ONLY, odds_headline: 'ten_minutes' })
  const headlineFonts: number[] = []
  const labelFonts: number[] = []

  for (const size of SIZES) {
    await page.setViewportSize(size)
    await page.goto('/kiosk')
    const headline = page.getByTestId('kiosk-odds-headline')
    await expect(headline).toBeVisible({ timeout: 20_000 })
    await expect(page.getByTestId('kiosk-odds-headline-label')).toHaveText(TEN_MINUTES_LABEL)

    const found = await page.evaluate(() => {
      const box = (name: string, el: Element | null): { name: string; left: number; right: number; top: number; bottom: number; fontPx: number } | null => {
        if (!el) return null
        const r = el.getBoundingClientRect()
        return { name, left: r.left, right: r.right, top: r.top, bottom: r.bottom, fontPx: parseFloat(getComputedStyle(el).fontSize) }
      }
      const byId = (id: string): Element | null => document.querySelector(`[data-testid="${id}"]`)
      const items: ({ name: string; left: number; right: number; top: number; bottom: number; fontPx: number } | null)[] = [
        box('eyebrow', byId('kiosk-odds-eyebrow')),
        box('headline', byId('kiosk-odds-headline')),
        box('label', byId('kiosk-odds-headline-label')),
      ]
      document.querySelectorAll('[data-testid="kiosk-odds-others"] dt').forEach((el, i) => items.push(box(`dt${i}`, el)))
      document.querySelectorAll('[data-testid="kiosk-odds-others"] dd').forEach((el, i) => items.push(box(`dd${i}`, el)))
      return { innerWidth: window.innerWidth, innerHeight: window.innerHeight, scrollWidth: document.documentElement.scrollWidth, items }
    })
    const at = `${size.width}x${size.height}`
    const measured = found.items.filter((x): x is Measured => x !== null)
    expect(measured.length, `${at}: eyebrow, headline, label and five time frames (two texts each)`).toBe(13)
    expect(found.innerWidth).toBe(size.width)

    // 1. no horizontal scrollbar, and every changed element is fully inside the screen
    expect(found.scrollWidth, `${at}: horizontal scroll`).toBeLessThanOrEqual(found.innerWidth)
    for (const m of measured) {
      expect(m.left, `${at} ${m.name} left`).toBeGreaterThanOrEqual(-PX)
      expect(m.top, `${at} ${m.name} top`).toBeGreaterThanOrEqual(-PX)
      expect(m.right, `${at} ${m.name} right`).toBeLessThanOrEqual(found.innerWidth + PX)
      expect(m.bottom, `${at} ${m.name} bottom`).toBeLessThanOrEqual(found.innerHeight + PX)
    }

    // 2. no two labels overlap
    for (let a = 0; a < measured.length; a++) {
      for (let b = a + 1; b < measured.length; b++) {
        const p = measured[a]!
        const q = measured[b]!
        const apart = p.right <= q.left + PX || q.right <= p.left + PX || p.bottom <= q.top + PX || q.bottom <= p.top + PX
        expect(apart, `${at}: ${p.name} overlaps ${q.name}`).toBe(true)
      }
    }

    // 3. text is never smaller than before this change and grows with the viewport width
    const font = (name: string): number => measured.find((m) => m.name === name)!.fontPx
    expect(font('headline'), `${at} headline`).toBeGreaterThanOrEqual(Math.max(48, 0.12 * size.width) - 0.5)
    expect(font('label'), `${at} label`).toBeGreaterThanOrEqual(Math.max(24, 0.026 * size.width) - 0.5)
    for (let i = 0; i < 5; i++) {
      expect(font(`dt${i}`), `${at} dt${i}`).toBeGreaterThanOrEqual(Math.max(14, 0.013 * size.width) - 0.5)
      expect(font(`dd${i}`), `${at} dd${i}`).toBeGreaterThanOrEqual(Math.max(24, 0.022 * size.width) - 0.5)
    }
    headlineFonts.push(font('headline'))
    labelFonts.push(font('label'))
  }

  // sizes run 1280, 1920, 3840, 1080 wide: compare in width order
  const byWidth = SIZES.map((s, i) => ({ width: s.width, headline: headlineFonts[i]!, label: labelFonts[i]! })).sort((a, b) => a.width - b.width)
  for (let i = 1; i < byWidth.length; i++) {
    expect(byWidth[i]!.headline, `headline grows from ${byWidth[i - 1]!.width}px to ${byWidth[i]!.width}px wide`).toBeGreaterThan(byWidth[i - 1]!.headline)
    expect(byWidth[i]!.label, `label grows from ${byWidth[i - 1]!.width}px to ${byWidth[i]!.width}px wide`).toBeGreaterThan(byWidth[i - 1]!.label)
  }
})

for (const theme of ['dark', 'light'] as const) {
  test(`odds headline text passes the contrast check in the ${theme} theme`, async ({ page, request }) => {
    await saveKiosk(request, { ...ODDS_ONLY, odds_headline: 'ten_minutes' })
    const before = await request.get('/api/v1/settings')
    const previousTheme = (await before.json()).ui.theme as string
    try {
      expect((await request.patch('/api/v1/settings', { data: { ui: { theme } } })).ok()).toBeTruthy()
      await page.goto('/kiosk')
      await expect(page.getByTestId('kiosk-odds-headline')).toBeVisible({ timeout: 20_000 })
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
      const results = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
      expect(results.violations).toEqual([])
    } finally {
      await request.patch('/api/v1/settings', { data: { ui: { theme: previousTheme } } })
    }
  })
}
