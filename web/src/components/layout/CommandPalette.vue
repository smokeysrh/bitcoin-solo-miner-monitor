<script setup lang="ts">
import { DialogContent, DialogDescription, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import { CornerDownLeft, Cpu, Moon, Palette, Plus, Radar, RefreshCw, Search, Sparkles, Sun, Tv, Wand2 } from 'lucide-vue-next'
import { computed, nextTick, ref, watch, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { copyText } from '@/composables/useClipboard'
import { rank } from '@/lib/fuzzy'
import { NAV } from '@/lib/nav'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'
import { useUi } from '@/stores/ui'
import Kbd from '@/components/ui/Kbd.vue'

interface Cmd {
  id: string
  group: 'Pages' | 'Miners' | 'Actions' | 'Settings'
  label: string
  hint?: string
  icon: Component
  keywords?: string
  run: () => void
}

const ui = useUi()
const live = useLive()
const router = useRouter()
const session = useSession()
const settings = useSettings()
const toasts = useToasts()

const query = ref('')
const active = ref(0)
const input = ref<HTMLInputElement | null>(null)
const list = ref<HTMLElement | null>(null)

const open = computed({
  get: () => ui.paletteOpen,
  set: (v: boolean) => (ui.paletteOpen = v),
})

function go(path: string): () => void {
  return () => void router.push(path)
}

const SETTINGS_PAGES = [
  ['General', '/settings/general', 'name units polling'],
  ['Appearance', '/settings/appearance', 'theme dark light accent colour density'],
  ['Node & pool', '/settings/sources', 'bitcoin core rpc public pool ckpool mempool'],
  ['Notifications', '/settings/notifications', 'discord telegram ntfy email slack webhook'],
  ['Energy & money', '/settings/energy', 'electricity price kwh currency'],
  ['Safety', '/settings/safety', 'control tuning overclock limits'],
  ['Security', '/settings/security', 'password token login'],
  ['Data & backup', '/settings/data', 'export import backup retention'],
  ['About & health', '/settings/about', 'version update diagnostics doctor'],
] as const

const commands = computed<Cmd[]>(() => {
  const out: Cmd[] = NAV.map((n) => ({ id: `nav-${n.name}`, group: 'Pages' as const, label: n.label, icon: n.icon, keywords: n.keywords, run: go(n.to) }))
  out.push({ id: 'nav-kiosk', group: 'Pages', label: 'Wall display', hint: 'Full-screen dashboard', icon: Tv, keywords: 'kiosk tv fullscreen', run: go('/kiosk') })
  for (const [label, path, kw] of SETTINGS_PAGES) {
    out.push({ id: `set-${path}`, group: 'Settings', label: `Settings: ${label}`, icon: Palette, keywords: kw, run: go(path) })
  }
  for (const d of live.devices) {
    out.push({
      id: `dev-${d.id}`,
      group: 'Miners',
      label: d.name,
      hint: `${d.model_override ?? d.model} · ${d.host}`,
      icon: Cpu,
      keywords: `${d.model} ${d.host} ${d.tags.join(' ')} ${d.status}`,
      run: go(`/miners/${d.id}`),
    })
  }
  if (session.canControl) {
    out.push({ id: 'act-add', group: 'Actions', label: 'Add a miner', hint: 'By address or by scanning', icon: Plus, keywords: 'new scan discover', run: () => (ui.addMinerOpen = true) })
    out.push({ id: 'act-scan', group: 'Actions', label: 'Scan my network for miners', icon: Radar, keywords: 'discover find', run: () => (ui.addMinerOpen = true) })
  }
  out.push({ id: 'act-refresh', group: 'Actions', label: 'Refresh data now', icon: RefreshCw, run: () => void live.reload() })
  out.push({
    id: 'act-simple',
    group: 'Actions',
    label: settings.simple ? 'Turn off simple mode' : 'Turn on simple mode',
    hint: 'Hide advanced details',
    icon: Wand2,
    keywords: 'beginner easy',
    run: () => void settings.patch({ ui: { simple_mode: !settings.simple } }),
  })
  for (const [label, value, icon] of [['dark', 'dark', Moon], ['light', 'light', Sun], ['black (OLED)', 'amoled', Moon], ['match my device', 'system', Sparkles]] as const) {
    out.push({ id: `theme-${value}`, group: 'Actions', label: `Theme: ${label}`, icon, keywords: 'appearance colours', run: () => void settings.patch({ ui: { theme: value } }) })
  }
  out.push({
    id: 'act-llms',
    group: 'Actions',
    label: 'Copy the agent instructions link',
    hint: 'Give this to an AI agent',
    icon: Sparkles,
    keywords: 'llms.txt ai mcp',
    run: () =>
      void copyText(`${location.origin}/llms.txt`).then((ok) => (ok ? toasts.success('Link copied', 'Paste it into your AI agent.') : toasts.error('Could not copy'))),
  })
  return out
})

const results = computed(() => {
  const q = query.value.trim()
  if (!q) {
    // with nothing typed, show the most useful starting points
    const pick = new Set(['nav-dashboard', 'nav-miners', 'nav-odds', 'act-add', 'nav-bitcoin', 'nav-alerts', 'nav-settings', 'nav-kiosk'])
    return commands.value.filter((c) => pick.has(c.id)).map((c) => ({ item: c, score: 1 }))
  }
  return rank(commands.value, q, (c) => `${c.label} ${c.hint ?? ''} ${c.keywords ?? ''} ${c.group}`).slice(0, 40)
})

watch(open, async (v) => {
  if (v) {
    query.value = ''
    active.value = 0
    await nextTick()
    input.value?.focus()
  }
})
watch(results, () => (active.value = 0))

function run(i: number): void {
  const r = results.value[i]
  if (!r) return
  open.value = false
  r.item.run()
}

function onKey(e: KeyboardEvent): void {
  const n = results.value.length
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    active.value = n ? (active.value + 1) % n : 0
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    active.value = n ? (active.value - 1 + n) % n : 0
  } else if (e.key === 'Enter') {
    e.preventDefault()
    run(active.value)
  } else if (e.key === 'Home') {
    active.value = 0
  } else if (e.key === 'End') {
    active.value = Math.max(0, n - 1)
  }
  void nextTick(() => list.value?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }))
}

