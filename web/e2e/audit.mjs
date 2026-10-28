// Visits every page at desktop and phone size and reports what a person would notice:
// console errors, failed requests, horizontal overflow, accessibility violations (axe) and a screenshot.
// Usage: BASE=http://localhost:6001 CHROME=/path/to/chrome node e2e/audit.mjs [outDir]
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'
import { requireDemo } from '../scripts/demo-preflight.mjs'

const BASE = process.env.BASE ?? 'http://localhost:6001'
const OUT = process.argv[2] ?? 'e2e/shots'
const CHROME = process.env.CHROME
await requireDemo(BASE)
mkdirSync(OUT, { recursive: true })

const ROUTES = (process.env.ROUTES ?? '/,/miners,/bitcoin,/odds,/analytics,/alerts,/alerts?tab=rules,/agents,/settings/general,/settings/appearance,/settings/sources,/settings/notifications,/settings/energy,/settings/safety,/settings/security,/settings/data,/settings/about,/kiosk,/setup').split(',')
const SIZES = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'phone', width: 390, height: 844 },
].filter((s) => !process.env.SIZES || process.env.SIZES.split(',').includes(s.name))

const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] })
let problems = 0
for (const size of SIZES) {
  const ctx = await browser.newContext({ viewport: { width: size.width, height: size.height }, deviceScaleFactor: 1 })
  for (const route of ROUTES) {
    await requireDemo(BASE)
    const page = await ctx.newPage()
    const errors = []
    page.on('console', (m) => ['error', 'warning'].includes(m.type()) && errors.push(`${m.type()}: ${m.text().slice(0, 240)}`))
    page.on('pageerror', (e) => errors.push(`pageerror: ${String(e.message).slice(0, 240)}`))
    page.on('response', (r) => r.status() >= 400 && !r.url().includes('/favicon') && errors.push(`http ${r.status()}: ${r.url().replace(BASE, '')}`))
    try {
      await page.goto(BASE + route, { waitUntil: 'networkidle', timeout: 30000 })
      await page.waitForTimeout(1800)
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      const title = await page.evaluate(() => document.querySelector('[data-testid=page-title], h1, h2')?.textContent?.trim() ?? '(none)')
      const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
      const bad = axe.violations.filter((v) => ['serious', 'critical'].includes(v.impact ?? ''))
      const file = `${OUT}/${size.name}${route.replace(/[/?=]/g, '_') || '_home'}.png`
      await requireDemo(BASE)
      await page.screenshot({ path: file, fullPage: false })
      const flags = []
      if (overflow > 2) flags.push(`H-OVERFLOW +${overflow}px`)
      if (errors.length) flags.push(`${errors.length} console/network issue(s)`)
      if (bad.length) flags.push(`${bad.length} a11y: ${bad.map((v) => `${v.id}(${v.nodes.length})`).join(' ')}`)
      problems += flags.length
      console.log(`${flags.length ? 'FAIL' : 'ok  '} ${size.name.padEnd(7)} ${route.padEnd(26)} "${title.slice(0, 40)}" ${flags.join(' | ')}`)
      for (const e of errors.slice(0, 4)) console.log(`        ${e}`)
      for (const v of bad.slice(0, 3)) console.log(`        axe ${v.id}: ${v.nodes[0]?.html.slice(0, 140)}`)
    } catch (e) {
      problems++
      console.log(`FAIL ${size.name.padEnd(7)} ${route.padEnd(26)} ${String(e.message).split('\n')[0]}`)
    }
    await page.close()
  }
  await ctx.close()
}
await browser.close()
console.log(problems ? `\n${problems} problem(s)` : '\nclean')
process.exit(problems ? 1 : 0)
