import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import LogoMark from '@/components/brand/LogoMark.vue'
import { BRAND_ASSETS, HASHLING_BLINK } from '@/lib/brand'

// Card #2362: the app logo blinks on a regular idle loop (every few seconds, with a little random jitter), when someone
// hovers it, and whenever the live stats refresh (`refreshSignal`: I Dream of Genie). The blink frame is the kit's own
// (same figure, eyes closed). A still logo for reduced motion, and no timer left behind.

const IDLE_BLINK_EVERY_MS = 4_000
const IDLE_BLINK_JITTER_MS = 2_000
const BLINK_MS = 200
const GRID_W = 52
const GRID_H = 44
const SYMBOL_SIZE = 32
const FIRST_STATS_AT = 1_000
const NEXT_STATS_AT = 5_000

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
function mountLogo(props: { size?: number; alt?: string; refreshSignal?: number } = {}): Wrapper {
  const w = mount(LogoMark, { props, attachTo: document.body })
  wrappers.push(w)
  return w
}
const blinking = (w: Wrapper): string | undefined => w.get('[data-testid="logo-mark"]').attributes('data-blinking')
/** Advance fake time and let Vue render, so `data-blinking` is up to date. */
async function advance(ms: number): Promise<void> {
  vi.advanceTimersByTime(ms)
  await nextTick()
}
/** How many separate blinks start while `ms` of fake time pass (sampled every 50 ms; a blink lasts 200 ms). */
async function countBlinks(w: Wrapper, ms: number): Promise<number> {
  const step = 50
  let starts = 0
  let was = blinking(w) === 'true'
  for (let t = 0; t < ms; t += step) {
    await advance(step)
    const now = blinking(w) === 'true'
    if (now && !was) starts++
    was = now
  }
  return starts
}

