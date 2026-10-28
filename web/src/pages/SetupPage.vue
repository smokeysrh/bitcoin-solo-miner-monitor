<script setup lang="ts">
import { ArrowLeft, ArrowRight, BellRing, Check, Coins, PartyPopper, Radar, Sparkles } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import LogoMark from '@/components/brand/LogoMark.vue'
import DiscoveryPanel from '@/components/miners/DiscoveryPanel.vue'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { api, describeError } from '@/lib/api'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const router = useRouter()
const live = useLive()
const session = useSession()
const settings = useSettings()
const toasts = useToasts()

const steps = [
  { id: 'welcome', label: 'Welcome', icon: Sparkles },
  { id: 'miners', label: 'Miners', icon: Radar },
  { id: 'energy', label: 'Electricity', icon: Coins },
  { id: 'alerts', label: 'Alerts', icon: BellRing },
  { id: 'done', label: 'Done', icon: PartyPopper },
] as const
const i = ref(0)
const step = computed(() => steps[i.value]!)
const busy = ref(false)
const error = ref<string | null>(null)

const price = ref<number | null>(settings.data?.energy.price_per_kwh ?? 0.12)
const currency = ref(settings.data?.units.currency ?? 'USD')
const topic = ref(`solo-miners-${Math.random().toString(36).slice(2, 8)}`)
const ntfyDone = ref(false)
const ntfyChannel = ref<{ id: string; topic: string } | null>(null)
watch(topic, () => { ntfyDone.value = false })

function go(n: number): void {
  error.value = null
  i.value = Math.max(0, Math.min(steps.length - 1, n))
}

async function saveEnergy(): Promise<void> {
  if (price.value === null || price.value < 0) return void (error.value = 'Enter a price per kWh, for example 0.14.')
  busy.value = true
  try {
    // always send the price: that is what tells the app you have confirmed it
    await settings.patch({ energy: { price_per_kwh: price.value }, units: { currency: currency.value } })
    go(i.value + 1)
  } catch (e) {
    error.value = describeError(e)
  } finally {
    busy.value = false
  }
}

async function setupNtfy(): Promise<void> {
  if (busy.value) return
  const t = topic.value.trim()
  if (!/^[A-Za-z0-9_-]{3,64}$/.test(t)) return void (error.value = 'Use 3 to 64 letters, numbers, dashes or underscores.')
  busy.value = true
  error.value = null
  try {
    ntfyDone.value = false
    if (!ntfyChannel.value) {
      const ch = await api.createChannel({ kind: 'ntfy', name: 'My phone (ntfy)', config: { topic: t } })
      ntfyChannel.value = { id: ch.id, topic: t }
    } else if (ntfyChannel.value.topic !== t) {
      await api.updateChannel(ntfyChannel.value.id, { config: { topic: t } })
      ntfyChannel.value.topic = t
    }
    const r = await api.testChannel(ntfyChannel.value.id)
    if (!r.ok) throw new Error(r.error ?? 'ntfy did not accept the test message.')
    ntfyDone.value = true
    toasts.success('Test sent', 'Check the ntfy app on your phone.')
  } catch (e) {
    error.value = describeError(e)
  } finally {
    busy.value = false
  }
}

async function finish(to = '/'): Promise<void> {
  try {
    await settings.patch({ general: { onboarding_done: true } })
    await session.refreshMeta()
  } catch {
    /* not being able to remember this is harmless */
  }
  void router.replace(to)
}

const currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'CHF', 'JPY', 'SEK', 'NOK', 'DKK', 'PLN', 'BRL', 'MXN', 'INR'].map((c) => ({ value: c, label: c }))
</script>

