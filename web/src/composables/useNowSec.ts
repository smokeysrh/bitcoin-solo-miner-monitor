import { ref, readonly } from 'vue'

const now = ref(Date.now() / 1000)
let started = false

/**
 * One shared one-second clock for every "5s ago" label, so a hundred timestamps cost one timer
 * instead of a hundred.
 */
export function useNowSec() {
  if (!started && typeof window !== 'undefined') {
    started = true
    setInterval(() => {
      now.value = Date.now() / 1000
    }, 1000)
  }
  return readonly(now)
}
