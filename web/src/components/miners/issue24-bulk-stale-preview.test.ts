import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { api } from '@/lib/api'
import type { ActionResult } from '@/lib/types'
import { useLive } from '@/stores/live'
import BulkActionDialog from './BulkActionDialog.vue'

// Render the dialog body inline; the real portal is not what is under test.
vi.mock('@/components/ui/Dialog.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    default: defineComponent({
      props: { open: Boolean, title: String, description: String, size: String },
      setup(props, { slots }) {
        return () => (props.open ? h('div', [slots.default?.(), slots.footer?.()]) : null)
      },
    }),
  }
})

type BulkReply = Awaited<ReturnType<typeof api.bulkAction>>

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function reply(ids: string[], dryRun: boolean): BulkReply {
  const results: ActionResult[] = ids.map((id) => ({ ok: true, device_id: id, name: `Miner ${id}`, message: 'Done' }))
  return { dry_run: dryRun, results, ok: true }
}

let wrapper: ReturnType<typeof mount> | undefined
let bulk: MockInstance<typeof api.bulkAction>

beforeEach(() => {
  setActivePinia(createPinia())
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport: mock the bulk endpoint') }))
  bulk = vi.spyOn(api, 'bulkAction')
  vi.spyOn(useLive(), 'reload').mockResolvedValue(undefined)
  wrapper = mount(BulkActionDialog, { props: { action: 'restart', ids: ['a1', 'a2', 'a3'], open: false } })
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

function dialog() {
  if (!wrapper) throw new Error('not mounted')
  return wrapper
}
async function show(ids: string[]) {
  await dialog().setProps({ open: true, ids })
  await flushPromises()
}
/** The footer's apply button: text starts with the verb ("Restart 3 miners"). */
function applyWrapper() {
  return dialog().findAll('button').find((b) => b.text().startsWith('Restart'))
}
function applyButton(): HTMLButtonElement | undefined {
  return applyWrapper()?.element as HTMLButtonElement | undefined
}
function appliedCalls() {
  return bulk.mock.calls.map(([body]) => body).filter((body) => !body.dry_run)
}

describe('bulk action preview confirmation', () => {
  it('keeps Apply disabled when the next preview fails after an earlier one succeeded', async () => {
    bulk.mockResolvedValueOnce(reply(['a1', 'a2', 'a3'], true))
    await show(['a1', 'a2', 'a3'])
    expect(applyButton()?.disabled).toBe(false)

    await dialog().setProps({ open: false })
    bulk.mockRejectedValueOnce(new Error('Preview unavailable'))
    await show(['b1'])

    expect(bulk).toHaveBeenCalledTimes(2)
    expect(dialog().get('[role="alert"]').text()).toContain('Preview unavailable')
    expect(applyButton()?.disabled).toBe(true)
    expect(dialog().text()).not.toContain('Miner a1')
    expect(appliedCalls()).toEqual([])
  })

  it('previews again when the selection changes while open and ignores the older late response', async () => {
    const previewA = deferred<BulkReply>()
    const previewB = deferred<BulkReply>()
    bulk.mockReturnValueOnce(previewA.promise).mockReturnValueOnce(previewB.promise)
    await show(['a1', 'a2', 'a3'])
    await dialog().setProps({ ids: ['b1'] })
    await flushPromises()
    expect(bulk).toHaveBeenCalledTimes(2)
    expect(bulk.mock.calls[1]![0]).toMatchObject({ action: 'restart', device_ids: ['b1'], dry_run: true })

    previewB.resolve(reply(['b1'], true))
    await flushPromises()
    previewA.resolve(reply(['a1', 'a2', 'a3'], true)) // older request settles last
    await flushPromises()

    expect(applyButton()?.disabled).toBe(false)
    expect(applyButton()?.textContent?.trim()).toBe('Restart 1 miner')
    expect(dialog().text()).toContain('Miner b1')
    expect(dialog().text()).not.toContain('Miner a1')

    bulk.mockResolvedValueOnce(reply(['b1'], false))
    await applyWrapper()!.trigger('click')
    await flushPromises()
    expect(appliedCalls()).toEqual([{ action: 'restart', device_ids: ['b1'], dry_run: false }])
  })

  it('drops a late preview from a closed dialog instead of enabling Apply for the next operation', async () => {
    const previewA = deferred<BulkReply>()
    bulk.mockReturnValueOnce(previewA.promise)
    await show(['a1', 'a2', 'a3'])
    await dialog().setProps({ open: false })
    const previewB = deferred<BulkReply>()
    bulk.mockReturnValueOnce(previewB.promise)
    await show(['b1'])

    previewA.resolve(reply(['a1', 'a2', 'a3'], true))
    await flushPromises()
    expect(applyButton()?.disabled).toBe(true)
    expect(dialog().text()).not.toContain('Miner a1')

    previewB.resolve(reply(['b1'], true))
    await flushPromises()
    expect(applyButton()?.disabled).toBe(false)
    expect(applyButton()?.textContent?.trim()).toBe('Restart 1 miner')
  })

  it('does not let an apply from a closed dialog complete the next operation', async () => {
    bulk.mockResolvedValueOnce(reply(['a1', 'a2', 'a3'], true))
    await show(['a1', 'a2', 'a3'])
    const applyA = deferred<BulkReply>()
    bulk.mockReturnValueOnce(applyA.promise)
    await applyWrapper()!.trigger('click')
    await flushPromises()
    expect(appliedCalls()).toEqual([{ action: 'restart', device_ids: ['a1', 'a2', 'a3'], dry_run: false }])

    await dialog().setProps({ open: false })
    const previewB = deferred<BulkReply>()
    bulk.mockReturnValueOnce(previewB.promise)
    await show(['b1'])
    applyA.resolve(reply(['a1', 'a2', 'a3'], false))
    await flushPromises()

    // The dialog is previewing B; the finished A apply must not replace it with a "done" state.
    expect(applyButton()?.disabled).toBe(true)
    previewB.resolve(reply(['b1'], true))
    await flushPromises()
    expect(applyButton()?.disabled).toBe(false)
    expect(applyButton()?.textContent?.trim()).toBe('Restart 1 miner')
    expect(dialog().text()).not.toContain('Miner a1')
  })
})
