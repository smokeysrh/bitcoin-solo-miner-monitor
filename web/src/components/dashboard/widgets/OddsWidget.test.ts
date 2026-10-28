import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, expect, it, vi } from 'vitest'
import type { HorizonKey, OddsHorizon } from '@/lib/types'
import OddsWidget from './OddsWidget.vue'

const fixture = vi.hoisted(() => ({ available: true, probability: 0.001 }))
vi.mock('@/stores/live', () => ({
  useLive: () => ({ odds: {
    available: fixture.available,
    reason: 'Connect a node', expected_seconds: 1000,
    horizons: {
      ten_minutes: { seconds: 600, probability: fixture.probability, one_in: 1000 },
      day: { probability: 0.1 }, month: { probability: 0.2 }, year: { probability: 0.3 },
      ten_years: { probability: 0.8 },
    },
  } }),
}))
vi.mock('@/composables/useFmt', () => ({
  useFmt: () => ({ formatOdds: (p: number) => p === 0 ? 'Never' : `chance=${p}`,
    formatFraction: (p: number) => `${p}`, formatDuration: (s: number) => `${s}s` }),
}))

beforeEach(() => { fixture.available = true; fixture.probability = 0.001 })

async function render(): Promise<string> {
  const app = createSSRApp(OddsWidget)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: OddsWidget }] })
  app.use(router)
  await router.push('/')
  return renderToString(app)
}

it('exposes the typed 600-second horizon visibly, separately from longer windows', async () => {
  const key: HorizonKey = 'ten_minutes'
  const value: OddsHorizon = { seconds: 600, probability: 0, one_in: null }
  expect(key).toBe('ten_minutes')
  expect(value.seconds).toBe(600)
  const html = await render()
  expect(html).toContain('Next 10 minutes')
  expect(html).toContain('chance=0.001')
  expect(html).toContain('Today')
  expect(html).toContain('This year')
})

it('shows zero probability without making it missing', async () => {
  fixture.probability = 0
  expect(await render()).toContain('0%')
})

it('does not fabricate odds when network difficulty is missing', async () => {
  fixture.available = false
  const html = await render()
  expect(html).toContain('Connect a node')
  expect(html).not.toContain('Next 10 minutes')
})
