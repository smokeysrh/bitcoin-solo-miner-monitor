<script setup lang="ts">
import { Eye, FlaskConical, WifiOff, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, describeError } from '@/lib/api'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useToasts } from '@/stores/toasts'
import Button from '@/components/ui/Button.vue'

const session = useSession()
const live = useLive()
const toasts = useToasts()
const demoDismissed = ref(false)
const busy = ref<string | null>(null)

const showDemo = computed(() => session.demo && !demoDismissed.value)
const lost = computed(() => live.loaded && live.status === 'reconnecting')

const scenarios = [
  { id: 'block', label: 'Find a block' },
  { id: 'offline', label: 'Take a miner offline' },
  { id: 'online', label: 'Bring it back' },
  { id: 'hot', label: 'Overheat one' },
  { id: 'cool', label: 'Cool it down' },
]

async function run(id: string): Promise<void> {
  busy.value = id
  try {
    await api.demoScenario(id)
  } catch (e) {
    toasts.error('Could not run that scenario', describeError(e))
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <div class="space-y-px">
    <div v-if="lost" class="flex items-center gap-2.5 bg-warn-soft px-4 py-2 text-sm text-warn sm:px-6 lg:px-8" role="status">
      <WifiOff class="size-4 shrink-0" aria-hidden="true" />
      Lost the connection to the server. Showing the last data we had; reconnecting automatically.
    </div>

    <div v-if="session.readOnly" class="flex items-center gap-2.5 bg-info-soft px-4 py-2 text-sm text-info sm:px-6 lg:px-8">
      <Eye class="size-4 shrink-0" aria-hidden="true" />
      You have read-only access. Buttons that change things are hidden.
      <RouterLink v-if="session.authEnabled && !session.authenticated" to="/login" class="font-medium underline">Sign in</RouterLink>
    </div>

    <div v-if="showDemo" class="flex flex-wrap items-center gap-x-4 gap-y-2 bg-accent-soft px-4 py-2 text-sm sm:px-6 lg:px-8" data-testid="demo-banner">
      <span class="inline-flex items-center gap-2 font-medium text-accent-text">
        <FlaskConical class="size-4 shrink-0" aria-hidden="true" />
        Demo mode: everything here is simulated.
      </span>
      <span class="hidden text-muted md:inline">Try a situation:</span>
      <span class="flex flex-wrap gap-1.5">
        <Button v-for="s in scenarios" :key="s.id" size="xs" variant="soft" :loading="busy === s.id" @click="run(s.id)">{{ s.label }}</Button>
      </span>
      <button class="ml-auto grid size-6 place-items-center rounded-md text-accent-text hover:bg-accent-soft" aria-label="Hide demo banner" @click="demoDismissed = true">
        <X class="size-4" />
      </button>
    </div>
  </div>
</template>
