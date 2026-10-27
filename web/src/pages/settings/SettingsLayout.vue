<script setup lang="ts">
import { BellRing, Coins, Database, Info, Lock, Palette, Server, ShieldAlert, SlidersHorizontal } from 'lucide-vue-next'
import { RouterLink, RouterView } from 'vue-router'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'

const session = useSession()
const settings = useSettings()

const items = [
  { to: '/settings/general', label: 'General', icon: SlidersHorizontal },
  { to: '/settings/appearance', label: 'Appearance', icon: Palette },
  { to: '/settings/sources', label: 'Node & pool', icon: Server },
  { to: '/settings/notifications', label: 'Notifications', icon: BellRing },
  { to: '/settings/energy', label: 'Energy & money', icon: Coins },
  { to: '/settings/safety', label: 'Safety', icon: ShieldAlert },
  { to: '/settings/security', label: 'Security', icon: Lock },
  { to: '/settings/data', label: 'Data & backup', icon: Database },
  { to: '/settings/about', label: 'About & health', icon: Info },
]
</script>

<template>
  <div class="space-y-5">
    <header>
      <h2 class="text-2xl font-semibold tracking-tight text-fg">Settings</h2>
      <p class="mt-1 text-sm text-muted">Most changes save as soon as you make them.</p>
    </header>
    <p v-if="session.state === 'ready' && !session.canAdmin" class="rounded-xl border border-info/30 bg-info-soft px-4 py-3 text-sm text-info">You are signed in without admin rights, so most settings are read-only. Appearance still works on this device.</p>
    <p v-if="settings.localOnly" class="rounded-xl border border-line bg-surface-2 px-4 py-3 text-sm text-muted">Appearance changes are saved on this device only.</p>
    <div class="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)]">
      <nav aria-label="Settings sections" class="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1 lg:sticky lg:top-24 lg:mx-0 lg:flex-col lg:self-start lg:overflow-visible lg:px-0">
        <RouterLink
          v-for="i in items"
          :key="i.to"
          :to="i.to"
          custom
          v-slot="{ href, navigate, isActive }"
        >
          <a
            :href="href"
            :aria-current="isActive ? 'page' : undefined"
            :class="['flex h-10 shrink-0 items-center gap-2.5 rounded-xl px-3 text-sm font-medium whitespace-nowrap transition-colors', isActive ? 'bg-accent-soft text-accent-text' : 'text-muted hover:bg-surface-3 hover:text-fg']"
            @click="navigate"
          >
            <component :is="i.icon" class="size-4" aria-hidden="true" />{{ i.label }}
          </a>
        </RouterLink>
      </nav>
      <div class="min-w-0 space-y-[var(--gap-grid)]"><RouterView /></div>
    </div>
  </div>
</template>
