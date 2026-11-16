import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import LogoMark from '@/components/brand/LogoMark.vue'
import { BRAND_ASSETS, HASHLING_BLINK } from '@/lib/brand'

// Card #2362: the app logo blinks ONCE a few seconds after the page loads, and again when someone hovers it. The
// blink frame is the kit's own (same figure, eyes closed). No loop, and a still logo for reduced motion.

const AUTO_BLINK_AFTER_MS = 3_000
const BLINK_MS = 200
const GRID_W = 52
const GRID_H = 44
const SYMBOL_SIZE = 32

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

function reducedMotion(on: boolean): void {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: on && query.includes('prefers-reduced-motion'),
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }))
}
function mountLogo(props: { size?: number; alt?: string } = {}): Wrapper {
  const w = mount(LogoMark, { props, attachTo: document.body })
  wrappers.push(w)
  return w
}
const blinking = (w: Wrapper): string | undefined => w.get('[data-testid="logo-mark"]').attributes('data-blinking')

beforeEach(() => {
  reducedMotion(false)
  document.documentElement.removeAttribute('data-reduce-motion')
  vi.useFakeTimers()
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('card 2362: the logo mark blinks', () => {
  it('keeps the supplied symbol as the logo image, unchanged (size, name, source)', () => {
    const w = mountLogo({ size: 64 })
    expect(w.get('img').attributes()).toMatchObject({ src: BRAND_ASSETS.symbol, alt: 'HashHurdr logo', width: '64', height: '64' })
  })

  it('is not blinking at first', () => {
    expect(blinking(mountLogo())).toBe('false')
  })

  it('blinks once, a few seconds after load, then stops for good', async () => {
    const w = mountLogo()
    vi.advanceTimersByTime(AUTO_BLINK_AFTER_MS - 100)
    await nextTick()
    expect(blinking(w)).toBe('false')
    vi.advanceTimersByTime(200)
    await nextTick()
    expect(blinking(w)).toBe('true')
    vi.advanceTimersByTime(BLINK_MS + 50)
    await nextTick()
    expect(blinking(w)).toBe('false')
    // no loop: a long time later it has not blinked again
    let blinks = 0
    for (let i = 0; i < 60; i++) {
      vi.advanceTimersByTime(1_000)
      await nextTick()
      if (blinking(w) === 'true') blinks++
    }
    expect(blinks).toBe(0)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('uses the kit blink frame, lined up over the symbol on the pose grid, and only while blinking', async () => {
    const w = mountLogo({ size: SYMBOL_SIZE * 2 })
    const frame = w.get('[data-testid="logo-blink-frame"]')
    expect(frame.attributes('src')).toBe(HASHLING_BLINK)
    expect(frame.attributes('alt')).toBe('')
    expect(frame.attributes('aria-hidden')).toBe('true')
    // a whole-number multiple of the 52 x 44 grid, at the same pixel size as the symbol (64 / 32 = 2)
    expect(frame.attributes('width')).toBe(String(GRID_W * 2))
    expect(frame.attributes('height')).toBe(String(GRID_H * 2))
    expect(frame.classes()).toContain('hashling-art') // main.css keeps .hashling-art pixelated (see the art test)
    vi.advanceTimersByTime(AUTO_BLINK_AFTER_MS + 10)
    await nextTick()
    expect(blinking(w)).toBe('true')
  })

  it('blinks again when it is hovered, once per hover', async () => {
    const w = mountLogo()
    vi.advanceTimersByTime(AUTO_BLINK_AFTER_MS + BLINK_MS + 100)
    await nextTick()
    expect(blinking(w)).toBe('false')
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    expect(blinking(w)).toBe('true')
    vi.advanceTimersByTime(BLINK_MS + 50)
    await nextTick()
    expect(blinking(w)).toBe('false')
    vi.advanceTimersByTime(10_000)
    await nextTick()
    expect(blinking(w)).toBe('false')
  })

  it('does not blink at a size that is not a whole multiple of the symbol grid (no blurred half pixels)', async () => {
    const w = mountLogo({ size: 40 })
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    vi.advanceTimersByTime(AUTO_BLINK_AFTER_MS + 10)
    await nextTick()
    expect(blinking(w)).toBe('false')
  })

  it('stays a still frame for reduced motion: no timer, no blink on hover', async () => {
    reducedMotion(true)
    const w = mountLogo()
    expect(vi.getTimerCount()).toBe(0)
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    vi.advanceTimersByTime(AUTO_BLINK_AFTER_MS + 10)
    await nextTick()
    expect(blinking(w)).toBe('false')
  })

  it('also honours the in-app Reduce motion switch', async () => {
    document.documentElement.setAttribute('data-reduce-motion', '1')
    const w = mountLogo()
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    vi.advanceTimersByTime(AUTO_BLINK_AFTER_MS + 10)
    await nextTick()
    expect(blinking(w)).toBe('false')
  })

  it('leaves no timer behind when it is removed', () => {
    const w = mountLogo()
    w.unmount()
    wrappers.splice(0)
    expect(vi.getTimerCount()).toBe(0)
  })
})
