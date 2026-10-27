/**
 * Applies the user's look-and-feel (theme, accent colour, density, motion) to the document and keeps a
 * copy in localStorage so `public/theme-init.js` can paint the right colours before the app loads.
 */
export type ThemePref = 'system' | 'dark' | 'light' | 'amoled'
export type ResolvedTheme = 'dark' | 'light' | 'amoled'

export interface Look {
  theme: ThemePref
  accent: string
  density: 'comfortable' | 'compact'
  reduceMotion: boolean
}

export const ACCENT_PRESETS: { name: string; value: string }[] = [
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
]

export const THEMES: { value: ThemePref; label: string; hint: string }[] = [
  { value: 'dark', label: 'Dark', hint: 'Easy on the eyes' },
  { value: 'amoled', label: 'Black', hint: 'True black for OLED screens' },
  { value: 'light', label: 'Light', hint: 'Bright rooms' },
  { value: 'system', label: 'Match device', hint: 'Follows your OS setting' },
]

const HEX = /^#[0-9a-fA-F]{6}$/

/** WCAG relative luminance of a #rrggbb colour. */
export function luminance(hex: string): number {
  const n = Number.parseInt(hex.slice(1), 16)
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * ch[0]! + 0.7152 * ch[1]! + 0.0722 * ch[2]!
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number]
  return (hi + 0.05) / (lo + 0.05)
}

/** Dark text or white text, whichever reads better on the accent colour. */
export function accentForeground(accent: string): string {
  return contrast(accent, '#1b1203') >= contrast(accent, '#ffffff') ? '#1b1203' : '#ffffff'
}

export function resolveTheme(pref: ThemePref, prefersLight: boolean): ResolvedTheme {
  if (pref === 'system') return prefersLight ? 'light' : 'dark'
  return pref
}

let mql: MediaQueryList | null = null
let current: Look | null = null

export function applyLook(look: Look): void {
  current = look
  const root = document.documentElement
  mql ??= window.matchMedia?.('(prefers-color-scheme: light)') ?? null
  const resolved = resolveTheme(look.theme, mql?.matches ?? false)
  root.setAttribute('data-theme', resolved)

  const accent = HEX.test(look.accent) ? look.accent : '#F7931A'
  root.style.setProperty('--accent-base', accent)
  root.style.setProperty('--accent-fg', accentForeground(accent))

  if (look.density === 'compact') root.setAttribute('data-density', 'compact')
  else root.removeAttribute('data-density')
  if (look.reduceMotion) root.setAttribute('data-reduce-motion', '1')
  else root.removeAttribute('data-reduce-motion')

  const meta = document.querySelector('meta[name="theme-color"]')
  meta?.setAttribute('content', resolved === 'light' ? '#f4f5f8' : resolved === 'amoled' ? '#000000' : '#090b10')

  try {
    localStorage.setItem('bsmm.theme', look.theme)
    localStorage.setItem('bsmm.accent', accent)
    localStorage.setItem('bsmm.density', look.density)
    localStorage.setItem('bsmm.reduceMotion', look.reduceMotion ? '1' : '0')
  } catch {
    /* private mode: the server-side setting still applies on the next load */
  }
}

/** Re-apply when the OS switches between light and dark while the preference is "system". */
export function watchSystemTheme(onChange: () => void): () => void {
  const q = window.matchMedia?.('(prefers-color-scheme: light)')
  if (!q) return () => undefined
  const handler = (): void => {
    if (current?.theme === 'system') {
      applyLook(current)
      onChange()
    }
  }
  q.addEventListener('change', handler)
  return () => q.removeEventListener('change', handler)
}

export function isLightTheme(): boolean {
  return document.documentElement.getAttribute('data-theme') === 'light'
}

/** Read a CSS variable's resolved value (used by charts, which draw on a canvas and can't use var()). */
export function cssVar(name: string, fallback = ''): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}
