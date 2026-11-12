// @vitest-environment node
import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { ACCENT_PRESETS, accentForeground, contrast } from '@/lib/theme'

// Card #2393 (umbrella #2244): the app wears the HashHurdr Night Shift palette in its three existing themes and bundles
// the brand fonts. These tests read the real stylesheet, fonts and public files, so a value edited out of the approved
// kit fails here. dark = the kit's "dark", amoled = the kit's "black" (OLED and wall display), light = the kit's "light".

const here = (rel: string): string => fileURLToPath(new URL(rel, import.meta.url))
const read = (rel: string): string => readFileSync(here(rel), 'utf8')
const css = read('./main.css')

type ThemeName = 'dark' | 'amoled' | 'light'
const THEME_NAMES: ThemeName[] = ['dark', 'amoled', 'light']

function firstGroup(re: RegExp, what: string): string {
  const match = re.exec(css)
  expect(match, `main.css has the ${what} block`).not.toBeNull()
  return match![1]!
}
const colourBlocks: Record<ThemeName, string> = {
  dark: firstGroup(/:root,\s*:root\[data-theme='dark'\] \{([^}]*)\}/, 'dark colour'),
  amoled: firstGroup(/:root\[data-theme='amoled'\] \{([^}]*)\}/, 'amoled colour'),
  light: firstGroup(/:root\[data-theme='light'\] \{([^}]*)\}/, 'light colour'),
}
const derivedRoot = firstGroup(/\n:root \{([^}]*)\}/, 'accent-derived')
const derivedLight = firstGroup(/:root\[data-theme='light'\] \{([^}]*--accent-text[^}]*)\}/, 'light accent-derived')

