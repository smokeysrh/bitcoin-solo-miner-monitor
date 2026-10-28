import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useSession } from './session'

export type ToastKind = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: number
  kind: ToastKind
  title: string
  body?: string
  /** milliseconds; 0 keeps it until dismissed */
  timeout: number
  action?: { label: string; run: () => void }
}

export const useToasts = defineStore('toasts', () => {
  const items = ref<Toast[]>([])
  let seq = 0

  function dismiss(id: number): void {
    items.value = items.value.filter((t) => t.id !== id)
  }

  function push(t: Omit<Toast, 'id' | 'timeout' | 'kind'> & { kind?: ToastKind; timeout?: number }): number {
    const id = ++seq
    // Cancelled page actions can settle after logout; do not retain their details for the next session.
    if (useSession().state !== 'ready') return id
    const kind = t.kind ?? 'info'
    const timeout = t.timeout ?? (kind === 'error' ? 9000 : 4500)
    items.value = [...items.value.slice(-4), { ...t, id, kind, timeout }]
    if (timeout > 0) setTimeout(() => dismiss(id), timeout)
    return id
  }

  const success = (title: string, body?: string) => push({ kind: 'success', title, body })
  const error = (title: string, body?: string) => push({ kind: 'error', title, body })
  const info = (title: string, body?: string) => push({ kind: 'info', title, body })
  const warning = (title: string, body?: string) => push({ kind: 'warning', title, body })

  return { items, push, dismiss, success, error, info, warning }
})
