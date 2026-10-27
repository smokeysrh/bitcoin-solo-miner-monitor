<script setup lang="ts">
import { Ellipsis, Plus, Tv } from 'lucide-vue-next'
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { MOBILE_PRIMARY, NAV } from '@/lib/nav'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import Dialog from '@/components/ui/Dialog.vue'

const live = useLive()
const ui = useUi()
const session = useSession()
const router = useRouter()
const more = ref(false)

const primary = NAV.filter((n) => MOBILE_PRIMARY.includes(n.name))
const rest = NAV.filter((n) => !MOBILE_PRIMARY.includes(n.name))

function go(path: string): void {
  more.value = false
  void router.push(path)
}
</script>

<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface-1/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
    aria-label="Main navigation"
  >
    <ul class="mx-auto grid max-w-lg grid-cols-5">
      <li v-for="item in primary" :key="item.name">
        <RouterLink :to="item.to" custom v-slot="{ href, navigate, isActive, isExactActive }">
          <a
            :href="href"
            :aria-current="(item.to === '/' ? isExactActive : isActive) ? 'page' : undefined"
            :class="[
              'relative flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors',
              (item.to === '/' ? isExactActive : isActive) ? 'text-accent-text' : 'text-subtle',
            ]"
            @click="navigate"
          >
            <component :is="item.icon" class="size-5" aria-hidden="true" />
            {{ item.label.split(' ')[0] }}
            <span
              v-if="item.name === 'alerts' && live.alerts.length"
              class="absolute top-2 left-1/2 ml-2 grid min-w-4 place-items-center rounded-full bg-bad px-1 text-[10px] leading-4 font-semibold text-white"
            >
              {{ live.alerts.length }}
            </span>
          </a>
        </RouterLink>
      </li>
      <li>
        <button class="flex h-16 w-full flex-col items-center justify-center gap-1 text-[11px] font-medium text-subtle" @click="more = true">
          <Ellipsis class="size-5" aria-hidden="true" />
          More
        </button>
      </li>
    </ul>
  </nav>

  <Dialog v-model:open="more" title="More" side size="sm">
    <ul class="space-y-1">
      <li v-for="item in rest" :key="item.name">
        <button class="flex h-12 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-medium text-fg hover:bg-surface-3" @click="go(item.to)">
          <component :is="item.icon" class="size-5 text-muted" aria-hidden="true" />
          {{ item.label }}
        </button>
      </li>
      <li>
        <button class="flex h-12 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-medium text-fg hover:bg-surface-3" @click="go('/kiosk')">
          <Tv class="size-5 text-muted" aria-hidden="true" />
          Wall display
        </button>
      </li>
      <li v-if="session.canControl">
        <button
          class="flex h-12 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-medium text-accent-text hover:bg-surface-3"
          @click="
            more = false;
            ui.addMinerOpen = true
          "
        >
          <Plus class="size-5" aria-hidden="true" />
          Add a miner
        </button>
      </li>
    </ul>
  </Dialog>
</template>
