import { useStorage } from '@vueuse/core'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { FoundBlock } from '@/lib/types'

export interface Celebration {
  height: number
  hash: string
  address?: string | null
  source?: string
  reward_sats?: number | null
}

/** Cross-cutting UI state that no single page owns. */
export const useUi = defineStore('ui', () => {
  const paletteOpen = ref(false)
  const sidebarCollapsed = useStorage('bsmm.sidebarCollapsed', false)
  const celebration = ref<Celebration | null>(null)

  const addMinerOpen = ref(false)
  const mobileMenuOpen = ref(false)

  function celebrate(b: Celebration | FoundBlock): void {
    celebration.value = { height: b.height, hash: b.hash, address: b.address ?? null, reward_sats: 'reward_sats' in b ? b.reward_sats : null }
  }

  function clear(): void {
    paletteOpen.value = addMinerOpen.value = mobileMenuOpen.value = false
    celebration.value = null
  }

  return { paletteOpen, sidebarCollapsed, celebration, addMinerOpen, mobileMenuOpen, celebrate, clear }
})
