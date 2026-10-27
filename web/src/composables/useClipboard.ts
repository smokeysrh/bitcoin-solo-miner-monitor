import { ref } from 'vue'
import { useToasts } from '@/stores/toasts'

/** Copy text to the clipboard, falling back to a hidden textarea on plain-http LAN pages where the Clipboard API is blocked. */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    /* fall through to the legacy path */
  }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.cssText = 'position:fixed;top:-1000px;opacity:0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    ta.remove()
    return ok
  } catch {
    return false
  }
}

export function useCopy() {
  const copied = ref(false)
  const toasts = useToasts()
  let t: ReturnType<typeof setTimeout> | null = null
  async function copy(text: string, what = 'Copied'): Promise<void> {
    const ok = await copyText(text)
    if (!ok) {
      toasts.error('Could not copy', 'Select the text and copy it by hand.')
      return
    }
    copied.value = true
    if (t) clearTimeout(t)
    t = setTimeout(() => (copied.value = false), 1600)
    if (what) toasts.success(what)
  }
  return { copied, copy }
}
