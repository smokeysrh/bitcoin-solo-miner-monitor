<script setup lang="ts">
import { TooltipProvider } from 'reka-ui'
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import Celebration from '@/components/layout/Celebration.vue'
import ConfirmHost from '@/components/ui/ConfirmHost.vue'
import Toaster from '@/components/ui/Toaster.vue'
import Button from '@/components/ui/Button.vue'
import { applyLook, watchSystemTheme } from '@/lib/theme'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useInsights } from '@/stores/insights'
import { useUi } from '@/stores/ui'
import { useToasts } from '@/stores/toasts'
import { pendingConfirm } from '@/composables/useConfirm'

const session = useSession()
const live = useLive()
const settings = useSettings()
const route = useRoute()
const router = useRouter()
const insights = useInsights()
const ui = useUi()
const toasts = useToasts()

// Start and stop everything that talks to the server as the session changes (sign in, expiry, sign out).
watch(
  () => session.state,
  async (state, _old, onCleanup) => {
    let cancelled = false
    onCleanup(() => { cancelled = true })
    if (state === 'ready') {
      if (!settings.data) {
        try {
          await settings.load()
          applyLook(settings.look)
        } catch (e) {
          if (!cancelled) console.warn('Could not load settings', e)
        }
      }
      if (!cancelled && session.state === 'ready') live.start()
    } else {
      live.stop()
      settings.clear()
      insights.clear()
      ui.clear()
      toasts.items = []
      pendingConfirm.value?.resolve(false)
      pendingConfirm.value = null
      if (state === 'login' && !route.meta.public) {
        void router.replace({ name: 'login', query: route.fullPath !== '/' ? { next: route.fullPath } : undefined })
      }
    }
  },
  { immediate: true, flush: 'sync' },
)

let unwatchTheme: (() => void) | null = null
onMounted(() => {
  unwatchTheme = watchSystemTheme(() => undefined)
})
onBeforeUnmount(() => unwatchTheme?.())
</script>

<template>
  <TooltipProvider :delay-duration="250" :skip-delay-duration="100">
    <main v-if="session.state === 'unreachable'" class="grid min-h-dvh place-items-center p-6 text-center">
      <div class="max-w-md space-y-4">
        <h1 class="text-xl font-semibold">Can't reach Solo Miner Monitor</h1>
        <p class="text-sm text-muted">{{ session.error ?? 'The server did not answer.' }} Check that it is still running, then try again.</p>
        <Button variant="primary" @click="session.bootstrap()">Try again</Button>
      </div>
    </main>
    <RouterView v-else-if="route.meta.bare && (session.state === 'ready' || route.meta.public)" />
    <AppShell v-else-if="session.state === 'ready'" />
    <Celebration v-if="session.state === 'ready'" />
    <Toaster v-if="session.state === 'ready'" />
    <ConfirmHost v-if="session.state === 'ready'" />
  </TooltipProvider>
</template>