const grouped = computed(() => {
  const seen = new Map<string, { item: Cmd; index: number }[]>()
  results.value.forEach((r, index) => {
    const arr = seen.get(r.item.group) ?? []
    arr.push({ item: r.item, index })
    seen.set(r.item.group, arr)
  })
  return [...seen.entries()]
})
</script>

<template>
  <DialogRoot v-model:open="open">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-[60] animate-fade-in bg-overlay backdrop-blur-sm" />
      <DialogContent
        class="fixed top-[12vh] left-1/2 z-[60] w-[calc(100vw-1.5rem)] max-w-xl -translate-x-1/2 animate-pop-in overflow-hidden rounded-2xl border border-line-strong bg-surface-1 shadow-pop outline-none"
        aria-describedby="palette-desc"
      >
        <DialogTitle class="sr-only">Search and jump</DialogTitle>
        <DialogDescription id="palette-desc" class="sr-only">Type to find a page, a miner or an action. Use the arrow keys and Enter.</DialogDescription>
        <div class="flex items-center gap-3 border-b border-line px-4">
          <Search class="size-[18px] shrink-0 text-subtle" aria-hidden="true" />
          <input
            ref="input"
            v-model="query"
            class="h-14 flex-1 bg-transparent text-base text-fg outline-none placeholder:text-subtle"
            placeholder="Search pages, miners and actions…"
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-list"
            :aria-activedescendant="results[active] ? `cmd-${results[active]!.item.id}` : undefined"
            autocomplete="off"
            spellcheck="false"
            data-testid="palette-input"
            @keydown="onKey"
          />
          <Kbd>Esc</Kbd>
        </div>
        <div id="palette-list" ref="list" role="listbox" class="max-h-[52vh] overflow-y-auto p-2">
          <p v-if="!results.length" class="px-3 py-10 text-center text-sm text-muted">Nothing matches “{{ query }}”.</p>
          <template v-for="[group, rows] in grouped" :key="group">
            <p class="eyebrow px-3 pt-3 pb-1.5">{{ group }}</p>
            <div
              v-for="{ item, index } in rows"
              :id="`cmd-${item.id}`"
              :key="item.id"
              role="option"
              :aria-selected="index === active"
              :class="['flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5', index === active ? 'bg-accent-soft text-fg' : 'text-muted hover:bg-surface-3']"
              @mousemove="active = index"
              @click="run(index)"
            >
              <component :is="item.icon" class="size-4 shrink-0" :class="index === active ? 'text-accent-text' : 'text-subtle'" aria-hidden="true" />
              <span class="min-w-0 flex-1 truncate text-sm" :class="index === active && 'font-medium'">{{ item.label }}</span>
              <span v-if="item.hint" class="hidden max-w-[40%] truncate text-xs text-subtle sm:block">{{ item.hint }}</span>
              <CornerDownLeft v-if="index === active" class="size-3.5 shrink-0 text-accent-text" aria-hidden="true" />
            </div>
          </template>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
