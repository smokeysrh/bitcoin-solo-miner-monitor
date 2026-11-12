import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import LiveBadge from '@/components/layout/LiveBadge.vue'

// Issue 77: the wall display shows the live pill 35% larger. Text, padding, gap and dot grow together; the regular pill is unchanged.

beforeEach(() => setActivePinia(createPinia()))

const pill = (props: { large?: boolean }) =>
  mount(LiveBadge, { props, global: { stubs: { Tooltip: { template: '<div><slot /></div>' } } } }).get('[data-testid="live-badge"]')

describe('LiveBadge large', () => {
  it('keeps the regular size by default', () => {
    const el = pill({})
    for (const cls of ['gap-2', 'px-2.5', 'py-1', 'text-xs']) expect(el.classes()).toContain(cls)
    expect(el.find('[role="img"] > span.size-1\\.5').exists()).toBe(true)
  })

  it('scales text, padding, gap and dot together when large', () => {
    const el = pill({ large: true })
    for (const cls of ['gap-[0.675rem]', 'px-[0.84375rem]', 'py-[0.3375rem]', 'text-[1.0125rem]']) expect(el.classes()).toContain(cls)
    for (const cls of ['gap-2', 'px-2.5', 'py-1', 'text-xs']) expect(el.classes()).not.toContain(cls)
    expect(el.find('[role="img"] > span.size-2').exists()).toBe(true) // 8px dot, from 6px
  })
})
