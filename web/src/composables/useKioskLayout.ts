import { useWindowSize } from '@vueuse/core'
import { computed, type ComputedRef } from 'vue'

// Wall display sizing for the Overview chart and the Miners tiles. Everything is derived from the screen's short side
// ("vmin") so a 4K wall screen gets about three times the type of a 720p one, and a portrait screen is handled alike.
const MIN_CHART_PX = 160 // the overview chart's height before issue #81; never smaller
const CHART_PER_PX = 0.16 // chart height as a share of the average of screen width and height
const EDGE_MIN_PX = 16 // outer margin floor; the page uses max(1rem, 2vmin)
const EDGE_VMIN = 0.02
const CHROME_PX = 48 // header buttons (2.5rem) plus the footer dots (0.5rem)
const EDGES_VERTICAL = 4 // main padding and section padding, top and bottom
const TILE_GAP_VMIN = 0.015
const TILE_STACK_VMIN = 0.42 // tallest tile (two-line name plus a degraded note) in vmin at scale 1
const MAX_TILE_SCALE = 1.3

export interface KioskLayout {
  /** Height in px for the Overview history chart. */
  chartHeight: ComputedRef<number>
  /** Inline style for the Miners grid: column/row counts that follow the screen shape, its minimum height, and the tile text scale `--k`. */
  tileGrid: ComputedRef<Record<string, string>>
}

function tileLayout(count: number, width: number, height: number): { cols: number; rows: number; scale: number; gridHeight: number } {
  const n = Math.max(1, count)
  const short = Math.min(width, height)
  const cols = Math.max(1, Math.min(n, Math.round(Math.sqrt((n * width) / height))))
  const rows = Math.ceil(n / cols)
  const edge = Math.max(EDGE_MIN_PX, EDGE_VMIN * short)
  const gap = TILE_GAP_VMIN * short
  const gridHeight = Math.max(0, height - EDGES_VERTICAL * edge - CHROME_PX)
  const rowHeight = (gridHeight - (rows - 1) * gap) / rows
  const scale = Math.min(MAX_TILE_SCALE, Math.max(0, rowHeight / (TILE_STACK_VMIN * short)))
  return { cols, rows, scale, gridHeight }
}

export function useKioskLayout(count: () => number): KioskLayout {
  const { width, height } = useWindowSize()
  const chartHeight = computed(() => Math.max(MIN_CHART_PX, Math.round(((width.value + height.value) / 2) * CHART_PER_PX)))
  const tileGrid = computed(() => {
    const { cols, rows, scale, gridHeight } = tileLayout(count(), width.value, height.value)
    return {
      '--k': scale.toFixed(3),
      gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
      gridTemplateRows: `repeat(${rows}, minmax(min-content, 1fr))`, // rows share the screen but never squeeze a tile below its text
      gap: `${TILE_GAP_VMIN * 100}vmin`,
      minHeight: `${Math.round(gridHeight)}px`,
    }
  })
  return { chartHeight, tileGrid }
}
