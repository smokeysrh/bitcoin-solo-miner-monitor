// @vitest-environment node
import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { HASHLING_ART, HASHLING_BLINK, HASHLING_POSES } from '@/lib/brand'

// Card #2362: Hashling is shown with the kit's pose files exactly as supplied (BRAND-POLICY: official marks are used
// unmodified). The hashes below were computed with `sha256sum` on the kit's `mascot/poses/*.svg`.
const KIT_SHA256: Record<string, string> = {
  'hashling-alert.svg': '80032279db6f31f907b9cfe9b9acd6cb2d7383d63f56bb723add64fd03137410',
  'hashling-blink.svg': 'e5d4aec2c72ed18420fcb3e38b199b32b08e97d9b364413191a8fc71b48c1d99',
  'hashling-celebrate.svg': 'c828613f3edd300c69d5d862e70fd3a7c145ec67e4771e3251c385ac2af63c6c',
  'hashling-found-block.svg': 'e1cc1433849fe73397b0a4c716e494f52bc4a5b1057bb0e01ae34eaa7ae038fa',
  'hashling-lottery-ticket.svg': 'e2376d03efbcda8a872321591555cba42f1e818366f89ec6e0ef9002d19d61b5',
  'hashling-sleeping.svg': 'e77946ef79ce124fde8f9776594ba749b516ab3dfa26728a6483641f4b49aea7',
  'hashling-thumbs-up.svg': '219ad028f8c903ba4fa80e714904f1cb18f8c561dc4134ab98882cde885de006',
  'hashling-tinkering.svg': 'cc6e80466d60272b83ef5f30cf4287e6b7d5b6729d29b5050f84d794eb72bc0f',
}

const publicPath = (url: string): string => fileURLToPath(new URL(`../../public${url}`, import.meta.url))
const sha256 = (path: string): string => createHash('sha256').update(readFileSync(path)).digest('hex')

describe('card 2362: Hashling pose files are the kit files, byte for byte', () => {
  const urls = [...HASHLING_POSES.map((pose) => HASHLING_ART[pose]), HASHLING_BLINK]

  it('every URL the app uses names a file in web/public', () => {
    for (const url of urls) expect(existsSync(publicPath(url)), url).toBe(true)
  })

  it.each(urls)('%s matches the kit hash', (url) => {
    const name = url.split('/').pop() as string
    expect(KIT_SHA256[name], `no kit hash recorded for ${name}`).toBeTruthy()
    expect(sha256(publicPath(url))).toBe(KIT_SHA256[name])
  })

  it('uses exactly the kit poses (seven poses and the blink frame), nothing else', () => {
    expect(urls.map((u) => u.split('/').pop()).sort()).toEqual(Object.keys(KIT_SHA256).sort())
  })

  it('is drawn with crisp pixels: the stylesheet keeps .hashling-art pixelated', () => {
    const css = readFileSync(fileURLToPath(new URL('../styles/main.css', import.meta.url)), 'utf8')
    expect(css).toMatch(/\.hashling-art\s*\{[^}]*image-rendering:\s*pixelated/)
  })

  it('is on the 52 x 44 pixel grid the kit draws every pose on', () => {
    for (const url of urls) expect(readFileSync(publicPath(url), 'utf8')).toContain('viewBox="0 0 52 44"')
  })
})
