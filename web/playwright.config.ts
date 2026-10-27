import { defineConfig } from '@playwright/test'

// These tests drive the real UI against a running Solo Miner Monitor in DEMO mode (simulated miners, nothing is saved):
//   bsmm serve --demo --port 8421   and   npm run dev -- --port 6001   (or BASE=http://localhost:8421 against a built app)
// CHROME=/path/to/chrome uses an existing browser instead of Playwright's own download.
const executablePath = process.env.CHROME || undefined

export default defineConfig({
  testDir: 'e2e',
  testMatch: /.*\.spec\.ts/,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE ?? 'http://localhost:6001',
    launchOptions: { executablePath, args: ['--no-sandbox'] },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } }, grepInvert: /@phone/ },
    { name: 'phone', use: { viewport: { width: 390, height: 844 }, hasTouch: true }, grep: /@phone/ },
  ],
})
