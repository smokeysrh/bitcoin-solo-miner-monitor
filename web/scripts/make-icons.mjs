// Renders the PNG app icons from the logo (run once: node scripts/make-icons.mjs; needs CHROME or Playwright's browser).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

mkdirSync('public/icons', { recursive: true })
const mark = (inset) => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="100%" height="100%">
  <defs><linearGradient id="g" x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#FFB547"/><stop offset=".55" stop-color="#F7931A"/><stop offset="1" stop-color="#E5600B"/></linearGradient></defs>
  <g transform="translate(16 16) scale(${inset}) translate(-16 -16)">
    <path d="M16 2.2 27.2 8.6v12.8L16 27.8 4.8 21.4V8.6z" fill="url(#g)"/>
    <path d="M17.6 8.5 11 17.2h4.1l-1 6.3 6.9-9.1h-4.3z" fill="#1b1203" fill-opacity=".9"/>
  </g>
</svg>`

const jobs = [
  { file: 'icon-192.png', size: 192, inset: 0.92, round: 0.22 },
  { file: 'icon-512.png', size: 512, inset: 0.92, round: 0.22 },
  // maskable icons are cropped to a circle or squircle by the OS: keep the mark inside the central 80%
  { file: 'icon-maskable-512.png', size: 512, inset: 0.66, round: 0 },
]

const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined, args: ['--no-sandbox'] })
for (const j of jobs) {
  const page = await browser.newPage({ viewport: { width: j.size, height: j.size } })
  await page.setContent(`<body style="margin:0;background:transparent"><div style="width:${j.size}px;height:${j.size}px;background:#090b10;border-radius:${j.round * 100}%">${mark(j.inset)}</div></body>`)
  await page.screenshot({ path: `public/icons/${j.file}`, omitBackground: true })
  await page.close()
  console.log('wrote public/icons/' + j.file)
}
await browser.close()
