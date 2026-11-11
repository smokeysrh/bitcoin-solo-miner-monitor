import { describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { DeviceView, Settings } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSettings } from '@/stores/settings'
import KioskPage from '@/pages/KioskPage.vue'

// Issue 89: the Miners panel centres an incomplete last row. The layout maths is in issue89-kiosk-last-row.test.ts;
// this checks the page hands each card its placement. The test window is 1024x768, which gives 3 columns for 5 miners.

const COLS = 3

function settings(): Settings {
  return { ui: { kiosk: { rotate_s: 60, panels: ['miners'], show_clock: false } } } as unknown as Settings
}
const miner = (n: number): DeviceView => ({ id: `m${n}`, name: `Bitaxe ${n}`, status: 'online' }) as unknown as DeviceView

async function open(count: number) {
  setActivePinia(createPinia())
  useSettings().data = settings()
  useLive().devicesById = Object.fromEntries(Array.from({ length: count }, (_, i) => [`m${i + 1}`, miner(i + 1)]))
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/kiosk')
  await router.isReady()
  return mount(KioskPage, { global: { plugins: [router], stubs: { KioskMinerTile: true, LiveBadge: true, HistoryChart: true } } })
}

describe('issue 89: Miners panel placement', () => {
  it('offsets a last row of two by half a card and keeps full rows unplaced', async () => {
    const w = await open(5)
    const tiles = w.findAll('kiosk-miner-tile-stub').map((t) => t.attributes('style') ?? '')
    expect(tiles).toHaveLength(5)
    expect(tiles.map((s) => /grid-column: ([^;]+)/.exec(s)?.[1])).toEqual(['span 2', 'span 2', 'span 2', '2 / span 2', '4 / span 2'])
    expect(w.get('section[aria-label="miners"] > div').attributes('style')).toContain(`repeat(${COLS * 2}, minmax(0, 1fr))`)
  })

  it('offsets a single last card by one full card width', async () => {
    const w = await open(7)
    const styles = w.findAll('kiosk-miner-tile-stub').map((t) => /grid-column: ([^;]+)/.exec(t.attributes('style') ?? '')?.[1])
    expect(styles).toEqual([...Array(6).fill('span 2'), '3 / span 2'])
  })

  it('does not move anything when every row is full', async () => {
    const w = await open(6)
    const styles = w.findAll('kiosk-miner-tile-stub').map((t) => /grid-column: ([^;]+)/.exec(t.attributes('style') ?? '')?.[1])
    expect(styles).toEqual(Array(6).fill('span 2'))
  })
})
