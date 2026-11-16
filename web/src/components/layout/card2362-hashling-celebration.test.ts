import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { HASHLING_ART } from '@/lib/brand'
import { HASHLING_MOMENTS, HASHLING_UI } from '@/lib/hashlingText'
import type { Settings } from '@/lib/types'
import Celebration from '@/components/layout/Celebration.vue'
import { useHashling } from '@/stores/hashling'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useUi } from '@/stores/ui'

// Card #2362: a found block. The existing celebration dialog stays and is the pop-up on the dashboard: it shows
// Hashling's found-block pose and line instead of the party icon, so two pop-ups never compete. On the wall display
// (nobody there to click Close) the Hashling pop-up carries the block for about a minute and the dialog stays shut.

vi.mock('@/components/ui/Dialog.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    default: defineComponent({
      inheritAttrs: false,
      props: ['open', 'title', 'size', 'hideTitle'],
      emits: ['update:open'],
      setup: (props, { slots }) => () => (props.open ? h('div', { 'data-testid': 'dialog' }, slots.default?.()) : null),
    }),
  }
})

const BLOCK = { height: 900_001, hash: 'ef'.repeat(32) }

type Wrapper = ReturnType<typeof mount>
const wrappers: Wrapper[] = []

/** A canvas context that records the confetti being drawn. happy-dom has none. */
function fakeContext() {
  return { clearRect: vi.fn(), save: vi.fn(), restore: vi.fn(), translate: vi.fn(), rotate: vi.fn(), fillRect: vi.fn(), fillStyle: '', globalAlpha: 1 }
}

/** requestAnimationFrame under test control: frames run only when the test says so. */
const frames: FrameRequestCallback[] = []
function runFrames(at = performance.now()): void {
  const due = frames.splice(0)
  due.forEach((cb) => cb(at))
}
const BURST_OVER_MS = 7_000 // the burst lasts 6.5 s

function osReducedMotion(on: boolean): void {
  vi.stubGlobal('matchMedia', (query: string) => ({ matches: on && query.includes('prefers-reduced-motion'), media: query, addEventListener: () => undefined, removeEventListener: () => undefined }))
}

function boot(popups: boolean | undefined = true, reduceMotion = true) {
  setActivePinia(createPinia())
  useSession().state = 'ready'
  // reduce_motion on by default: no confetti canvas work unless a test asks for it
  useSettings().data = { ui: { reduce_motion: reduceMotion, sound_on_block: false, ...(popups === undefined ? {} : { hashling_popups: popups }) } } as unknown as Settings
  const wrapper = mount(Celebration, { attachTo: document.body })
  wrappers.push(wrapper)
  return { wrapper, ui: useUi(), hashling: useHashling() }
}

