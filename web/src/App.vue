<script setup lang="ts">
import { TooltipProvider } from 'reka-ui'
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import Celebration from '@/components/layout/Celebration.vue'
import ConfirmHost from '@/components/ui/ConfirmHost.vue'
import Toaster from '@/components/ui/Toaster.vue'
import Button from '@/components/ui/Button.vue'
import { applyLook, watchSystemTheme } from '@/lib/theme'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'

const session = useSession()
const live = useLive()
const settings = useSettings()
const route = useRoute()

// Start and stop everything that talks to the server as the session changes (sign in, expiry, sign out).
watch(
  () => session.state,
  async (state) => {
    if (state === 'ready') {
      if (!settings.data) {
        try {
          await settings.load()
          applyLook(settings.look)
        } catch {
          /* keep defaults */
        }
      }
      live.start()
    } else {
      live.stop()
    }
  },
  { immediate: true },
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
    <RouterView v-else-if="route.meta.bare" />
    <AppShell v-else />
    <Celebration v-if="session.state === 'ready'" />
    <Toaster />
    <ConfirmHost />
  </TooltipProvider>
</template>
