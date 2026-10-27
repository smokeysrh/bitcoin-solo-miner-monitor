<script setup lang="ts">
import { useEventListener } from '@vueuse/core'
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { useUi } from '@/stores/ui'
import AddMinerDialog from '@/components/miners/AddMinerDialog.vue'
import Banners from './Banners.vue'
import CommandPalette from './CommandPalette.vue'
import MobileNav from './MobileNav.vue'
import SidebarNav from './SidebarNav.vue'
import TopBar from './TopBar.vue'

const ui = useUi()
const cols = computed(() => (ui.sidebarCollapsed ? 'lg:grid-cols-[76px_minmax(0,1fr)]' : 'lg:grid-cols-[264px_minmax(0,1fr)]'))

function isTyping(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null
  if (!el) return false
  return el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)
}

useEventListener(window, 'keydown', (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    ui.paletteOpen = !ui.paletteOpen
  } else if (e.key === '/' && !e.metaKey && !e.ctrlKey && !isTyping(e.target)) {
    e.preventDefault()
    ui.paletteOpen = true
  }
})
</script>

<template>
  <div :class="['min-h-dvh transition-[grid-template-columns] duration-200 lg:grid', cols]">
    <a href="#main" class="sr-only-focusable fixed top-3 left-3 z-[100] rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-fg">Skip to content</a>
    <SidebarNav />
    <div class="flex min-w-0 flex-col">
      <TopBar />
      <Banners />
      <main id="main" class="mx-auto w-full max-w-[1560px] flex-1 px-4 pt-5 pb-28 sm:px-6 lg:px-8 lg:pb-12" tabindex="-1">
        <RouterView v-slot="{ Component, route }">
          <component :is="Component" :key="route.matched[0]?.path === '/settings' ? 'settings' : route.path" class="animate-fade-up" />
        </RouterView>
      </main>
    </div>
    <MobileNav />
    <CommandPalette />
    <AddMinerDialog />
  </div>
</template>