beforeEach(() => {
  reducedMotion(false)
  document.documentElement.removeAttribute('data-reduce-motion')
  vi.useFakeTimers()
  vi.spyOn(Math, 'random').mockReturnValue(0) // no jitter: the idle blink comes exactly IDLE_BLINK_EVERY_MS after the last blink
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  vi.useRealTimers()
  vi.restoreAllMocks()
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

  it('blinks on a regular idle loop: the first blink after the idle wait, for 200 ms', async () => {
    const w = mountLogo()
    await advance(IDLE_BLINK_EVERY_MS - 100)
    expect(blinking(w)).toBe('false')
    await advance(200)
    expect(blinking(w)).toBe('true')
    await advance(BLINK_MS + 50)
    expect(blinking(w)).toBe('false')
  })

  it('keeps blinking, again and again (it is a loop, not a one-off)', async () => {
    const w = mountLogo()
    const minute = 60_000
    // one blink every IDLE_BLINK_EVERY_MS + BLINK_MS: 14 fit in a minute, so 10 proves the loop without edge fuss
    expect(await countBlinks(w, minute)).toBeGreaterThanOrEqual(10)
  })

  it('adds random jitter to the idle wait: never earlier than the base, never later than base + jitter', async () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.999)
    const w = mountLogo()
    await advance(IDLE_BLINK_EVERY_MS + 100)
    expect(blinking(w)).toBe('false') // the jitter pushed it later
    await advance(IDLE_BLINK_JITTER_MS)
    expect(blinking(w)).toBe('true')
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
    await advance(IDLE_BLINK_EVERY_MS + 10)
    expect(blinking(w)).toBe('true')
  })

  it('blinks when it is hovered, once per hover, and the idle wait starts over afterwards', async () => {
    const w = mountLogo()
    await advance(IDLE_BLINK_EVERY_MS - 1_000) // part-way through the idle wait
    expect(blinking(w)).toBe('false')
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    expect(blinking(w)).toBe('true')
    await advance(BLINK_MS + 50)
    expect(blinking(w)).toBe('false')
    // the old idle deadline (1 s after the hover) passes without a second blink: the wait began again at the hover
    await advance(1_000)
    expect(blinking(w)).toBe('false')
    await advance(IDLE_BLINK_EVERY_MS - BLINK_MS - 50 - 1_000 + 10) // now 4 s + 10 ms after the hover
    expect(blinking(w)).toBe('true')
  })

  it('does not blink at a size that is not a whole multiple of the symbol grid (no blurred half pixels)', async () => {
    const w = mountLogo({ size: 40, refreshSignal: FIRST_STATS_AT })
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    await w.setProps({ refreshSignal: NEXT_STATS_AT })
    expect(blinking(w)).toBe('false')
    expect(vi.getTimerCount()).toBe(0)
    await advance(IDLE_BLINK_EVERY_MS + IDLE_BLINK_JITTER_MS)
    expect(blinking(w)).toBe('false')
  })

  it('stays a still frame for reduced motion: no timer, no blink on hover, none for a stats refresh', async () => {
    reducedMotion(true)
    const w = mountLogo({ refreshSignal: FIRST_STATS_AT })
    expect(vi.getTimerCount()).toBe(0)
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    await w.setProps({ refreshSignal: NEXT_STATS_AT })
    expect(blinking(w)).toBe('false')
    expect(await countBlinks(w, IDLE_BLINK_EVERY_MS + IDLE_BLINK_JITTER_MS + 1_000)).toBe(0)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('also honours the in-app Reduce motion switch', async () => {
    document.documentElement.setAttribute('data-reduce-motion', '1')
    const w = mountLogo({ refreshSignal: FIRST_STATS_AT })
    await w.get('[data-testid="logo-mark"]').trigger('mouseenter')
    await w.setProps({ refreshSignal: NEXT_STATS_AT })
    expect(await countBlinks(w, IDLE_BLINK_EVERY_MS + IDLE_BLINK_JITTER_MS + 1_000)).toBe(0)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('leaves no timer behind when it is removed while waiting to blink', () => {
    const w = mountLogo()
    expect(vi.getTimerCount()).toBeGreaterThan(0) // the idle wait is running
    w.unmount()
    wrappers.splice(0)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('leaves no timer behind when it is removed in the middle of a blink', async () => {
    const w = mountLogo()
    await advance(IDLE_BLINK_EVERY_MS + 10)
    expect(blinking(w)).toBe('true') // blink timer and the next idle wait are both running
    w.unmount()
    wrappers.splice(0)
    expect(vi.getTimerCount()).toBe(0)
  })
})

describe('I Dream of Genie: the logo mark blinks every time the stats refresh', () => {
  it('blinks when refreshSignal changes, and the blink lasts 200 ms', async () => {
    const w = mountLogo({ refreshSignal: FIRST_STATS_AT })
    await w.setProps({ refreshSignal: NEXT_STATS_AT })
    expect(blinking(w)).toBe('true')
    await advance(BLINK_MS + 50)
    expect(blinking(w)).toBe('false')
  })

  it('blinks for every refresh, not only the first', async () => {
    const w = mountLogo({ refreshSignal: FIRST_STATS_AT })
    for (let i = 1; i <= 3; i++) {
      await w.setProps({ refreshSignal: FIRST_STATS_AT + i * 4_000 })
      expect(blinking(w)).toBe('true')
      await advance(BLINK_MS + 50)
      expect(blinking(w)).toBe('false')
      await advance(1_000) // refreshes come every few seconds, well inside the idle wait
    }
  })

  it('does not blink for the first load (the signal going from 0, "nothing yet", to its first value)', async () => {
    const w = mountLogo({ refreshSignal: 0 })
    await w.setProps({ refreshSignal: FIRST_STATS_AT })
    expect(blinking(w)).toBe('false')
    await w.setProps({ refreshSignal: NEXT_STATS_AT }) // the next one is a refresh
    expect(blinking(w)).toBe('true')
  })

  it('does not blink when the signal is unchanged or is already set when he appears', async () => {
    const w = mountLogo({ refreshSignal: FIRST_STATS_AT })
    expect(blinking(w)).toBe('false')
    await w.setProps({ refreshSignal: FIRST_STATS_AT })
    expect(blinking(w)).toBe('false')
  })

  it('ignores a refresh while a blink is already in progress (no second blink queued)', async () => {
    const w = mountLogo({ refreshSignal: FIRST_STATS_AT })
    await w.setProps({ refreshSignal: NEXT_STATS_AT })
    await advance(100) // half-way through the blink
    await w.setProps({ refreshSignal: NEXT_STATS_AT + 1 })
    expect(blinking(w)).toBe('true')
    await advance(BLINK_MS - 100 + 50) // the first blink ends on schedule, not 200 ms after the ignored refresh
    expect(blinking(w)).toBe('false')
    expect(await countBlinks(w, 1_000)).toBe(0)
  })

  it('a refresh blink restarts the idle wait, so the two never bunch into a double blink', async () => {
    const w = mountLogo({ refreshSignal: FIRST_STATS_AT })
    await advance(IDLE_BLINK_EVERY_MS - 500) // the idle blink is 500 ms away
    await w.setProps({ refreshSignal: NEXT_STATS_AT })
    expect(blinking(w)).toBe('true')
    await advance(BLINK_MS + 50)
    expect(blinking(w)).toBe('false')
    expect(await countBlinks(w, 1_000)).toBe(0) // the old idle deadline passed without a blink
    await advance(IDLE_BLINK_EVERY_MS - BLINK_MS - 50 - 1_000 + 10) // now 4 s + 10 ms after the refresh blink
    expect(blinking(w)).toBe('true') // and the idle loop carries on from the refresh blink
  })
})
