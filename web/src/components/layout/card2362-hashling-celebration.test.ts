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

function boot(popups: boolean | undefined = true) {
  setActivePinia(createPinia())
  useSession().state = 'ready'
  // reduce_motion on: no confetti canvas work in the test
  useSettings().data = { ui: { reduce_motion: true, sound_on_block: false, ...(popups === undefined ? {} : { hashling_popups: popups }) } } as unknown as Settings
  const wrapper = mount(Celebration, { attachTo: document.body })
  wrappers.push(wrapper)
  return { wrapper, ui: useUi(), hashling: useHashling() }
}

beforeEach(() => {
  localStorage.clear()
})
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
  document.body.innerHTML = ''
  vi.restoreAllMocks()
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