function rawToken(block: string, name: string): string | undefined {
  return new RegExp(`(?:^|[\\s;{])${name}:\\s*([^;]+);`).exec(block)?.[1]?.trim().toLowerCase()
}
/** A colour token of a theme; the light and black themes inherit what they do not set from the dark block. */
function colour(theme: ThemeName, name: string): string {
  const value = rawToken(colourBlocks[theme], name) ?? (theme === 'dark' ? undefined : rawToken(colourBlocks.dark, name))
  expect(value, `${theme} ${name}`).toMatch(/^#[0-9a-f]{6}$/)
  return value!
}

// Values copied from the approved kit's tokens (kit theme names in the comments).
const KIT: Record<ThemeName, Record<string, string>> = {
  dark: {
    '--bg': '#0a0a0a', '--surface-1': '#151413', '--surface-2': '#1d1c1a', '--surface-3': '#272522',
    '--line': '#2e2c29', '--line-strong': '#7c766c',
    '--fg': '#f4f1ea', '--fg-muted': '#b9b2a7', '--fg-subtle': '#958e84',
    '--ok': '#3dd68c', '--warn': '#f5d547', '--bad': '#ff6b6b', '--info': '#5cb8ff', '--violet': '#e08bc1',
    '--chart-1': '#f7931a', '--chart-2': '#56b4e9', '--chart-3': '#f0e442', '--chart-4': '#2fbf9b', '--chart-5': '#e08bc1', '--chart-6': '#d6d0c5',
    '--chart-grid': '#2e2c29', '--chart-axis': '#958e84',
    '--accent-base': '#f7931a', '--on-bad': '#0a0a0a',
  },
  amoled: {
    '--bg': '#000000', '--surface-1': '#0d0d0c', '--surface-2': '#151413', '--surface-3': '#1d1c1a',
    '--line': '#272522', '--chart-grid': '#272522',
  },
  light: {
    '--bg': '#faf8f4', '--surface-1': '#ffffff', '--surface-2': '#f2efe9', '--surface-3': '#e8e4dc',
    '--line': '#e2ddd4', '--line-strong': '#7c766c',
    '--fg': '#0a0a0a', '--fg-muted': '#4f4a43', '--fg-subtle': '#6b655c',
    '--ok': '#0b6b41', '--warn': '#7a5a00', '--bad': '#b42525', '--info': '#1a5ab8', '--violet': '#a8407a',
    '--chart-1': '#b35c00', '--chart-2': '#0072b2', '--chart-3': '#8c7a00', '--chart-4': '#007f66', '--chart-5': '#a8407a', '--chart-6': '#57524a',
    '--chart-grid': '#e2ddd4', '--chart-axis': '#6b655c',
    '--on-bad': '#ffffff',
  },
}
// The kit's black theme has the same text, signal and chart colours as dark, so the app's amoled block must not redefine them.
const AMOLED_INHERITS = ['--line-strong', '--fg', '--fg-muted', '--fg-subtle', '--ok', '--warn', '--bad', '--info', '--violet', '--on-bad', '--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5', '--chart-6', '--chart-axis', '--accent-base']

describe('issue 2393: Night Shift colour tokens', () => {
  it.each(THEME_NAMES)('the %s theme carries the kit values', (theme) => {
    for (const [name, hex] of Object.entries(KIT[theme])) {
      expect(rawToken(colourBlocks[theme], name), `${theme} ${name}`).toBe(hex)
    }
  })

  it('the black (amoled) theme inherits the dark text, signal and chart colours', () => {
    for (const name of AMOLED_INHERITS) expect(rawToken(colourBlocks.amoled, name), `amoled ${name}`).toBeUndefined()
  })

  it('keeps the three existing theme selectors and no new theme name', () => {
    expect([...css.matchAll(/data-theme='([\w-]+)'/g)].map((m) => m[1]).filter((v, i, all) => all.indexOf(v) === i).sort()).toEqual(['amoled', 'dark', 'light'])
  })

  it('the default accent is Bitcoin orange and its foreground is the kit jet', () => {
    expect(rawToken(colourBlocks.dark, '--accent-base')).toBe('#f7931a')
    expect(rawToken(derivedRoot, '--accent-fg')).toBe('#0a0a0a')
  })

  it('light keeps orange as the fill and uses Ember for orange text and the focus ring', () => {
    expect(rawToken(derivedLight, '--accent-text')).toBe('var(--accent-ink, #9a4d00)')
    expect(rawToken(derivedLight, '--focus')).toBe('var(--accent-text)')
    expect(rawToken(derivedRoot, '--accent-text')).toBe('var(--accent)')
    expect(rawToken(derivedRoot, '--focus')).toBe('var(--accent)')
    expect(css).toMatch(/:focus-visible \{[^}]*outline: 2px solid var\(--focus\)/)
  })

  it('the wall display series companions are the kit sky and plum, and light uses the darker status colours', () => {
    expect(rawToken(derivedRoot, '--accent-blue')).toBe('#56b4e9')
    expect(rawToken(derivedRoot, '--accent-violet')).toBe('#e08bc1')
    expect(rawToken(derivedLight, '--accent-blue')).toBe('var(--info)')
    expect(rawToken(derivedLight, '--accent-violet')).toBe('var(--violet)')
  })

  it('the alert count badge has its own readable foreground instead of white text', () => {
    expect(css).toMatch(/--color-on-bad:\s*var\(--on-bad\)/)
    for (const file of ['../components/layout/SidebarNav.vue', '../components/layout/MobileNav.vue']) {
      const source = read(file)
      const badgeLine = source.split('\n').find((line) => line.includes('bg-bad'))
      expect(badgeLine, file).toBeDefined()
      expect(badgeLine, file).toContain('text-on-bad')
      expect(badgeLine, file).not.toContain('text-white')
    }
  })
})

// ---------------------------------------------------------------------------------------------------- contrast

const AA_TEXT = 4.5
const AA_UI = 3
const SURFACES = ['--bg', '--surface-1', '--surface-2'] as const
const STATUS = ['--ok', '--warn', '--bad', '--info'] as const
const VIOLET_TINT_ALPHA = 0.15 // the violet Badge tone mixes 15% (Badge.vue)

function blend(fg: string, bg: string, alpha: number): string {
  const channel = (hex: string, i: number): number => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16)
  const mixed = [0, 1, 2].map((i) => Math.round(alpha * channel(fg, i) + (1 - alpha) * channel(bg, i)))
  return `#${mixed.map((v) => v.toString(16).padStart(2, '0')).join('')}`
}
/** The tint share a status colour is mixed in at (`--ok-soft` ...), as written in the stylesheet for that theme. */
function softAlpha(theme: ThemeName, soft: string): number {
  const own = theme === 'light' ? rawToken(derivedLight, soft) : undefined
  const match = /color-mix\(in oklab, var\(--[\w-]+\) (\d+)%, transparent\)/.exec(own ?? rawToken(derivedRoot, soft) ?? '')
  expect(match, `${theme} ${soft} is a colour mix`).not.toBeNull()
  return Number(match![1]) / 100
}
const accentText = (theme: ThemeName): string => (theme === 'light' ? '#9a4d00' : colour(theme, '--accent-base'))
const focusRing = accentText // the focus ring follows the accent text colour in light and the accent in dark

