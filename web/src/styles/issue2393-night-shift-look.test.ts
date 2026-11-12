import { beforeEach, describe, expect, it } from 'vitest'
import { ACCENT_PRESETS, THEMES, accentForeground, applyLook, contrast, resolveTheme, type Look } from '@/lib/theme'

// Card #2393: the retheme keeps every stored appearance value working. Theme names, accent colours and storage keys are
// unchanged; the default accent is Bitcoin orange; the page's theme-color follows the new backgrounds.

const root = document.documentElement
const THEME_COLOR = 'meta[name="theme-color"]'
const BITCOIN_ORANGE = '#F7931A'
const MIN_TEXT_CONTRAST = 4.5

const look = (over: Partial<Look> = {}): Look => ({ theme: 'dark', accent: BITCOIN_ORANGE, density: 'comfortable', reduceMotion: false, ...over })
const inline = (name: string): string => root.style.getPropertyValue(name).trim()

beforeEach(() => {
  document.head.innerHTML = '<meta name="theme-color" content="#000000">'
  root.removeAttribute('style')
  root.removeAttribute('data-theme')
  localStorage.clear()
})

describe('issue 2393: stored theme and accent values still resolve', () => {
  it('keeps the theme keys, labels and hints exactly as they were', () => {
    expect(THEMES).toEqual([
      { value: 'dark', label: 'Dark', hint: 'Easy on the eyes' },
      { value: 'amoled', label: 'Black', hint: 'True black for OLED screens' },
      { value: 'light', label: 'Light', hint: 'Bright rooms' },
      { value: 'system', label: 'Match device', hint: 'Follows your OS setting' },
    ])
    expect(resolveTheme('amoled', true)).toBe('amoled')
    expect(resolveTheme('system', true)).toBe('light')
    expect(resolveTheme('system', false)).toBe('dark')
  })

  it('keeps the ten accent presets with their stored values and names', () => {
    expect(ACCENT_PRESETS).toEqual([
      { name: 'Bitcoin orange', value: '#F7931A' },
      { name: 'Amber', value: '#F5B301' },
      { name: 'Lime', value: '#84CC16' },
      { name: 'Emerald', value: '#10B981' },
      { name: 'Cyan', value: '#06B6D4' },
      { name: 'Sky', value: '#38BDF8' },
      { name: 'Indigo', value: '#818CF8' },
      { name: 'Violet', value: '#A78BFA' },
      { name: 'Pink', value: '#F472B6' },
      { name: 'Red', value: '#F87171' },
    ])
  })

  it.each(ACCENT_PRESETS.map((p): [string, string] => [p.name, p.value]))('%s is applied and stored unchanged, with a readable button foreground', (_name, value) => {
    applyLook(look({ accent: value }))
    expect(inline('--accent-base').toLowerCase()).toBe(value.toLowerCase())
    expect(localStorage.getItem('bsmm.accent')).toBe(value)
    expect(contrast(value, inline('--accent-fg'))).toBeGreaterThanOrEqual(MIN_TEXT_CONTRAST)
  })

  it('stores the theme under the same key and value for all three themes', () => {
    for (const theme of ['dark', 'amoled', 'light'] as const) {
      applyLook(look({ theme }))
      expect(root.getAttribute('data-theme')).toBe(theme)
      expect(localStorage.getItem('bsmm.theme')).toBe(theme)
    }
  })

  it('an unusable accent falls back to Bitcoin orange, the default', () => {
    applyLook(look({ accent: 'not-a-colour' }))
    expect(inline('--accent-base').toLowerCase()).toBe(BITCOIN_ORANGE.toLowerCase())
    expect(localStorage.getItem('bsmm.accent')).toBe(BITCOIN_ORANGE)
  })
})

describe('issue 2393: Night Shift look', () => {
  it('uses the kit jet as the foreground on the orange fill', () => {
    expect(accentForeground(BITCOIN_ORANGE)).toBe('#0a0a0a')
    expect(accentForeground('#1d4ed8')).toBe('#ffffff') // a deep accent still gets white
  })

  it('the page theme-color follows the dark, black and light backgrounds', () => {
    const expected = { dark: '#0a0a0a', amoled: '#000000', light: '#faf8f4' } as const
    for (const [theme, colour] of Object.entries(expected)) {
      applyLook(look({ theme: theme as keyof typeof expected }))
      expect(document.querySelector(THEME_COLOR)?.getAttribute('content'), theme).toBe(colour)
    }
  })

  it('orange keeps the kit Ember for light-theme text; any other accent gets a darkened copy of itself', () => {
    applyLook(look())
    expect(inline('--accent-ink')).toBe('')
    applyLook(look({ accent: '#10B981' }))
    expect(inline('--accent-ink').toLowerCase()).toBe('color-mix(in oklab, #10b981 62%, black)')
    applyLook(look({ accent: '#f7931a' })) // the default written in lower case is still the default
    expect(inline('--accent-ink')).toBe('')
  })
})
