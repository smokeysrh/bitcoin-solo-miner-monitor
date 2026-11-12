import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

// Issue #81: the wall display Overview and Miners panels must scale up to fill the screen.
// These are the recorded visual checks: real browser geometry at four screen sizes. Nothing here
// changes a setting or writes to the app; it only reads the demo fleet and measures the page.
// Run against a task-owned --demo --offline server (the shared preflight enforces it).

const SIZES = [
  { label: '1280x720', width: 1280, height: 720 },
  { label: '1920x1080', width: 1920, height: 1080 },
  { label: '3840x2160', width: 3840, height: 2160 },
  { label: 'portrait 1080x1920', width: 1080, height: 1920 },
] as const
type PanelName = 'overview' | 'miners'

// Minimum computed font sizes as a fraction of the short screen side ("vmin"). Today's fixed text
// (14 px labels, 36 px values, 28 px hashrate, 12 px temperature) falls below these from 720p up.
const MIN_LABEL = 0.02
const MIN_OVERVIEW_VALUE = 0.055
const MIN_MINER_NAME = 0.026
const MIN_MINER_STATUS = 0.02
const MIN_MINER_HASHRATE = 0.06
const MIN_MINER_TEMP = 0.03
const MIN_HEADLINE_OF_VMIN = 0.25 // headline hashrate, landscape
const MIN_HEADLINE_OF_WIDTH = 0.15 // headline hashrate, narrow portrait screens
const MIN_GRID_WIDTH_SHARE = 0.9 // the tile grid uses at least this share of the screen width
const MIN_GROWTH_FACTOR = 2 // key text at 4K versus 720p (the screens are 3x apart)
const EDGE_PX = 1 // sub-pixel tolerance for edges that touch
const MAX_DEMO_MINERS_FOR_TWO_ROWS = 6 // the sizes above describe the two-row layout of the small demo fleet

interface Rect { left: number; top: number; right: number; bottom: number }
interface Box extends Rect { text: string; size: number; role: 'dt' | 'dd' | 'other' }
interface Scene { boxes: Box[]; area: Rect; grid: Rect | null; viewport: { width: number; height: number }; scrollWidth: number }

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
  if (panel === 'overview') {
    await expect(section.locator('dd').first()).toContainText(/\/ [1-9]/)
    await expect(section.locator('canvas')).toBeVisible()
  } else {
    await expect(section.getByText(/°[CF]$/).first()).toBeVisible() // tiles carry telemetry
  }
  await page.evaluate(async () => {
    await document.fonts.ready
  })
}

/** Every visible text run in a panel (or in one miner's tile) with its real box and computed size. */
async function scene(page: Page, panel: PanelName, miner: string | null): Promise<Scene> {
  return page.evaluate(([panelName, minerName]) => {
    const section = document.querySelector(`section[aria-label="${panelName}"]`)
    if (!section) throw new Error(`no ${panelName} section`)
    let root: Element = section
    let gridEl: Element | null = null
    if (minerName !== null) {
      const label = [...section.querySelectorAll('*')].find((el) => el.children.length === 0 && el.textContent?.trim() === minerName)
      if (!label) throw new Error(`no miner named ${minerName} on screen`)
      const tile = label.closest('[data-testid^="miner-tile-"]')
      if (!tile?.parentElement) throw new Error(`miner ${minerName} is not inside a tile in a grid`)
      root = tile
      gridEl = tile.parentElement
    }
    const rect = (r: DOMRect) => ({ left: r.left, top: r.top, right: r.right, bottom: r.bottom })
    const boxes: Box[] = []
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent?.trim() ?? ''
      const el = node.parentElement
      if (!text || !el) continue
      const style = getComputedStyle(el)
      if (style.display === 'none' || style.visibility === 'hidden') continue
      const range = document.createRange()
      range.selectNodeContents(node)
      const r = range.getBoundingClientRect()
      const host = el.getBoundingClientRect()
      if (r.width <= 2 || r.height <= 2 || host.width <= 2 || host.height <= 2) continue // visually hidden screen-reader text
      boxes.push({ ...rect(r), text, size: parseFloat(style.fontSize), role: el.closest('dd') ? 'dd' : el.closest('dt') ? 'dt' : 'other' })
    }
    return {
      boxes,
      area: rect(root.getBoundingClientRect()),
      grid: gridEl ? rect(gridEl.getBoundingClientRect()) : null,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      scrollWidth: document.documentElement.scrollWidth,
    }
  }, [panel, miner] as const)
}

