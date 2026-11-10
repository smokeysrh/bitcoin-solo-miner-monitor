import { expect, test, type Locator, type Page } from '@playwright/test'

// Issue 77: wall display panel buttons and lock button. Geometry is the recorded visual check: the kiosk is read from
// across a room, so the controls must be on screen, not overlap, be easy to hit and grow with the screen.
// Runs in the desktop project against a task-owned --demo --offline server; it changes no settings.

interface Wall {
  name: string
  width: number
  height: number
  minFontPx: number
  minTargetPx: number
}
const WALLS: Wall[] = [
  { name: '1280x720', width: 1280, height: 720, minFontPx: 18, minTargetPx: 44 },
  { name: '1920x1080', width: 1920, height: 1080, minFontPx: 26, minTargetPx: 44 },
  { name: '3840x2160', width: 3840, height: 2160, minFontPx: 44, minTargetPx: 64 },
  { name: 'portrait 1080x1920', width: 1080, height: 1920, minFontPx: 18, minTargetPx: 44 },
]
const PANEL_BUTTONS = ['Show overview', 'Show miners', 'Show odds', 'Show network', 'Show chart']
const NAV_BUTTONS = ['Previous panel', 'Next panel']
const LOCK_BUTTON = 'Lock on this panel'

interface Box {
  x: number
  y: number
  width: number
  height: number
}
async function boxOf(locator: Locator): Promise<Box> {
  const box = await locator.boundingBox()
  if (!box) throw new Error('control has no box on screen')
  return box
}
const fontPx = (locator: Locator): Promise<number> => locator.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))
const overlaps = (a: Box, b: Box): boolean => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height

async function openWall(page: Page, wall: Wall): Promise<void> {
  await page.setViewportSize({ width: wall.width, height: wall.height })
  await page.goto('/kiosk')
  await expect(page.getByTestId('kiosk')).toBeVisible()
  await expect(page.getByRole('button', { name: LOCK_BUTTON })).toBeVisible()
}

for (const wall of WALLS) {
  test(`kiosk controls fit and are readable at ${wall.name}`, async ({ page }) => {
    await openWall(page, wall)

    const names = [...PANEL_BUTTONS, ...NAV_BUTTONS, LOCK_BUTTON]
    const controls = names.map((name) => page.getByRole('button', { name, exact: true }))
    const boxes: Box[] = []
    for (const control of controls) boxes.push(await boxOf(control))

    // fully inside the viewport: no clipping, no horizontal scrollbar
    for (const [i, box] of boxes.entries()) {
      expect(box.x, `${names[i]} left edge`).toBeGreaterThanOrEqual(0)
      expect(box.y, `${names[i]} top edge`).toBeGreaterThanOrEqual(0)
      expect(box.x + box.width, `${names[i]} right edge`).toBeLessThanOrEqual(wall.width)
      expect(box.y + box.height, `${names[i]} bottom edge`).toBeLessThanOrEqual(wall.height)
    }
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
    expect(scrollWidth).toBeLessThanOrEqual(wall.width)

    // no two controls overlap
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        expect(overlaps(boxes[i]!, boxes[j]!), `${names[i]} overlaps ${names[j]}`).toBe(false)
      }
    }

    // easy to hit with a mouse, finger or remote
    for (const [i, box] of boxes.entries()) {
      expect(box.height, `${names[i]} height`).toBeGreaterThanOrEqual(wall.minTargetPx)
      expect(box.width, `${names[i]} width`).toBeGreaterThanOrEqual(wall.minTargetPx)
    }

    // big plain labels: every panel and previous/next button is readable from across the room
    const labelled = controls.slice(0, PANEL_BUTTONS.length + NAV_BUTTONS.length)
    for (const [i, control] of labelled.entries()) {
      expect(await fontPx(control), `${names[i]} font size`).toBeGreaterThanOrEqual(wall.minFontPx)
      expect((await control.innerText()).trim().length, `${names[i]} has a visible label`).toBeGreaterThan(0)
    }
  })
}

test('kiosk controls grow with the screen', async ({ page }) => {
  const measured: Record<string, { font: number; height: number }> = {}
  for (const wall of WALLS.slice(0, 3)) {
    await openWall(page, wall)
    const first = page.getByRole('button', { name: 'Show overview', exact: true })
    measured[wall.name] = { font: await fontPx(first), height: (await boxOf(first)).height }
  }
  const [small, medium, large] = ['1280x720', '1920x1080', '3840x2160'].map((n) => measured[n]!)
  expect(medium!.font).toBeGreaterThan(small!.font)
  expect(large!.font).toBeGreaterThan(medium!.font)
  expect(medium!.height).toBeGreaterThan(small!.height)
  expect(large!.height).toBeGreaterThan(medium!.height)
})

test('lock button toggles its pressed state with the keyboard and keeps the chosen panel', async ({ page }) => {
  await openWall(page, WALLS[1]!)
  const lock = page.getByRole('button', { name: LOCK_BUTTON })
  await expect(lock).toHaveAttribute('aria-pressed', 'false')
  await page.getByRole('button', { name: 'Show network', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Show network', exact: true })).toHaveAttribute('aria-current', 'true')
  await lock.focus()
  await page.keyboard.press('Enter')
  await expect(lock).toHaveAttribute('aria-pressed', 'true')
  await page.keyboard.press('Enter')
  await expect(lock).toHaveAttribute('aria-pressed', 'false')
})
