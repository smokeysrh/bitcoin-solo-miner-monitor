import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { ApiError, api } from '@/lib/api'
import type { Settings } from '@/lib/types'
import { applyLook, type Look } from '@/lib/theme'

type Json = Record<string, unknown>
export type SettingsPatch = { [K in keyof Settings]?: Partial<Settings[K]> }

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v)

/** Same merge rules as the server: nested objects merge, `dashboard`/`kiosk`/`quiet_hours` are replaced whole. */
export function mergeSettings<T>(base: T, patch: Json): T {
  const opaque = new Set(['dashboard', 'kiosk', 'quiet_hours'])
  const out: Json = { ...(base as Json) }
  for (const [k, v] of Object.entries(patch)) {
    const cur = out[k]
    out[k] = isObj(v) && isObj(cur) && !opaque.has(k) ? mergeSettings(cur, v) : v
  }
  return out as T
}

export const useSettings = defineStore('settings', () => {
  const data = ref<Settings | null>(null)
  const saving = ref(false)
  /** true when a change could only be kept on this device (read-only session) */
  const localOnly = ref(false)

  async function load(): Promise<Settings> {
    data.value = await api.settings()
    return data.value
  }

  /**
   * Optimistic update: the UI changes instantly, the server confirms, and a failure rolls everything back.
   * Appearance settings fall back to "this device only" when the session is read-only.
   */
  async function patch(change: SettingsPatch): Promise<void> {
    if (!data.value) return
    const before = data.value
    data.value = mergeSettings(before, change as Json)
    saving.value = true
    try {
      data.value = await api.updateSettings(change as Json)
      localOnly.value = false
    } catch (e) {
      const onlyUi = Object.keys(change).every((k) => k === 'ui')
      if (e instanceof ApiError && (e.status === 401 || e.status === 403) && onlyUi) {
        localOnly.value = true // keep the optimistic value; it is stored in localStorage by applyLook
        return
      }
      data.value = before
      throw e
    } finally {
      saving.value = false
    }
  }

  const tempUnit = computed(() => data.value?.units.temperature ?? 'c')
  const hashUnit = computed(() => data.value?.units.hashrate ?? 'auto')
  const currency = computed(() => data.value?.units.currency ?? 'USD')
  const simple = computed(() => data.value?.ui.simple_mode ?? false)
  const look = computed<Look>(() => ({
    theme: data.value?.ui.theme ?? 'dark',
    accent: data.value?.ui.accent ?? '#F7931A',
    density: data.value?.ui.density ?? 'comfortable',
    reduceMotion: data.value?.ui.reduce_motion ?? false,
  }))

  watch(
    look,
    (l) => {
      if (data.value) applyLook(l)
    },
    { deep: true },
  )

  return { data, saving, localOnly, load, patch, tempUnit, hashUnit, currency, simple, look }
})
