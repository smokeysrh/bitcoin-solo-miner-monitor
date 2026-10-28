import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { Settings } from '@/lib/types'
import { applyLook, type Look } from '@/lib/theme'
import { useSession } from './session'

type Json = Record<string, unknown>
export type SettingsPatch = { [K in keyof Settings]?: Partial<Settings[K]> }
const LOCAL_UI_KEY = 'bsmm.localAppearance'
const LOCAL_FIELDS = ['theme', 'accent', 'density', 'reduce_motion', 'view_miners', 'sound_on_block', 'simple_mode'] as const

function localAppearance(): Partial<Settings['ui']> {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(LOCAL_UI_KEY) ?? '{}')
    if (!isObj(value)) return {}
    const out: Partial<Settings['ui']> = {}
    if (['system', 'dark', 'light', 'amoled'].includes(String(value.theme))) out.theme = value.theme as Settings['ui']['theme']
    if (typeof value.accent === 'string' && /^#[0-9a-f]{6}$/i.test(value.accent)) out.accent = value.accent
    if (value.density === 'comfortable' || value.density === 'compact') out.density = value.density
    if (value.view_miners === 'grid' || value.view_miners === 'table') out.view_miners = value.view_miners
    for (const key of ['reduce_motion', 'sound_on_block', 'simple_mode'] as const) if (typeof value[key] === 'boolean') out[key] = value[key]
    return out
  } catch (e) {
    console.warn('Could not read local appearance preferences', e)
    return {}
  }
}

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
  let epoch = 0

  function clear(): void {
    epoch++
    data.value = null
    saving.value = localOnly.value = false
  }

  async function load(): Promise<Settings> {
    const started = epoch
    const result = await api.settings()
    if (started !== epoch) throw new DOMException('Session ended', 'AbortError')
    const local = useSession().readOnly ? localAppearance() : {}
    localOnly.value = Object.keys(local).length > 0
    data.value = mergeSettings(result, { ui: local })
    return data.value
  }

  /**
   * Optimistic update: the UI changes instantly, the server confirms, and a failure rolls everything back.
   * Appearance settings fall back to "this device only" when the session is read-only.
   */
  async function patch(change: SettingsPatch): Promise<void> {
    if (!data.value) return
    const started = epoch
    const before = data.value
    data.value = mergeSettings(before, change as Json)
    saving.value = true
    try {
      const appearanceOnly = Object.keys(change).every((key) => key === 'ui') &&
        Object.keys(change.ui ?? {}).every((key) => LOCAL_FIELDS.some((field) => field === key))
      if (useSession().readOnly && appearanceOnly) {
        // Public principals receive 401 on writes: do not attempt a forbidden request just to save a local look.
        localStorage.setItem(LOCAL_UI_KEY, JSON.stringify({ ...localAppearance(), ...change.ui }))
        localOnly.value = true
        return
      }
      const result = await api.updateSettings(change as Json)
      if (started !== epoch) throw new DOMException('Session ended', 'AbortError')
      data.value = result
      localOnly.value = false
    } catch (e) {
      if (started !== epoch) throw e
      data.value = before
      throw e
    } finally {
      if (started === epoch) saving.value = false
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

  return { data, saving, localOnly, load, patch, clear, tempUnit, hashUnit, currency, simple, look }
})
