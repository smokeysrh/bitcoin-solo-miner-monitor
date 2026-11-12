import { describe, expect, it } from 'vitest'
import { freeHeight, overviewChartHeight } from '@/composables/useKioskLayout'

// Wall display Overview: the fixed-height budget must use the same orientation as the page's CSS.
// KioskPage.vue stacks the four figures two by two with `grid-cols-2 landscape:grid-cols-4`, and CSS
// `(orientation: landscape)` means width > height, so an exactly square screen is portrait: two rows of figures.
// The budget used `width >= height`, counted one row on a square screen, left the chart too tall and let the
// footer cover the figures (the guarantee of PR #95 / issue #81).

const SQUARE_PX = 1000
const SQUARE_FOOTER_PX = 200 // a footer that has wrapped; large enough that the chart has to be squeezed to fit
const FOOTER_PX = 112 // a measured footer height at 1920x1080
// Everything on the Overview panel except the chart at 1000x1000 with two rows of figures, from the KioskPage.vue classes:
// label 30 + hashrate gap 15 + hashrate 216 + chart gap 20 + figures gap 30 + 2 figure rows of 130 + 1 row gap of 25.
const SQUARE_FIXED_TWO_ROWS_PX = 596
const ROUNDING_PX = 1 // the chart height is floored

describe('issue 2373: Overview budget treats a square screen like the CSS does', () => {
  it('keeps the chart and the Overview text above the footer on an exactly square screen', () => {
    const free = freeHeight(SQUARE_PX, SQUARE_PX, SQUARE_FOOTER_PX)
    const chart = overviewChartHeight(SQUARE_PX, SQUARE_PX, SQUARE_FOOTER_PX)
    expect(free).toBe(680)
    expect(SQUARE_FIXED_TWO_ROWS_PX + chart).toBeLessThanOrEqual(free + ROUNDING_PX)
    expect(chart).toBe(84)
  })

  it('has no jump between a square screen and one a pixel taller, which CSS also lays out in portrait', () => {
    const square = overviewChartHeight(SQUARE_PX, SQUARE_PX, SQUARE_FOOTER_PX)
    const slightlyTall = overviewChartHeight(SQUARE_PX, SQUARE_PX + 1, SQUARE_FOOTER_PX)
    expect(slightlyTall).toBe(85) // one more pixel of height, one more pixel of chart
    expect(Math.abs(slightlyTall - square)).toBeLessThanOrEqual(ROUNDING_PX)
  })

  it('still budgets a single row of figures once the screen is wider than it is tall', () => {
    expect(overviewChartHeight(SQUARE_PX + 1, SQUARE_PX, SQUARE_FOOTER_PX)).toBe(160) // the usual size: one row leaves room
  })

  it('leaves the common landscape and portrait budgets unchanged', () => {
    expect(overviewChartHeight(1920, 1080, FOOTER_PX)).toBe(236)
    expect(overviewChartHeight(1280, 720, FOOTER_PX)).toBe(98)
    expect(overviewChartHeight(1080, 1920, FOOTER_PX)).toBe(240)
  })
})
