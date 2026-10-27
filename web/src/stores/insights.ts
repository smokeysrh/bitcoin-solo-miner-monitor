import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/lib/api'
import type { Insight } from '@/lib/types'

/** The server's plain-language observations ("your node is behind", "set your electricity price"). */
export const useInsights = defineStore('insights', () => {
  const items = ref<Insight[]>([])
  const loaded = ref(false)
  let inflight: Promise<void> | null = null
  let lastLoad = 0

  async function refresh(force = false): Promise<void> {
    if (!force && Date.now() - lastLoad < 15_000) return
    if (inflight) return inflight
    inflight = (async () => {
      try {
        items.value = await api.insights()
        loaded.value = true
        lastLoad = Date.now()
      } catch {
        /* leave the previous list in place */
      } finally {
        inflight = null
      }
    })()
    return inflight
  }

  async function dismiss(id: string): Promise<void> {
    items.value = items.value.filter((i) => i.id !== id)
    try {
      await api.dismissInsight(id)
    } catch {
      void refresh(true)
    }
  }

  const has = (id: string): boolean => items.value.some((i) => i.id === id)
  const ids = computed(() => new Set(items.value.map((i) => i.id)))

  return { items, loaded, refresh, dismiss, has, ids }
})

/** Insights that are really setup steps; the checklist shows these, the tips card shows the rest. */
export const SETUP_INSIGHT_IDS = ['no-miners', 'no-node', 'energy-default', 'no-channel', 'no-password']