function overlaps(a: Rect, b: Rect): boolean {
  return a.left < b.right - EDGE_PX && b.left < a.right - EDGE_PX && a.top < b.bottom - EDGE_PX && b.top < a.bottom - EDGE_PX
}

/** Layout problems as readable strings, so a failure says what was clipped or overlapping. */
function layoutProblems(s: Scene, container: Rect, containerName: string): string[] {
  const problems: string[] = []
  if (s.scrollWidth > s.viewport.width) problems.push(`horizontal scrollbar: scrollWidth ${s.scrollWidth} > ${s.viewport.width}`)
  const screen: Rect = { left: 0, top: 0, right: s.viewport.width, bottom: s.viewport.height }
  for (const b of s.boxes) {
    for (const [name, outer] of [['the screen', screen], [containerName, container]] as const) {
      if (b.left < outer.left - EDGE_PX || b.top < outer.top - EDGE_PX || b.right > outer.right + EDGE_PX || b.bottom > outer.bottom + EDGE_PX) {
        problems.push(`"${b.text}" sticks out of ${name}`)
      }
    }
  }
  s.boxes.forEach((a, i) => s.boxes.slice(i + 1).forEach((b) => overlaps(a, b) && problems.push(`"${a.text}" overlaps "${b.text}"`)))
  return problems
}

const vmin = (s: Scene): number => Math.min(s.viewport.width, s.viewport.height)
const biggest = (boxes: Box[]): number => Math.max(0, ...boxes.map((b) => b.size))
const find = (boxes: Box[], pattern: RegExp): Box[] => boxes.filter((b) => pattern.test(b.text))

for (const size of SIZES) {
  test(`issue81 overview fills the ${size.label} screen without clipping or overlap`, async ({ page }) => {
    await openPanel(page, size, 'overview')
    const s = await scene(page, 'overview', null)
    const unit = vmin(s)

    expect(layoutProblems(s, { left: 0, top: 0, right: s.viewport.width, bottom: s.viewport.height }, 'the screen')).toEqual([])

    for (const label of ['Fleet hashrate', 'Miners online', 'Power', 'Efficiency', 'Hottest chip']) {
      expect(find(s.boxes, new RegExp(`^${label}$`, 'i')), `label "${label}" is on screen`).toHaveLength(1)
    }
    const tooSmall = s.boxes.filter((b) => b.size < MIN_LABEL * unit).map((b) => `"${b.text}" ${b.size.toFixed(1)}px`)
    expect(tooSmall, `all overview text is at least ${(MIN_LABEL * unit).toFixed(1)}px`).toEqual([])
    expect(biggest(s.boxes.filter((b) => b.role === 'dd')), 'summary values').toBeGreaterThanOrEqual(MIN_OVERVIEW_VALUE * unit)
    expect(biggest(s.boxes), 'headline hashrate').toBeGreaterThanOrEqual(Math.min(MIN_HEADLINE_OF_VMIN * unit, MIN_HEADLINE_OF_WIDTH * s.viewport.width))
  })

  test(`issue81 miners tiles fill the ${size.label} screen without clipping or overlap`, async ({ page, request }) => {
    const devices = (await (await request.get('/api/v1/devices')).json()) as { name: string }[]
    const names = devices.map((d) => d.name).slice(0, 12)
    expect(names.length).toBeGreaterThan(0)
    expect(names.length, 'the sizes below describe the two-row demo layout').toBeLessThanOrEqual(MAX_DEMO_MINERS_FOR_TWO_ROWS)
    await openPanel(page, size, 'miners')
    const section = page.locator('section[aria-label="miners"]')
    for (const name of names) await expect(section.getByText(name, { exact: true })).toBeVisible()

    const whole = await scene(page, 'miners', null)
    const unit = vmin(whole)
    expect(whole.scrollWidth, 'no horizontal scrollbar').toBeLessThanOrEqual(whole.viewport.width)

    const tiles: Rect[] = []
    for (const name of names) {
      const s = await scene(page, 'miners', name)
      tiles.push(s.area)
      expect(s.grid, 'tiles sit in a grid').not.toBeNull()
      expect(s.grid!.right - s.grid!.left, `${name}: tile grid uses the screen width`).toBeGreaterThanOrEqual(MIN_GRID_WIDTH_SHARE * s.viewport.width)
      expect(layoutProblems(s, s.area, `the ${name} tile`), `${name}: nothing clipped or overlapping`).toEqual([])
      expect(s.boxes.filter((b) => b.text === name), `${name}: name shown`).toHaveLength(1)

      const nameBox = s.boxes.find((b) => b.text === name)!
      expect(nameBox.size, `${name}: name size`).toBeGreaterThanOrEqual(MIN_MINER_NAME * unit)
      const status = find(s.boxes, /^(online|degraded|offline|paused|unknown|disabled)$/i)
      expect(status, `${name}: status is written as a word, not only a coloured dot`).toHaveLength(1)
      expect(status[0]!.size, `${name}: status size`).toBeGreaterThanOrEqual(MIN_MINER_STATUS * unit)
      if (/^(online|degraded)$/i.test(status[0]!.text)) {
        expect(find(s.boxes, /H\/s$/), `${name}: hashrate unit shown`).toHaveLength(1)
        expect(biggest(find(s.boxes, /^\d[\d.,]*$/)), `${name}: hashrate size`).toBeGreaterThanOrEqual(MIN_MINER_HASHRATE * unit)
        const temp = find(s.boxes, /°[CF]/)
        expect(temp, `${name}: temperature shown`).not.toHaveLength(0)
        expect(biggest(temp), `${name}: temperature size`).toBeGreaterThanOrEqual(MIN_MINER_TEMP * unit)
      }
    }
    tiles.forEach((a, i) => tiles.slice(i + 1).forEach((b) => expect(overlaps(a, b), 'tiles do not overlap each other').toBe(false)))
  })
}

