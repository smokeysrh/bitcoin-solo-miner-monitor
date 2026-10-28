// Takes the README screenshots from a running DEMO server (simulated fleet, so no real addresses or hardware appear).
//   bsmm serve --demo --offline --port 8421; BASE=http://localhost:8421 npm run shots
// For a Vite proxy, set BSMM_DEV_API=http://127.0.0.1:8421 and BASE to the Vite origin.
import { mkdirSync, statSync } from 'node:fs'
import { chromium, firefox } from 'playwright'
import { requireDemo } from './demo-preflight.mjs'

if (process.argv.includes('--list')) {
  console.log('dashboard\nminer\nodds\nminers-table\ndashboard-light\nphone')
  process.exit(0)
}

const BASE = process.env.BASE ?? 'http://localhost:6001'
const OUT = process.env.OUT ?? 'test-results/screenshots'
await requireDemo(BASE)
mkdirSync(OUT, { recursive: true })

const browserType = process.env.BROWSER === 'firefox' ? firefox : chromium
const browser = await browserType.launch({ executablePath: process.env.CHROME || undefined, args: ['--no-sandbox'] })

async function shot(name, route, { width = 1440, height = 900, theme = 'dark', full = false, wait = 3500, actions } = {}) {
  await requireDemo(BASE)
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2 })
  await ctx.addInitScript((t) => localStorage.setItem('bsmm.theme', t), theme)
  const page = await ctx.newPage()
  // the theme is stored on the server too, so set it for this run only through the page's own setting
  await page.goto(BASE + route, { waitUntil: 'networkidle' })
  await page.evaluate(async (t) => {
    await fetch('/api/v1/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ui: { theme: t } }) })
  }, theme)
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(wait)
  if (actions) await actions(page)
  await requireDemo(BASE)
  // hide the demo banner so the pictures show the product, not the simulator controls
  await page.addStyleTag({ content: '[data-testid=demo-banner]{display:none!important}' })
  const file = `${OUT}/${name}.png`
  await page.screenshot({ path: file, fullPage: full })
  console.log(file, Math.round(statSync(file).size / 1024) + ' kB')
  await ctx.close()
}

try {
const devices = await (await fetch(BASE + '/api/v1/devices')).json()
const first = devices.find((d) => d.name.includes('NerdQAxe')) ?? devices[0]

await shot('dashboard', '/')
await shot('miner', `/miners/${first.id}`)
await shot('odds', '/odds')
await shot('miners-table', '/miners', { actions: async (p) => p.getByRole('radio', { name: 'Table' }).click() })
await shot('dashboard-light', '/', { theme: 'light' })
await shot('phone', '/', { width: 390, height: 844 })
await shot('dashboard', '/', { theme: 'dark' }) // leave the demo as we found it
// the table shot switched the (server-side) miners layout; put it back so later runs and the e2e tests start clean
await requireDemo(BASE)
await fetch(BASE + '/api/v1/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ui: { theme: 'dark', view_miners: 'grid' } }) })
} finally {
await browser.close()
}