<template>
  <main class="mx-auto flex min-h-dvh w-full max-w-2xl flex-col px-4 py-6 sm:py-10">
    <header class="mb-6 flex items-center justify-between">
      <div class="flex items-center gap-3"><LogoMark :size="32" /><span class="text-sm font-semibold text-fg">Solo Miner Monitor</span></div>
      <button class="text-sm text-subtle hover:text-fg" data-testid="skip-setup" @click="finish('/')">Skip setup</button>
    </header>

    <ol class="mb-8 flex items-center gap-2" aria-label="Setup progress">
      <li v-for="(s, n) in steps" :key="s.id" class="flex flex-1 items-center gap-2" :aria-current="n === i ? 'step' : undefined">
        <span :class="['grid size-8 shrink-0 place-items-center rounded-full border text-xs font-semibold transition-colors', n < i ? 'border-transparent bg-accent text-accent-fg' : n === i ? 'border-accent text-accent-text' : 'border-line text-subtle']">
          <Check v-if="n < i" class="size-4" aria-hidden="true" /><component :is="s.icon" v-else class="size-4" aria-hidden="true" />
        </span>
        <span class="hidden text-xs font-medium sm:block" :class="n === i ? 'text-fg' : 'text-subtle'">{{ s.label }}</span>
        <span v-if="n < steps.length - 1" class="h-px flex-1" :class="n < i ? 'bg-accent' : 'bg-line'" aria-hidden="true" />
      </li>
    </ol>

    <section class="card flex-1 p-6 sm:p-8" :aria-label="step.label">
      <div v-if="step.id === 'welcome'" class="animate-fade-up space-y-5">
        <h1 class="text-gradient-accent text-3xl font-bold tracking-tight">Welcome</h1>
        <p class="text-base leading-relaxed text-muted">
          This takes about two minutes. We will find your miners, set your electricity price and, if you like, send alerts to your phone.
          Nothing is changed on your miners, and you can redo any of it later in Settings.
        </p>
        <ul class="space-y-2.5 text-sm text-muted">
          <li class="flex gap-3"><Check class="mt-0.5 size-4 shrink-0 text-ok" aria-hidden="true" />See every miner, its health and its history on one screen</li>
          <li class="flex gap-3"><Check class="mt-0.5 size-4 shrink-0 text-ok" aria-hidden="true" />Know your real odds of finding a block, in plain numbers</li>
          <li class="flex gap-3"><Check class="mt-0.5 size-4 shrink-0 text-ok" aria-hidden="true" />Get told when something breaks, or when you win</li>
        </ul>
        <div class="flex flex-wrap gap-3 pt-2">
          <Button variant="primary" size="lg" data-testid="setup-start" @click="go(1)">Let’s begin <template #icon><ArrowRight class="size-5" /></template></Button>
          <Button variant="ghost" size="lg" to="/agents">Have an AI agent do it</Button>
        </div>
      </div>

      <div v-else-if="step.id === 'miners'" class="animate-fade-up space-y-5">
        <div><h2 class="text-xl font-semibold text-fg">Find your miners</h2><p class="mt-1 text-sm text-muted">Make sure they are powered on and on the same network as this computer.</p></div>
        <DiscoveryPanel @adopted="(n) => n > 0 && go(2)" />
        <p v-if="live.deviceCount" class="text-sm text-ok">{{ live.deviceCount }} miner{{ live.deviceCount === 1 ? '' : 's' }} now being monitored.</p>
      </div>

      <form v-else-if="step.id === 'energy'" class="animate-fade-up space-y-5" @submit.prevent="saveEnergy">
        <div><h2 class="text-xl font-semibold text-fg">What does electricity cost you?</h2><p class="mt-1 text-sm text-muted">Mining is a power bill first. This lets the app show your real costs. Look for “per kWh” on your bill.</p></div>
        <div class="grid gap-4 sm:grid-cols-[1fr_9rem]">
          <Field label="Price per kWh" required hint="Example: 0.14"><template #default="{ id, describedBy }"><Input :id="id" v-model="price" type="number" :min="0" :step="0.01" :described-by="describedBy" data-testid="setup-price" /></template></Field>
          <Field label="Currency"><template #default="{ id }"><Select :id="id" v-model="currency" :options="currencies" /></template></Field>
        </div>
        <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
        <div class="flex flex-wrap gap-3"><Button type="submit" variant="primary" :loading="busy" data-testid="setup-energy-next">Continue <template #icon><ArrowRight class="size-4" /></template></Button></div>
      </form>

      <div v-else-if="step.id === 'alerts'" class="animate-fade-up space-y-5">
        <div><h2 class="text-xl font-semibold text-fg">Alerts on your phone <span class="text-sm font-normal text-subtle">(optional)</span></h2><p class="mt-1 text-sm text-muted">The free ntfy app buzzes your phone when a miner overheats, drops offline, or finds a block.</p></div>
        <ol class="list-decimal space-y-1.5 pl-5 text-sm text-muted"><li>Install <b class="text-fg">ntfy</b> from your app store.</li><li>In the app, subscribe to the topic below.</li><li>Press the button here to send a test.</li></ol>
        <Field label="Your private topic" hint="Anyone who knows the name can read the alerts, so keep the random part."><template #default="{ id, describedBy }"><Input :id="id" v-model="topic" mono :disabled="busy" :described-by="describedBy" data-testid="setup-topic" /></template></Field>
        <p v-if="ntfyChannel" class="text-sm text-muted">This channel is saved. Sending again reuses it; changing the topic updates the same channel.</p>
        <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
        <p v-if="ntfyDone" class="text-sm text-ok">Test sent. If it arrived, you are all set.</p>
        <div class="flex flex-wrap gap-3">
          <Button variant="primary" :loading="busy" @click="setupNtfy">{{ ntfyDone ? 'Send another test' : 'Set up and send a test' }}</Button>
          <Button variant="ghost" @click="go(4)">{{ ntfyDone ? 'Continue' : 'Skip for now' }}</Button>
        </div>
      </div>

      <div v-else class="animate-fade-up space-y-5 text-center">
        <div class="mx-auto grid size-16 place-items-center rounded-3xl bg-accent-soft text-accent-text"><PartyPopper class="size-8" aria-hidden="true" /></div>
        <h2 class="text-2xl font-bold tracking-tight text-fg">You are set</h2>
        <p class="mx-auto max-w-md text-sm leading-relaxed text-muted">
          Your dashboard is ready. Next, the best upgrade is to connect your own Bitcoin node or solo pool and set a password. The checklist on the dashboard walks you through it.
        </p>
        <div class="flex flex-wrap justify-center gap-3"><Button variant="primary" size="lg" data-testid="setup-finish" @click="finish('/')">Open my dashboard</Button><Button variant="ghost" size="lg" @click="finish('/settings/sources')">Connect my node</Button></div>
      </div>
    </section>

    <footer v-if="i > 0 && i < steps.length - 1" class="mt-5 flex justify-between">
      <Button variant="ghost" size="sm" @click="go(i - 1)"><template #icon><ArrowLeft class="size-4" /></template>Back</Button>
      <Button v-if="step.id === 'miners'" variant="ghost" size="sm" @click="go(i + 1)">{{ live.deviceCount ? 'Next' : 'I will add them later' }}</Button>
    </footer>
  </main>
</template>
