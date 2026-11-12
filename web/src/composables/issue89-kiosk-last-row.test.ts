import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { tileColumn, tileLayout, useKioskLayout } from '@/composables/useKioskLayout'

// Wall display Miners panel: when the last row has fewer cards than the columns, that row is centred.
// The grid has two tracks per card column and every card spans two. Rather than trusting the arithmetic, these tests
// place the tiles the way CSS grid does (explicit start, or the next free tracks in the row) and measure the gaps.

const screenSize = { width: ref(1920), height: ref(1080) }
vi.mock('@vueuse/core', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@vueuse/core')>()),
  useWindowSize: () => screenSize,
}))

const TRACKS_PER_CARD = 2
const MAX_TILES = 12 // the wall display shows at most 12 miners
const FOOTER_PX = 112 // a measured footer height (about its size at 1920x1080); the column counts do not depend on it
const SCREENS = [
  { name: '1080p landscape', width: 1920, height: 1080 },
  { name: '720p landscape', width: 1280, height: 720 },
  { name: '4K landscape', width: 3840, height: 2160 },
  { name: 'portrait', width: 1080, height: 1920 },
  { name: 'ultrawide', width: 3440, height: 1000 },
  { name: 'square', width: 1000, height: 1000 },
] as const

interface Placed { row: number; first: number; last: number } // 1-based tracks, inclusive

/** Place tiles like CSS grid: `span 2` takes the next free tracks, `S / span 2` starts at track S; a row never wraps backwards. */
function place(count: number, cols: number): { cells: Placed[]; tracks: number } {
  const tracks = cols * TRACKS_PER_CARD
  const cells: Placed[] = []
  let row = 1
  let cursor = 1 // next free track in the current row
  for (let i = 0; i < count; i++) {
    const css = tileColumn(i, count, cols)
    const explicit = /^(\d+) \/ span 2$/.exec(css)
    const start = explicit ? Number(explicit[1]) : cursor
    if (start < cursor || start + TRACKS_PER_CARD - 1 > tracks) {
      row += 1
      cursor = 1
    }
    const first = explicit ? start : cursor
    expect(first + TRACKS_PER_CARD - 1).toBeLessThanOrEqual(tracks)
    cells.push({ row, first, last: first + TRACKS_PER_CARD - 1 })
    cursor = first + TRACKS_PER_CARD
  }
  return { cells, tracks }
}

describe('issue 89: incomplete last row is centred', () => {
  it('leaves full rows exactly as an ordinary grid would, for every column and tile count', () => {
    for (let cols = 1; cols <= 6; cols++) {
      for (let count = cols; count <= MAX_TILES; count++) {
        const { cells } = place(count, cols)
        const fullRowTiles = count - (count % cols)
        for (let i = 0; i < fullRowTiles; i++) {
          expect(tileColumn(i, count, cols), `${count} tiles / ${cols} cols, tile ${i}`).toBe('span 2')
          expect(cells[i]!.row).toBe(Math.floor(i / cols) + 1)
          expect(cells[i]!.first).toBe((i % cols) * TRACKS_PER_CARD + 1)
        }
      }
    }
  })

  it('splits the empty space evenly on both sides of the last row, whatever the column count', () => {
    for (let cols = 2; cols <= 6; cols++) {
      for (let count = cols + 1; count <= MAX_TILES; count++) {
        const inLastRow = count % cols
        if (inLastRow === 0) continue
        const { cells, tracks } = place(count, cols)
        const lastRowNumber = Math.ceil(count / cols)
        const lastRow = cells.filter((c) => c.row === lastRowNumber)
        expect(lastRow, `${count} tiles / ${cols} cols`).toHaveLength(inLastRow)
        const left = lastRow[0]!.first - 1
        const right = tracks - lastRow[lastRow.length - 1]!.last
        expect(left, `${count} tiles / ${cols} cols`).toBeGreaterThan(0) // it really moved
        expect(left).toBe(right)
        for (let i = 1; i < lastRow.length; i++) expect(lastRow[i]!.first).toBe(lastRow[i - 1]!.last + 1) // cards stay side by side
      }
    }
  })

  it('gives the screen-shaped column counts from useKioskLayout a centred last row', () => {
    let incompleteSeen = 0
    for (const screen of SCREENS) {
      screenSize.width.value = screen.width
      screenSize.height.value = screen.height
      for (let count = 1; count <= MAX_TILES; count++) {
        const layout = useKioskLayout(() => count, () => FOOTER_PX)
        const { cols } = tileLayout(count, screen.width, screen.height, FOOTER_PX)
        const style = layout.tileGrid.value
        expect(style.gridTemplateColumns, `${screen.name}, ${count} tiles`).toBe(`repeat(${cols * TRACKS_PER_CARD}, minmax(0, 1fr))`)
        expect(style.gridTemplateRows).toBe(`repeat(${Math.ceil(count / cols)}, minmax(min-content, 1fr))`) // #81 sizing kept
        const { cells, tracks } = place(count, cols)
        for (let i = 0; i < count; i++) expect(layout.tileCell(i)).toEqual({ gridColumn: tileColumn(i, count, cols) })
        if (count % cols !== 0) {
          incompleteSeen++
          const lastRow = cells.filter((c) => c.row === cells[count - 1]!.row)
          expect(lastRow[0]!.first - 1, `${screen.name}, ${count} tiles, ${cols} cols`).toBe(tracks - lastRow[lastRow.length - 1]!.last)
        }
      }
    }
    expect(incompleteSeen).toBeGreaterThan(10) // the loop above really exercised incomplete rows
  })

  beforeEach(() => {
    screenSize.width.value = 1920
    screenSize.height.value = 1080
  })

  it('does not move a single full row or a single column', () => {
    expect(tileColumn(0, 1, 1)).toBe('span 2')
    expect(tileColumn(2, 3, 3)).toBe('span 2')
    expect(tileColumn(5, 6, 1)).toBe('span 2')
  })

  it('offsets the examples from the request: 1 or 2 cards in the last of 3 columns', () => {
    expect([0, 1, 2, 3].map((i) => tileColumn(i, 4, 3))).toEqual(['span 2', 'span 2', 'span 2', '3 / span 2']) // 1 card: one card-width gap each side
    expect([0, 1, 2, 3, 4].map((i) => tileColumn(i, 5, 3))).toEqual(['span 2', 'span 2', 'span 2', '2 / span 2', '4 / span 2']) // 2 cards: half a card each side
  })
})
