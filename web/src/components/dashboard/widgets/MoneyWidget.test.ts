import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'
import { expect, it, vi } from 'vitest'
import MoneyWidget from './MoneyWidget.vue'

// An older server may still send the removed break-even field; the widget must not show it.
vi.mock('@/stores/live', () => ({
  useLive: () => ({ odds: {
    available: true,
    economics: {
      price_per_kwh: 0.12, power_w: 100, cost_note: null,
      cost_per_day: 1, cost_per_month: 30, cost_per_year: 365,
      expected_value_per_year: 180, ev_to_cost_ratio: 0.5, break_even_btc_price: 120000,
    },
  } }),
}))
vi.mock('@/composables/useFmt', () => ({
  useFmt: () => ({ money: (n: number) => `$${n}`, formatPower: (w: number) => `${w} W` }),
}))

async function render(): Promise<string> {
  const app = createSSRApp(MoneyWidget)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: MoneyWidget }] })
  app.use(router)
  await router.push('/')
  return renderToString(app)
}

it('keeps the electricity and expected value rows and shows no break-even row', async () => {
  const html = await render()
  expect(html).toContain('Electricity &amp; value')
  expect(html).toContain('Expected payout / year')
  expect(html).toContain('Payout vs. cost')
  expect(html).not.toMatch(/break-?even/i)
  expect(html).not.toContain('$120000')
})
