import { useWindowSize } from '@vueuse/core'
import { computed, type ComputedRef } from 'vue'

// Wall display sizing for the Overview chart and the Miners tiles. Everything is derived from the screen's short side
// ("vmin") so a 4K wall screen gets about three times the type of a 720p one, and a portrait screen is handled alike.
const MIN_CHART_PX = 160 // the overview chart's height before issue #81; it only goes below this when the footer leaves no room
const MIN_FIT_CHART_PX = 80 // the least the overview chart is squeezed to so the rest of the panel fits above the footer
const CHART_PER_PX = 0.16 // chart height as a share of the average of screen width and height
const EDGE_MIN_PX = 16 // outer margin floor; the page uses max(1rem, 2vmin)
const EDGE_VMIN = 0.02
const HEADER_PX = 40 // the header's buttons (2.5rem). The footer is not a constant: it wraps on narrow screens, so its real height is passed in.
const EDGES_VERTICAL = 4 // main padding and section padding, top and bottom
const TILE_GAP_VMIN = 0.015
const TILE_STACK_VMIN = 0.42 // tallest tile (two-line name plus a degraded note) in vmin at scale 1
const MAX_TILE_SCALE = 1.3
const HALF_COLUMNS = 2 // the grid has two tracks per card column so an incomplete last row can be offset by half a card
// The Overview panel's own text, mirrored from KioskPage.vue (sizes in vmin, floors in px). Page line height is the inherited 1.5.
const BODY_LINE_HEIGHT = 1.5
const OVERVIEW_LABEL_VMIN = 0.024 // "Fleet hashrate" and the figure captions
const OVERVIEW_LABEL_MIN_PX = 14
const OVERVIEW_LABEL_LINE_HEIGHT = 1.25 // the "Fleet hashrate" eyebrow
const OVERVIEW_HASH_VMIN = 0.28 // big hashrate number: min(18vw, 28vmin), clamped to 4rem..48rem
const OVERVIEW_HASH_VW = 0.18
const OVERVIEW_HASH_MIN_PX = 64
const OVERVIEW_HASH_MAX_PX = 768
const OVERVIEW_HASH_LINE_HEIGHT = 1.2
const OVERVIEW_VALUE_VMIN = 0.06 // figure values, at least 2.25rem
const OVERVIEW_VALUE_MIN_PX = 36
const OVERVIEW_HASH_GAP_VMIN = 0.015 // margin above the hashrate line
const OVERVIEW_CHART_GAP_VMIN = 0.02 // margin above the chart
const OVERVIEW_FIGURES_GAP_VMIN = 0.03 // margin above the figures
const OVERVIEW_FIGURE_GRID_GAP_VMIN = 0.025 // row gap between figures when they stack two by two (portrait)
const OVERVIEW_CAPTION_GAP_PX = 4 // `mt-1` between a caption and its value
const OVERVIEW_FIGURE_COLUMNS_LANDSCAPE = 4
const OVERVIEW_FIGURE_COLUMNS_PORTRAIT = 2
const OVERVIEW_FIGURE_COUNT = 4

export interface KioskLayout {
  /** Height in px for the Overview history chart. */
  chartHeight: ComputedRef<number>
  /** Height in px left for a panel's main block (the Chart panel's container) once the page chrome and the footer are taken out. */
  panelHeight: ComputedRef<number>
  /** Inline style for the Miners grid: column/row counts that follow the screen shape, its minimum height, and the tile text scale `--k`. */
  tileGrid: ComputedRef<Record<string, string>>
  /** Inline style for the tile at `index`: one card column wide, placed so an incomplete last row is centred. */
  tileCell: (index: number) => Record<string, string>
}

/** Pixels a panel's main block may use: the screen minus the page and section padding, the header and the footer (`footerPx`, as rendered). */
export function freeHeight(width: number, height: number, footerPx: number): number {
  const edge = Math.max(EDGE_MIN_PX, EDGE_VMIN * Math.min(width, height))
  return Math.max(0, height - EDGES_VERTICAL * edge - HEADER_PX - footerPx)
}

