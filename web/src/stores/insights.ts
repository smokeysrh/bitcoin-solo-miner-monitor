import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, describeError } from '@/lib/api'
import type { Insight } from '@/lib/types'

/** The server's plain-language observations ("your node is behind", "set your electricity price"). */
export const useInsights = defineStore('insights', () => {
  const items = ref<Insight[]>([])
  const loaded = ref(false)
  const error = ref<string | null>(null)
  const loading = ref(false)
  const lastSuccess = ref<number | null>(null)
  let epoch = 0
  let inflight: Promise<void> | null = null
  let lastLoad = 0

  async function refresh(force = false): Promise<void> {
    if (!force && Date.now() - lastLoad < 15_000) return
    if (inflight) return inflight
    const started = epoch
    loading.value = true
    inflight = (async () => {
      try {
        const result = await api.insights()
        if (started !== epoch) return
        items.value = result
        loaded.value = true
        lastLoad = Date.now()
        lastSuccess.value = lastLoad
        error.value = null
      } catch (e) {
        if (started === epoch) error.value = describeError(e)
      } finally {
        if (started === epoch) {
          inflight = null
          loading.value = false
        }
      }
    })()
    return inflight
  }

  async function dismiss(id: string): Promise<void> {
    const started = epoch
    items.value = items.value.filter((i) => i.id !== id)
    try {
      await api.dismissInsight(id)
    } catch {
      if (started === epoch) void refresh(true)
    }
  }

  const has = (id: string): boolean => items.value.some((i) => i.id === id)
  const ids = computed(() => new Set(items.value.map((i) => i.id)))

  function clear(): void {
    epoch++
    items.value = []
    loaded.value = loading.value = false
    error.value = null
    lastSuccess.value = null
    lastLoad = 0
    inflight = null
  }

  return { items, loaded, error, loading, lastSuccess, refresh, dismiss, has, ids, clear }
})

/** Insights that are really setup steps; the checklist shows these, the tips card shows the rest. */
export const SETUP_INSIGHT_IDS = ['no-miners', 'no-node', 'energy-default', 'no-channel', 'no-password']
