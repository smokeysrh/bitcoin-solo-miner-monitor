<script setup lang="ts">
import { Bell, EllipsisVertical, LogOut, Monitor, Moon, Plus, Search, Sun, SunMoon, Tv } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { THEMES } from '@/lib/theme'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'
import { useUi } from '@/stores/ui'
import LogoMark from '@/components/brand/LogoMark.vue'
import Button from '@/components/ui/Button.vue'
import Kbd from '@/components/ui/Kbd.vue'
import Menu, { type MenuItem } from '@/components/ui/Menu.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import LiveBadge from './LiveBadge.vue'

const route = useRoute()
const router = useRouter()
const live = useLive()
const ui = useUi()
const session = useSession()
const settings = useSettings()
const toasts = useToasts()

const title = computed(() => (route.meta.title as string | undefined) ?? '')
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
const themeIcon = computed(() => {
  const t = settings.data?.ui.theme ?? 'dark'
  return t === 'light' ? Sun : t === 'system' ? SunMoon : Moon
})

const themeItems = computed<MenuItem[]>(() => [
  { heading: 'Theme' },
  ...THEMES.map((t) => ({
    label: `${t.label}${settings.data?.ui.theme === t.value ? '  ✓' : ''}`,
    icon: t.value === 'light' ? Sun : t.value === 'system' ? SunMoon : t.value === 'amoled' ? Monitor : Moon,
    run: () => void settings.patch({ ui: { theme: t.value } }).catch((e: Error) => toasts.error('Could not change theme', e.message)),
  })),
])

const userItems = computed<MenuItem[]>(() => [
  { heading: session.me?.name ?? 'Account' },
  { label: 'Wall display', icon: Tv, run: () => void router.push('/kiosk') },
  ...(session.authEnabled && session.authenticated ? [{ separator: true }, { label: 'Sign out', icon: LogOut, danger: true, run: () => void session.logout() }] : []),
])
</script>

<template>
  <header class="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-3 border-b border-line bg-bg/75 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
    <RouterLink to="/" class="flex items-center gap-2.5 lg:hidden" aria-label="Dashboard"><LogoMark :size="32" alt="" /></RouterLink>
    <h1 class="min-w-0 truncate text-lg font-semibold tracking-tight text-fg" data-testid="page-title">{{ title }}</h1>

    <div class="ml-auto flex items-center gap-2">
      <div class="hidden sm:block"><LiveBadge /></div>

      <button
        class="hidden h-9 items-center gap-2 rounded-xl border border-line bg-surface-2 pr-2 pl-3 text-sm text-subtle transition-colors hover:border-line-strong hover:text-fg md:inline-flex"
        data-testid="open-palette"
        @click="ui.paletteOpen = true"
      >
        <Search class="size-4" aria-hidden="true" />
        <span class="pr-2 xl:pr-6">Search or jump to…</span>
        <span class="hidden items-center gap-2 xl:inline-flex"><Kbd>{{ isMac ? '⌘' : 'Ctrl' }}</Kbd><Kbd>K</Kbd></span>
      </button>
      <Tooltip text="Search (press /)">
        <Button size="icon" variant="ghost" class="md:hidden" aria-label="Search" @click="ui.paletteOpen = true"><Search class="size-[18px]" /></Button>
      </Tooltip>

      <Tooltip text="Wall display">
        <Button to="/kiosk" size="sm" class="hidden px-2.5 lg:inline-flex xl:px-3" aria-label="Wall display" data-testid="open-kiosk">
          <template #icon><Tv class="size-4" aria-hidden="true" /></template>
          <span class="hidden xl:inline">Wall display</span>
        </Button>
      </Tooltip>

      <Button v-if="session.canControl" variant="primary" size="sm" data-testid="add-miner" @click="ui.addMinerOpen = true">
        <template #icon><Plus class="size-4" /></template>
        <span class="hidden sm:inline">Add miner</span>
        <span class="sm:hidden">Add</span>
      </Button>

      <Tooltip :text="live.alerts.length ? `${live.alerts.length} active alert(s)` : 'No active alerts'">
        <RouterLink to="/alerts" class="relative grid size-9 place-items-center rounded-xl text-muted transition-colors hover:bg-surface-3 hover:text-fg" aria-label="Alerts">
          <Bell class="size-[18px]" />
          <span v-if="live.alerts.length" class="absolute top-1.5 right-1.5 size-2 rounded-full bg-bad ring-2 ring-bg" />
        </RouterLink>
      </Tooltip>

      <Menu :items="themeItems">
        <Button size="icon" variant="ghost" aria-label="Change theme"><component :is="themeIcon" class="size-[18px]" /></Button>
      </Menu>
      <Menu :items="userItems">
        <Button size="icon" variant="ghost" aria-label="More options"><EllipsisVertical class="size-[18px]" /></Button>
      </Menu>
    </div>
  </header>
</template>
