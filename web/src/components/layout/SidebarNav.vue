<script setup lang="ts">
import { PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useFmt } from '@/composables/useFmt'
import { NAV } from '@/lib/nav'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import LogoMark from '@/components/brand/LogoMark.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import LiveBadge from './LiveBadge.vue'

const live = useLive()
const ui = useUi()
const session = useSession()
const fmt = useFmt()

const collapsed = computed(() => ui.sidebarCollapsed)
const groups = [
  { label: 'Monitor', items: NAV.filter((i) => i.group === 'monitor') },
  { label: 'Manage', items: NAV.filter((i) => i.group === 'manage') },
]
const badge = (name: string): number => (name === 'alerts' ? live.alerts.length : 0)
const hash = computed(() => fmt.splitHash(live.summary?.hashrate_hs))
</script>

<template>
  <aside class="sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface-1/70 backdrop-blur-xl lg:flex" aria-label="Main navigation">
    <div class="flex h-16 shrink-0 items-center gap-3 px-[18px]">
      <LogoMark :size="30" />
      <div v-if="!collapsed" class="min-w-0">
        <p class="truncate text-[15px] leading-tight font-semibold tracking-tight text-fg">Solo Miner Monitor</p>
        <p class="truncate text-[11px] text-subtle">{{ session.meta?.instance_name }}</p>
      </div>
    </div>

    <nav class="flex-1 overflow-y-auto px-3 pb-3">
      <div v-for="g in groups" :key="g.label">
        <p v-if="!collapsed" class="eyebrow px-3 pt-5 pb-1.5">{{ g.label }}</p>
        <div v-else class="mx-3 my-3 hairline" />
        <ul class="space-y-0.5">
          <li v-for="item in g.items" :key="item.name">
            <RouterLink :to="item.to" custom v-slot="{ href, navigate, isActive, isExactActive }">
              <Tooltip :text="item.label" side="right" :delay="100">
                <a
                  :href="href"
                  :aria-current="(item.to === '/' ? isExactActive : isActive) ? 'page' : undefined"
                  :data-testid="`nav-${item.name}`"
                  :class="[
                    'group relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors',
                    (item.to === '/' ? isExactActive : isActive) ? 'bg-accent-soft text-accent-text' : 'text-muted hover:bg-surface-3 hover:text-fg',
                    collapsed && 'justify-center px-0',
                  ]"
                  @click="navigate"
                >
                  <span
                    v-if="(item.to === '/' ? isExactActive : isActive)"
                    class="absolute top-2 bottom-2 -left-3 w-[3px] rounded-r-full bg-accent"
                    aria-hidden="true"
                  />
                  <component :is="item.icon" class="size-[18px] shrink-0" aria-hidden="true" />
                  <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
                  <span
                    v-if="badge(item.name)"
                    :class="[
                      'grid min-w-5 place-items-center rounded-full bg-bad px-1.5 py-0.5 text-[11px] leading-none font-semibold text-white',
                      collapsed ? 'absolute top-1 right-1.5' : 'ml-auto',
                    ]"
                    :aria-label="`${badge(item.name)} active alerts`"
                  >
                    {{ badge(item.name) }}
                  </span>
                </a>
              </Tooltip>
            </RouterLink>
          </li>
        </ul>
      </div>
    </nav>

    <div class="shrink-0 space-y-3 border-t border-line p-3">
      <div v-if="!collapsed && live.summary" class="rounded-xl border border-line bg-surface-2/70 p-3">
        <div class="flex items-center justify-between">
          <span class="eyebrow">Fleet</span>
          <LiveBadge compact />
        </div>
        <p class="tnum mt-1.5 text-lg leading-none font-semibold text-fg">
          {{ hash.value }} <span class="text-xs font-medium text-subtle">{{ hash.unit }}</span>
        </p>
        <p class="mt-1 text-xs text-muted">{{ live.summary.devices_online }} of {{ live.summary.devices_total }} miners online</p>
      </div>
      <div v-else-if="collapsed" class="flex justify-center"><LiveBadge compact /></div>
      <button
        class="flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-xs font-medium text-subtle transition-colors hover:bg-surface-3 hover:text-fg"
        :class="collapsed && 'justify-center px-0'"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="ui.sidebarCollapsed = !ui.sidebarCollapsed"
      >
        <PanelLeftOpen v-if="collapsed" class="size-4" />
        <template v-else>
          <PanelLeftClose class="size-4" />
          Collapse
        </template>
      </button>
    </div>
  </aside>
</template>