test('issue81 key wall display text grows with the screen', async ({ page, request }) => {
  const devices = (await (await request.get('/api/v1/devices')).json()) as { name: string }[]
  const first = devices[0]!.name
  const measure = async (width: number, height: number) => {
    await openPanel(page, { width, height }, 'overview')
    const overviewValue = biggest((await scene(page, 'overview', null)).boxes.filter((b) => b.role === 'dd'))
    await openPanel(page, { width, height }, 'miners')
    await expect(page.locator('section[aria-label="miners"]').getByText(first, { exact: true })).toBeVisible()
    const tileText = biggest((await scene(page, 'miners', first)).boxes)
    return { overviewValue, tileText }
  }
  const small = await measure(1280, 720)
  const large = await measure(3840, 2160)
  expect(large.overviewValue / small.overviewValue, 'overview summary values').toBeGreaterThanOrEqual(MIN_GROWTH_FACTOR)
  expect(large.tileText / small.tileText, 'miner tile hashrate').toBeGreaterThanOrEqual(MIN_GROWTH_FACTOR)
})

test('issue81 overview and miners panels keep passing the colour contrast audit', async ({ page }) => {
  for (const panel of ['overview', 'miners'] as const) {
    await openPanel(page, { width: 1920, height: 1080 }, panel)
    const results = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
    expect(results.violations, `${panel} contrast`).toEqual([])
  }
})

test('issue81 miner cards have an orange fade on the right and an orange hashrate', async ({ page }) => {
  await openPanel(page, { width: 1920, height: 1080 }, 'miners')
  const tile = page.locator('section[aria-label="miners"] [data-testid^="miner-tile-"]').first()
  const look = await tile.evaluate((el) => {
    const fade = getComputedStyle(el, '::before')
    const value = el.querySelector('.kt-hash-value')
    const probe = document.createElement('span')
    probe.className = 'text-accent-text'
    document.body.appendChild(probe)
    const accentText = getComputedStyle(probe).color
    probe.remove()
    return { fadeImage: fade.backgroundImage, valueColor: value ? getComputedStyle(value).color : null, accentText }
  })
  expect(look.fadeImage).toContain('linear-gradient')
  expect(look.valueColor).toBe(look.accentText)
})
