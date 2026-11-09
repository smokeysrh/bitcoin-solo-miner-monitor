import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { Settings } from '@/lib/types'
import { applyLook, type Look } from '@/lib/theme'
import { useSession } from './session'

type Json = Record<string, unknown>
export type SettingsPatch = { [K in keyof Settings]?: Partial<Settings[K]> }
interface PendingSave { change: SettingsPatch }
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
  /** Saves not yet answered, oldest first. They go to the server one at a time. */
  let queue: PendingSave[] = []
  /** The last settings the server confirmed. Only meaningful while `queue` is not empty. */
  let confirmed: Settings | null = null
  let tail: Promise<void> = Promise.resolve()

  function clear(): void {
    epoch++
    queue = []
    confirmed = null
    data.value = null
    saving.value = localOnly.value = false
  }

  /** What the screen shows while saves are pending: the confirmed settings with every unanswered save on top. */
  function withPending(base: Settings): Settings {
    return queue.reduce((acc, entry) => mergeSettings(acc, entry.change as Json), base)
  }

  async function load(): Promise<Settings> {
    const started = epoch
    const result = await api.settings()
    if (started !== epoch) throw new DOMException('Session ended', 'AbortError')
    const local = useSession().readOnly ? localAppearance() : {}
    localOnly.value = Object.keys(local).length > 0
    const loaded = mergeSettings(result, { ui: local })
    confirmed = loaded
    data.value = withPending(loaded)
    return data.value
  }

  /** Called once a save has an answer. Drops only that save from what is pending and keeps showing the rest. */
  function settle(entry: PendingSave): void {
    queue = queue.filter((item) => item !== entry)
    if (confirmed) data.value = withPending(confirmed)
    saving.value = queue.length > 0
  }

  async function send(entry: PendingSave, started: number): Promise<void> {
    try {
      if (started !== epoch) throw new DOMException('Session ended', 'AbortError')
      const result = await api.updateSettings(entry.change as Json)
      if (started !== epoch) throw new DOMException('Session ended', 'AbortError')
      confirmed = result
      localOnly.value = false
      settle(entry)
    } catch (e) {
      if (started !== epoch) throw e
      settle(entry)
      throw e
    }
  }

  /**
   * Optimistic update: the UI changes instantly and the server confirms. Saves are sent one at a time, so an older
   * answer can never replace a newer one. A failure removes only that save's change; other saves stay.
   * Appearance settings fall back to "this device only" when the session is read-only.
   */
  async function patch(change: SettingsPatch): Promise<void> {
    if (!data.value) return
    const started = epoch
    const appearanceOnly = Object.keys(change).every((key) => key === 'ui') &&
      Object.keys(change.ui ?? {}).every((key) => LOCAL_FIELDS.some((field) => field === key))
    if (useSession().readOnly && appearanceOnly) {
      // Public principals receive 401 on writes: do not attempt a forbidden request just to save a local look.
      localStorage.setItem(LOCAL_UI_KEY, JSON.stringify({ ...localAppearance(), ...change.ui }))
      if (confirmed) confirmed = mergeSettings(confirmed, change as Json)
      data.value = mergeSettings(data.value, change as Json)
      localOnly.value = true
      return
    }
    const entry: PendingSave = { change }
    const idle = queue.length === 0
    if (idle) confirmed = data.value
    queue.push(entry)
    data.value = mergeSettings(data.value, change as Json)
    saving.value = true
    // With nothing ahead of it the request starts in this same tick (so a later `clear()` still finds it in flight);
    // otherwise it waits for the save before it.
    const sent = idle ? send(entry, started) : tail.then(() => send(entry, started))
    // The next save waits for this one to finish either way; its error still reaches this caller through `sent`.
    tail = sent.catch(() => undefined)
    await sent
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
