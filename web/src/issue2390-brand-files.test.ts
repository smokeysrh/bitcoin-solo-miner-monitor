// @vitest-environment node
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { BRAND_ASSETS } from '@/lib/brand'

// Card #2390: the install manifest, page head and service worker show HashHurdr; technical identifiers keep their names.
// The files are read from disk, so these tests run against what the browser is actually served.
const publicFile = (name: string): string => readFileSync(fileURLToPath(new URL(`../public/${name}`, import.meta.url)), 'utf8')

describe('issue 2390: brand file URLs', () => {
  it('each URL the components use names a kit file that exists in web/public', () => {
    const urls = Object.values(BRAND_ASSETS)
    expect(urls.length).toBeGreaterThan(0)
    for (const url of urls) {
      expect(existsSync(fileURLToPath(new URL(`../public${url}`, import.meta.url))), url).toBe(true)
    }
  })
})

describe('issue 2390: install manifest and page head', () => {
  it('the manifest names HashHurdr and keeps its start URL and scope', () => {
    const manifest = JSON.parse(publicFile('manifest.webmanifest')) as Record<string, string>
    expect(manifest.name).toBe('HashHurdr')
    expect(manifest.short_name).toBe('HashHurdr')
    expect(manifest.description).toContain('Built for Plebs, By Plebs.')
    expect(manifest.start_url).toBe('/')
    expect(manifest.scope).toBe('/')
  })

  it('the page title, no-script text and icon links use the supplied files', () => {
    const html = readFileSync(fileURLToPath(new URL('../index.html', import.meta.url)), 'utf8')
    expect(html).toContain('<title>HashHurdr</title>')
    expect(html).toContain('<noscript>HashHurdr needs JavaScript.')
    expect(html).toContain('href="/favicon.ico" sizes="16x16 32x32 48x48"')
    expect(html).toContain('href="/favicon.svg"')
    expect(html).toContain('href="/apple-touch-icon-180.png"')
  })

  it('the service worker speaks as HashHurdr and keeps its cache prefix', () => {
    const worker = publicFile('sw.js')
    expect(worker).toContain('HashHurdr could not save a copy for offline use:')
    expect(worker).toContain('HashHurdr is not reachable right now.')
    expect(worker).not.toContain('Solo Miner Monitor')
    expect(worker).toContain("const CACHE_PREFIX = 'bsmm-shell-'")
  })
})