/** Pixels of the Overview panel that are not the chart: the labels, the hashrate figure, the four figures and the gaps between them. */
function overviewFixedHeight(width: number, height: number): number {
  const short = Math.min(width, height)
  const label = Math.max(OVERVIEW_LABEL_MIN_PX, OVERVIEW_LABEL_VMIN * short)
  const hash = Math.min(OVERVIEW_HASH_MAX_PX, Math.max(OVERVIEW_HASH_MIN_PX, Math.min(OVERVIEW_HASH_VW * width, OVERVIEW_HASH_VMIN * short)))
  const value = Math.max(OVERVIEW_VALUE_MIN_PX, OVERVIEW_VALUE_VMIN * short)
  const columns = width >= height ? OVERVIEW_FIGURE_COLUMNS_LANDSCAPE : OVERVIEW_FIGURE_COLUMNS_PORTRAIT
  const figureRows = OVERVIEW_FIGURE_COUNT / columns
  const figureRow = (label + value) * BODY_LINE_HEIGHT + OVERVIEW_CAPTION_GAP_PX
  return (
    label * OVERVIEW_LABEL_LINE_HEIGHT +
    OVERVIEW_HASH_GAP_VMIN * short +
    hash * OVERVIEW_HASH_LINE_HEIGHT +
    OVERVIEW_CHART_GAP_VMIN * short +
    OVERVIEW_FIGURES_GAP_VMIN * short +
    figureRows * figureRow +
    (figureRows - 1) * OVERVIEW_FIGURE_GRID_GAP_VMIN * short
  )
}

/** Height in px for the Overview history chart: the usual size for the screen, squeezed only as far as the footer (`footerPx`, as rendered) requires. */
export function overviewChartHeight(width: number, height: number, footerPx: number): number {
  const preferred = Math.max(MIN_CHART_PX, Math.round(((width + height) / 2) * CHART_PER_PX))
  const fits = Math.floor(freeHeight(width, height, footerPx) - overviewFixedHeight(width, height))
  return Math.min(preferred, Math.max(MIN_FIT_CHART_PX, fits))
}

export function tileLayout(
  count: number,
  width: number,
  height: number,
  footerPx: number,
): { cols: number; rows: number; scale: number; gridHeight: number } {
  const n = Math.max(1, count)
  const short = Math.min(width, height)
  const cols = Math.max(1, Math.min(n, Math.round(Math.sqrt((n * width) / height))))
  const rows = Math.ceil(n / cols)
  const gap = TILE_GAP_VMIN * short
  const gridHeight = freeHeight(width, height, footerPx)
  const rowHeight = (gridHeight - (rows - 1) * gap) / rows
  const scale = Math.min(MAX_TILE_SCALE, Math.max(0, rowHeight / (TILE_STACK_VMIN * short)))
  return { cols, rows, scale, gridHeight }
}

/**
 * CSS `grid-column` of the tile at `index` (0-based) among `count` tiles in `cols` card columns.
 * Every card spans HALF_COLUMNS tracks. Tiles in a full row flow normally. When the last row has fewer cards than
 * `cols`, its tiles are placed (cols - cardsInRow) tracks in, so the empty space splits evenly on both sides.
 */
export function tileColumn(index: number, count: number, cols: number): string {
  const inLastRow = count % cols
  const lastRowStart = count - inLastRow
  if (inLastRow === 0 || index < lastRowStart) return `span ${HALF_COLUMNS}`
  const start = cols - inLastRow + 1 + (index - lastRowStart) * HALF_COLUMNS
  return `${start} / span ${HALF_COLUMNS}`
}

/** `footerPx` is the footer's rendered height (border box), so a footer that wraps to more rows shrinks the panel above it. */
export function useKioskLayout(count: () => number, footerPx: () => number): KioskLayout {
  const { width, height } = useWindowSize()
  const chartHeight = computed(() => overviewChartHeight(width.value, height.value, footerPx()))
  const panelHeight = computed(() => Math.floor(freeHeight(width.value, height.value, footerPx())))
  const layout = computed(() => tileLayout(count(), width.value, height.value, footerPx()))
  const tileGrid = computed(() => {
    const { cols, rows, scale, gridHeight } = layout.value
    return {
      '--k': scale.toFixed(3),
      gridTemplateColumns: `repeat(${cols * HALF_COLUMNS}, minmax(0, 1fr))`,
      gridTemplateRows: `repeat(${rows}, minmax(min-content, 1fr))`, // rows share the screen but never squeeze a tile below its text
      gap: `${TILE_GAP_VMIN * 100}vmin`,
      minHeight: `${Math.round(gridHeight)}px`,
    }
  })
  const tileCell = (index: number): Record<string, string> => ({ gridColumn: tileColumn(index, count(), layout.value.cols) })
  return { chartHeight, panelHeight, tileGrid, tileCell }
}
