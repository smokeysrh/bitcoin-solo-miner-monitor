import { shallowRef } from 'vue'

export interface ConfirmOptions {
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'danger' | 'default'
  /** the user must type this text before the confirm button enables (for irreversible actions) */
  typeToConfirm?: string
}

interface Pending extends ConfirmOptions {
  resolve: (ok: boolean) => void
}

export const pendingConfirm = shallowRef<Pending | null>(null)

/** Ask the user to confirm. Resolves true/false; never rejects. Replaces `window.confirm` everywhere. */
export function confirmDialog(opts: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    pendingConfirm.value?.resolve(false)
    pendingConfirm.value = { ...opts, resolve }
  })
}
