import { nextTick, ref, type Ref } from 'vue'

export type MoveDirection = 'earlier' | 'later'

/**
 * The draft behind every "Customize" screen (Dashboard, Bitcoin, Odds & costs): the cards being arranged, the keyboard
 * and single-pointer alternative to dragging, and the spoken position after a move.
 * Put `ref="root"` on an element around the editor and `data-move="<id>:<earlier|later>"` on its Move buttons.
 */
export function useLayoutEditor<T extends { id: string }>(titleOf: (id: string) => string) {
  const root = ref<HTMLElement | null>(null)
  const draft = ref([]) as Ref<T[]>
  // Spoken by screen readers after a keyboard move; cleared whenever editing starts.
  const announcement = ref('')

  function begin(items: T[]): void {
    draft.value = items.map((p) => ({ ...p }))
    announcement.value = ''
  }

  function hide(id: string): void {
    draft.value = draft.value.filter((p) => p.id !== id)
  }

  function append(item: T): void {
    draft.value = [...draft.value, item]
  }

  /** Moves a card one place in the same draft array. */
  function move(id: string, direction: MoveDirection): void {
    const from = draft.value.findIndex((p) => p.id === id)
    const to = direction === 'earlier' ? from - 1 : from + 1
    if (from < 0 || to < 0 || to >= draft.value.length) return
    const next = [...draft.value]
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item!)
    draft.value = next
    announcement.value = `${titleOf(id)} moved to position ${to + 1} of ${next.length}`
    void nextTick(() => focusMoveControl(id, direction, to, next.length))
  }

  /** Re-inserting the card's element drops keyboard focus: restore it to the same control, or the opposite one at an end. */
  function focusMoveControl(id: string, direction: MoveDirection, position: number, count: number): void {
    const atEnd = direction === 'earlier' ? position === 0 : position === count - 1
    const target: MoveDirection = atEnd ? (direction === 'earlier' ? 'later' : 'earlier') : direction
    const buttons = Array.from(root.value?.querySelectorAll<HTMLButtonElement>('[data-move]') ?? [])
    buttons.find((b) => b.dataset.move === `${id}:${target}`)?.focus()
  }

  return { root, draft, announcement, begin, hide, append, move }
}
