import { computed, reactive, ref, watch } from 'vue'
import { describeError } from '@/lib/api'
import { type SettingsPatch, useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

type Json = Record<string, unknown>

/**
 * A form bound to one settings section (`energy`, `polling`...). It tracks what changed, sends only the changes,
 * and re-seeds from the server's answer. Use it for text and number fields; switches and selects can patch instantly.
 */
export function useSectionForm<K extends keyof NonNullable<ReturnType<typeof useSettings>['data']>>(section: K) {
  const settings = useSettings()
  const toasts = useToasts()
  // fields are bound with v-model and differ per section, so a loose type is the honest one here
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const form = reactive<Record<string, any>>({})
  const saving = ref(false)
  const error = ref<string | null>(null)
  const baseline = ref<Json>({})
  const copy = (value: Json): Json => JSON.parse(JSON.stringify(value))

  const source = computed(() => (settings.data?.[section] ?? {}) as Json)
  function seed(): void {
    for (const k of Object.keys(form)) delete form[k]
    // settings are plain JSON; structuredClone cannot copy a reactive proxy, a JSON round trip can
    Object.assign(form, JSON.parse(JSON.stringify(source.value)))
    baseline.value = copy(source.value)
    error.value = null
  }
  watch(source, (current) => {
    for (const key of new Set([...Object.keys(baseline.value), ...Object.keys(current)])) {
      if (JSON.stringify(form[key]) !== JSON.stringify(baseline.value[key])) continue
      if (key in current) form[key] = copy(current)[key]
      else delete form[key]
      baseline.value[key] = copy(current)[key]
    }
  }, { immediate: true, deep: true })

  const changes = computed<Json>(() => {
    const out: Json = {}
    for (const [k, v] of Object.entries(form)) if (JSON.stringify(v) !== JSON.stringify(baseline.value[k])) out[k] = v
    return out
  })
  const dirty = computed(() => Object.keys(changes.value).length > 0)

  async function save(message = 'Saved'): Promise<boolean> {
    if (saving.value) return false
    if (!dirty.value) return true
    const sent = copy(changes.value)
    const conflicts = Object.keys(sent).filter((key) => JSON.stringify(source.value[key]) !== JSON.stringify(baseline.value[key]) && JSON.stringify(source.value[key]) !== JSON.stringify(sent[key]))
    if (conflicts.length) {
      error.value = 'These settings changed elsewhere. Discard to load the latest values before editing again.'
      return false
    }
    saving.value = true
    error.value = null
    try {
      await settings.patch({ [section]: sent } as SettingsPatch)
      for (const key of Object.keys(sent)) {
        if (JSON.stringify(form[key]) === JSON.stringify(sent[key])) form[key] = copy(source.value)[key]
        baseline.value[key] = copy(source.value)[key]
      }
      toasts.success(message)
      return true
    } catch (e) {
      error.value = describeError(e)
      return false
    } finally {
      saving.value = false
    }
  }

  return { form, dirty, saving, error, save, discard: seed }
}