beforeEach(() => {
  localStorage.clear()
  frames.length = 0
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => frames.push(cb))
  vi.stubGlobal('cancelAnimationFrame', () => undefined)
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  document.body.innerHTML = ''
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('card 2362: the celebration dialog and Hashling', () => {
  it('on the dashboard the dialog shows the found-block pose and line, and keeps its own words and actions', async () => {
    const { wrapper, ui } = boot()
    ui.celebrate(BLOCK)
    await nextTick()
    const dialog = wrapper.get('[data-testid="celebration"]')
    const img = dialog.get('img')
    expect(img.attributes('src')).toBe(HASHLING_ART['found-block'])
    expect(img.attributes('alt')).toBe(HASHLING_UI.U01c)
    expect(dialog.text()).toContain(HASHLING_MOMENTS.M13.line)
    expect(dialog.text()).toContain('You found a block')
    expect(dialog.text()).toContain('See it on mempool.space')
  })

  it('shows the found-block pose once: one dialog, no second Hashling pop-up', async () => {
    const { wrapper, ui, hashling } = boot()
    ui.celebrate(BLOCK)
    await nextTick()
    expect(wrapper.findAll('[data-testid="celebration"]')).toHaveLength(1)
    expect(wrapper.findAll(`img[src="${HASHLING_ART['found-block']}"]`)).toHaveLength(1)
    expect(hashling.items).toEqual([])
  })

  it('with Hashling pop-ups off it is the dialog it always was (party icon, no pose)', async () => {
    const { wrapper, ui } = boot(false)
    ui.celebrate(BLOCK)
    await nextTick()
    const dialog = wrapper.get('[data-testid="celebration"]')
    expect(dialog.find('img').exists()).toBe(false)
    expect(dialog.text()).not.toContain(HASHLING_MOMENTS.M13.line)
    expect(dialog.text()).toContain('You found a block')
  })

  it('does not call a block a confirmed block when only the miner reported it (no hash): old dialog, no Hashling line', async () => {
    const { wrapper, ui } = boot()
    ui.celebrate({ height: 0, hash: '' })
    await nextTick()
    const dialog = wrapper.get('[data-testid="celebration"]')
    expect(dialog.find('img').exists()).toBe(false)
    expect(dialog.text()).not.toContain(HASHLING_MOMENTS.M13.line)
  })

  it('on the wall display the dialog stays shut, because the Hashling pop-up shows the block and dismisses itself', async () => {
    const { wrapper, ui, hashling } = boot()
    hashling.surface = 'wall'
    ui.celebrate(BLOCK)
    await nextTick()
    expect(wrapper.find('[data-testid="celebration"]').exists()).toBe(false)
    expect(ui.celebration).toBeNull()
  })

  it('on the wall display with pop-ups off the dialog still opens, as before', async () => {
    const { wrapper, ui, hashling } = boot(false)
    hashling.surface = 'wall'
    ui.celebrate(BLOCK)
    await nextTick()
    expect(wrapper.find('[data-testid="celebration"]').exists()).toBe(true)
  })
})

// A confirmed block on the wall display keeps its confetti even though the dialog stays shut there. The burst is drawn
// on the existing canvas; reduce motion (the in-app switch or the device setting) turns it off, as for the dialog.
describe('card 2362: the confetti on the wall display', () => {
  /** Fires the block and runs the frame that starts the burst, then one drawing frame. */
  async function blockOnWall(reduceMotion: boolean) {
    const ctx = fakeContext()
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctx as unknown as CanvasRenderingContext2D)
    const booted = boot(true, reduceMotion)
    booted.hashling.surface = 'wall'
    booted.ui.celebrate(BLOCK)
    await nextTick()
    runFrames() // starts the burst
    runFrames() // draws a frame
    await nextTick()
    return { ...booted, ctx, getContext }
  }

  it('plays the burst with the dialog shut: the canvas is shown and pieces are drawn', async () => {
    const { wrapper, ctx, getContext } = await blockOnWall(false)
    expect(wrapper.find('[data-testid="celebration"]').exists()).toBe(false)
    expect(getContext).toHaveBeenCalledWith('2d')
    expect(ctx.fillRect).toHaveBeenCalled()
    expect(wrapper.get('canvas').classes()).not.toContain('hidden')
  })

  it('hides the canvas again when the burst is over, and the dialog was never opened', async () => {
    const { wrapper, ctx, ui } = await blockOnWall(false)
    runFrames(performance.now() + BURST_OVER_MS)
    await nextTick()
    expect(ctx.clearRect).toHaveBeenCalled()
    expect(frames).toHaveLength(0)
    expect(wrapper.get('canvas').classes()).toContain('hidden')
    expect(wrapper.find('[data-testid="celebration"]').exists()).toBe(false)
    expect(ui.celebration).toBeNull()
  })

  it('plays no burst with the in-app Reduce motion switch on', async () => {
    const { wrapper, getContext } = await blockOnWall(true)
    expect(getContext).not.toHaveBeenCalled()
    expect(wrapper.get('canvas').classes()).toContain('hidden')
  })

  it('plays no burst when the device asks for reduced motion', async () => {
    osReducedMotion(true)
    const { wrapper, getContext } = await blockOnWall(false)
    expect(getContext).not.toHaveBeenCalled()
    expect(wrapper.get('canvas').classes()).toContain('hidden')
  })

  it('a block the miner only reported (no hash) still opens the dialog on the wall, as before', async () => {
    const { wrapper, ui, hashling } = boot()
    hashling.surface = 'wall'
    ui.celebrate({ height: 0, hash: '' })
    await nextTick()
    expect(wrapper.find('[data-testid="celebration"]').exists()).toBe(true)
  })
})