describe('issue 2393: WCAG 2.1 AA contrast of the themed pairs', () => {
  it.each(THEME_NAMES)('%s: body, muted and subtle text read on every surface', (theme) => {
    for (const text of ['--fg', '--fg-muted', '--fg-subtle']) {
      for (const surface of [...SURFACES, '--surface-3']) {
        expect(contrast(colour(theme, text), colour(theme, surface)), `${theme} ${text} on ${surface}`).toBeGreaterThanOrEqual(AA_TEXT)
      }
    }
  })

  it.each(THEME_NAMES)('%s: status text reads on the page, cards and on its own tint', (theme) => {
    for (const status of STATUS) {
      const soft = softAlpha(theme, `${status}-soft`)
      for (const surface of SURFACES) {
        const fg = colour(theme, status)
        const bg = colour(theme, surface)
        expect(contrast(fg, bg), `${theme} ${status} on ${surface}`).toBeGreaterThanOrEqual(AA_TEXT)
        expect(contrast(fg, blend(fg, bg, soft)), `${theme} ${status} on its tint over ${surface}`).toBeGreaterThanOrEqual(AA_TEXT)
      }
    }
    const violet = colour(theme, '--violet')
    expect(contrast(violet, blend(violet, colour(theme, '--surface-1'), VIOLET_TINT_ALPHA)), `${theme} violet on its tint`).toBeGreaterThanOrEqual(AA_TEXT)
  })

  it.each(THEME_NAMES)('%s: orange text, the primary button and the alert count badge', (theme) => {
    const accent = colour(theme, '--accent-base')
    for (const surface of [...SURFACES, '--surface-3']) {
      expect(contrast(accentText(theme), colour(theme, surface)), `${theme} accent text on ${surface}`).toBeGreaterThanOrEqual(AA_TEXT)
    }
    const accentSoft = blend(accent, colour(theme, '--surface-1'), 0.14)
    expect(contrast(accentText(theme), accentSoft), `${theme} accent text on accent tint`).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast('#0a0a0a', accent), `${theme} on-accent`).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast(colour(theme, '--on-bad'), colour(theme, '--bad')), `${theme} count badge`).toBeGreaterThanOrEqual(AA_TEXT)
  })

  it.each(THEME_NAMES)('%s: control borders, focus ring, status dots and chart lines reach 3:1 on cards', (theme) => {
    for (const surface of [...SURFACES, '--surface-3']) {
      expect(contrast(colour(theme, '--line-strong'), colour(theme, surface)), `${theme} control border on ${surface}`).toBeGreaterThanOrEqual(AA_UI)
    }
    for (const surface of ['--bg', '--surface-1']) {
      expect(contrast(focusRing(theme), colour(theme, surface)), `${theme} focus ring on ${surface}`).toBeGreaterThanOrEqual(AA_UI)
    }
    const card = colour(theme, '--surface-1')
    for (const status of STATUS) expect(contrast(colour(theme, status), card), `${theme} ${status} dot`).toBeGreaterThanOrEqual(AA_UI)
    for (const n of [1, 2, 3, 4, 5, 6]) expect(contrast(colour(theme, `--chart-${n}`), card), `${theme} chart-${n}`).toBeGreaterThanOrEqual(AA_UI)
    for (const surface of ['--surface-1', '--surface-2']) {
      expect(contrast(colour(theme, '--chart-axis'), colour(theme, surface)), `${theme} chart axis on ${surface}`).toBeGreaterThanOrEqual(AA_TEXT)
    }
  })

  it('every accent preset still gets a readable button foreground', () => {
    expect(ACCENT_PRESETS).toHaveLength(10)
    for (const preset of ACCENT_PRESETS) {
      expect(contrast(preset.value, accentForeground(preset.value)), preset.name).toBeGreaterThanOrEqual(AA_TEXT)
    }
  })
})

// ---------------------------------------------------------------------------------------------------- fonts

const FONT_DIR = '../../public/fonts/'
// sha256 of the files in the approved kit's fonts/ folder: the app must ship them unmodified.
const KIT_FONT_FILES: Record<string, string> = {
  'Saira-latin.woff2': 'de2f064250d463a76f2daa50317f600087223b3c6a6aa3e7e3ecf858ff3b1133',
  'Inter-latin.woff2': '0a095cbd7ebb3ec3f204741d54f08868e67870d67ccbe6c6f76c6afd8e0fa87d',
  'JetBrainsMono-latin.woff2': 'c72dace1a7b135069510340ec5ca9a24b72deb909f8126e87443107f42ca2023',
  'OFL-Saira.txt': 'f2665d4718b452b3818a877191355ac884a6b9b419d35408fe7ee487e9e8f30f',
  'OFL-Inter.txt': '5b9321a4298cfeb6b34354164a1c3afc3db114569984c502b9b35d988fd58c57',
  'OFL-JetBrainsMono.txt': 'b2fe5e8987594e9ffd1d2ca52a2f5d73eb8335243893c5d6254b5ad69269591d',
}
const sha256 = (file: string): string => createHash('sha256').update(readFileSync(here(FONT_DIR + file))).digest('hex')

