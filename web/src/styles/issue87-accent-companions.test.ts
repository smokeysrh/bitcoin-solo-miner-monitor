// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// The wall display's blue and violet series (network bars, chart power line) sit at the same depth as the brand orange:
// the same OKLCH lightness and, as far as sRGB allows, the same chroma, with only the hue changed. These tests read
// the real stylesheet and convert its hex values, so a token edited out of range fails here.

const css = readFileSync(fileURLToPath(new URL('./main.css', import.meta.url)), 'utf8')
const MAX_LIGHTNESS_GAP = 0.01
const MIN_CHROMA_SHARE = 0.85 // sRGB cannot reach the orange's chroma at this lightness for any blue hue (about 0.15 of 0.166)
const MIN_HUE_GAP_DEG = 90

function srgbToLinear(channel: number): number {
  const c = channel / 255
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

/** Hex colour to OKLCH (Björn Ottosson's matrices): lightness 0..1, chroma, hue in degrees. */
function oklch(hex: string): { l: number; c: number; h: number } {
  const [r, g, b] = [1, 3, 5].map((i) => srgbToLinear(parseInt(hex.slice(i, i + 2), 16))) as [number, number, number]
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  const lightness = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s
  const a = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s
  const bb = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
  return { l: lightness, c: Math.hypot(a, bb), h: ((Math.atan2(bb, a) * 180) / Math.PI + 360) % 360 }
}

function token(block: string, name: string): string | undefined {
  return new RegExp(`${name}:\\s*([^;]+);`).exec(block)?.[1]?.trim()
}
const hueGap = (a: number, b: number): number => Math.min(Math.abs(a - b), 360 - Math.abs(a - b))

const darkBlock = /\n:root \{([^}]*)\}/.exec(css)?.[1] ?? '' // the accent block: dark and black themes inherit it
const lightBlock = /:root\[data-theme='light'\] \{([^}]*--accent-text[^}]*)\}/.exec(css)?.[1] ?? ''
const orange = oklch(token(/:root,\s*:root\[data-theme='dark'\] \{([^}]*)\}/.exec(css)?.[1] ?? '', '--accent-base') ?? '#000000')

describe('accent companion colours (wall display blue and violet)', () => {
  const blue = token(darkBlock, '--accent-blue')
  const violet = token(darkBlock, '--accent-violet')

  it('defines both as named tokens for the dark and black themes', () => {
    expect(blue).toMatch(/^#[0-9a-f]{6}$/)
    expect(violet).toMatch(/^#[0-9a-f]{6}$/)
    expect(css).not.toMatch(/\[data-theme='amoled'\] \{[^}]*--accent-(blue|violet)/) // black inherits the dark values
  })

  it.each([
    ['blue', blue],
    ['violet', violet],
  ])('keeps the %s at the orange\'s lightness and close to its chroma, with a different hue', (_name, hex) => {
    const own = oklch(hex ?? '#000000')
    expect(Math.abs(own.l - orange.l)).toBeLessThan(MAX_LIGHTNESS_GAP)
    expect(own.c).toBeGreaterThan(orange.c * MIN_CHROMA_SHARE)
    expect(own.c).toBeLessThan(orange.c * 1.02)
    expect(hueGap(own.h, orange.h)).toBeGreaterThan(MIN_HUE_GAP_DEG)
  })

  it('keeps blue and violet distinct from each other', () => {
    expect(hueGap(oklch(blue ?? '#000000').h, oklch(violet ?? '#000000').h)).toBeGreaterThan(MIN_HUE_GAP_DEG / 1.5)
  })

  it('uses the darker status colours in the light theme so bars stay readable on white', () => {
    expect(token(lightBlock, '--accent-blue')).toBe('var(--info)')
    expect(token(lightBlock, '--accent-violet')).toBe('var(--violet)')
  })
})