describe('issue 2393: bundled brand fonts', () => {
  it('ships the kit font files and the three OFL texts unmodified in web/public/fonts', () => {
    for (const [file, hash] of Object.entries(KIT_FONT_FILES)) {
      expect(existsSync(here(FONT_DIR + file)), file).toBe(true)
      expect(sha256(file), file).toBe(hash)
    }
    for (const file of Object.keys(KIT_FONT_FILES).filter((f) => f.endsWith('.woff2'))) {
      expect(readFileSync(here(FONT_DIR + file)).subarray(0, 4).toString('latin1'), `${file} is a woff2`).toBe('wOF2')
    }
    for (const file of Object.keys(KIT_FONT_FILES).filter((f) => f.startsWith('OFL-'))) {
      expect(readFileSync(here(FONT_DIR + file), 'utf8'), file).toContain('SIL OPEN FONT LICENSE Version 1.1')
    }
  })

  const faces = [...css.matchAll(/@font-face\s*\{([^}]*)\}/g)].map((m) => m[1]!)

  it('declares Saira, Inter and JetBrains Mono locally, with swap', () => {
    const byFamily = new Map(faces.map((face): [string, string] => [/font-family:\s*'([^']+)'/.exec(face)?.[1] ?? '', face]))
    expect([...byFamily.keys()].sort()).toEqual(['Inter Variable', 'JetBrains Mono Variable', 'Saira'])
    const expectedFile: Record<string, string> = { Saira: 'Saira-latin.woff2', 'Inter Variable': 'Inter-latin.woff2', 'JetBrains Mono Variable': 'JetBrainsMono-latin.woff2' }
    for (const [family, face] of byFamily) {
      expect(face, `${family} source`).toContain(`url('/fonts/${expectedFile[family]}') format('woff2')`)
      expect(face, `${family} display`).toMatch(/font-display:\s*swap/)
    }
    expect(byFamily.get('Saira')).toMatch(/font-stretch:\s*50% 125%/) // the kit headline width, 87.5%, is a variation of this axis
    expect(byFamily.get('Saira')).toMatch(/font-weight:\s*100 900/)
  })

  it('makes no request to a font host: no remote URL in the stylesheet, page head or sources', () => {
    expect(css).not.toMatch(/https?:\/\//)
    expect(css).not.toMatch(/@import\s+url\(/)
    expect(css).not.toMatch(/fontsource/)
    const sourceRoot = here('../')
    const files = (readdirSync(sourceRoot, { recursive: true }) as string[])
      .filter((f) => /\.(css|vue|ts)$/.test(f) && !f.endsWith('.test.ts'))
      .map((f) => `src/${f}`)
    files.push('index.html')
    for (const file of files) {
      const text = readFileSync(here(file === 'index.html' ? '../../index.html' : `../../${file}`), 'utf8')
      expect(text, file).not.toMatch(/fonts\.googleapis|fonts\.gstatic|typekit|cdn\.jsdelivr|unpkg\.com/)
    }
  })

  it('uses Saira for headlines, Inter for the interface and JetBrains Mono for numbers and data', () => {
    expect(css).toMatch(/--font-display:\s*'Saira',/)
    expect(css).toMatch(/--font-sans:\s*'Inter Variable',/)
    expect(css).toMatch(/--font-mono:\s*'JetBrains Mono Variable',/)
    expect(css).toMatch(/h1,\s*h2,\s*h3[^{]*\{[^}]*font-family:\s*var\(--font-display\)[^}]*font-stretch:\s*87\.5%/)
    expect(css).toMatch(/\.tnum\s*\{[^}]*font-family:\s*var\(--font-mono\)/)
  })

  it('reaches the build: Vite still copies web/public and the Python package still includes the built UI', () => {
    expect(read('../../vite.config.ts')).not.toContain('publicDir')
    expect(read('../../../pyproject.toml')).toContain('artifacts = ["src/bsmm/web/**"]')
  })
})

// ---------------------------------------------------------------------------------------------------- install surfaces

describe('issue 2393: install and first-paint surfaces follow the dark background', () => {
  it('the manifest and the page head use jet; names, scope and start URL are unchanged', () => {
    const manifest = JSON.parse(read('../../public/manifest.webmanifest')) as Record<string, string>
    expect(manifest.theme_color).toBe('#0a0a0a')
    expect(manifest.background_color).toBe('#0a0a0a')
    expect(manifest.name).toBe('HashHurdr')
    expect(manifest.start_url).toBe('/')
    expect(manifest.scope).toBe('/')
    expect(read('../../index.html')).toContain('<meta name="theme-color" content="#0a0a0a" />')
  })

  it('theme-init.js still reads the same storage keys and handles a custom accent for light text', () => {
    const init = read('../../public/theme-init.js')
    expect(init).toContain("localStorage.getItem('bsmm.theme')")
    expect(init).toContain("localStorage.getItem('bsmm.accent')")
    expect(init).toContain("'--accent-base'")
    expect(init).toContain("'--accent-ink'")
  })
})
