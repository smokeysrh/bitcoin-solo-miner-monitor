<script setup lang="ts">
import { Check, Tv } from 'lucide-vue-next'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Button from '@/components/ui/Button.vue'
import Segmented from '@/components/ui/Segmented.vue'
import ToggleRow from '@/components/ui/ToggleRow.vue'
import { describeError } from '@/lib/api'
import { ACCENT_PRESETS, THEMES, type ThemePref } from '@/lib/theme'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const settings = useSettings()
const toasts = useToasts()

async function patch(change: Parameters<typeof settings.patch>[0]): Promise<void> {
  try {
    await settings.patch(change)
  } catch (e) {
    toasts.error('Could not save that', describeError(e))
  }
}

// miniature previews, drawn with each theme's real colours
const PREVIEW: Record<Exclude<ThemePref, 'system'>, { bg: string; card: string; line: string; fg: string; muted: string }> = {
  dark: { bg: '#090b10', card: '#0f1219', line: '#242833', fg: '#eceef4', muted: '#4b5365' },
  amoled: { bg: '#000000', card: '#07080b', line: '#1f2229', fg: '#eceef4', muted: '#3f4655' },
  light: { bg: '#f4f5f8', card: '#ffffff', line: '#dfe2e9', fg: '#12151c', muted: '#b7bdcb' },
}
const swatch = (t: ThemePref) => PREVIEW[t === 'system' ? 'dark' : t]
const accent = (): string => settings.data?.ui.accent ?? '#F7931A'
</script>

<template>
  <SettingsCard title="Theme" description="Dark is easiest on the eyes in a mining shed. Black saves power on OLED screens.">
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4" role="radiogroup" aria-label="Theme">
      <button
        v-for="t in THEMES"
        :key="t.value"
        role="radio"
        :aria-checked="settings.data?.ui.theme === t.value"
        :class="['group relative overflow-hidden rounded-2xl border p-2.5 text-left transition-colors', settings.data?.ui.theme === t.value ? 'border-accent ring-2 ring-accent/30' : 'border-line hover:border-line-strong']"
        :data-testid="`theme-${t.value}`"
        @click="patch({ ui: { theme: t.value } })"
      >
        <span class="block rounded-xl border p-2" :style="{ background: swatch(t.value).bg, borderColor: swatch(t.value).line }">
          <span class="block h-2 w-10 rounded-full" :style="{ background: accent() }" />
          <span class="mt-2 grid grid-cols-2 gap-1.5">
            <span class="h-7 rounded-md border" :style="{ background: swatch(t.value).card, borderColor: swatch(t.value).line }" />
            <span class="h-7 rounded-md border" :style="{ background: swatch(t.value).card, borderColor: swatch(t.value).line }" />
          </span>
          <span class="mt-2 block h-1.5 w-16 rounded-full" :style="{ background: swatch(t.value).muted }" />
        </span>
        <span class="mt-2.5 flex items-center justify-between gap-2 px-0.5">
          <span><span class="block text-sm font-medium text-fg">{{ t.label }}</span><span class="block text-xs text-subtle">{{ t.hint }}</span></span>
          <Check v-if="settings.data?.ui.theme === t.value" class="size-4 shrink-0 text-accent-text" aria-hidden="true" />
        </span>
      </button>
    </div>
  </SettingsCard>

  <SettingsCard title="Accent colour" description="Used for buttons, highlights and charts. Bitcoin orange is the default.">
    <div class="flex flex-wrap items-center gap-2.5">
      <button
        v-for="a in ACCENT_PRESETS"
        :key="a.value"
        :title="a.name"
        :aria-label="a.name"
        :aria-pressed="settings.data?.ui.accent?.toLowerCase() === a.value.toLowerCase()"
        class="grid size-9 place-items-center rounded-full ring-offset-2 ring-offset-surface-1 transition-transform hover:scale-110 focus-visible:ring-2"
        :class="settings.data?.ui.accent?.toLowerCase() === a.value.toLowerCase() ? 'ring-2 ring-fg' : ''"
        :style="{ background: a.value }"
        @click="patch({ ui: { accent: a.value } })"
      >
        <Check v-if="settings.data?.ui.accent?.toLowerCase() === a.value.toLowerCase()" class="size-4 text-black/70" aria-hidden="true" />
      </button>
      <label class="ml-1 inline-flex h-9 cursor-pointer items-center gap-2 rounded-full border border-line px-3 text-xs font-medium text-muted hover:border-line-strong hover:text-fg">
        Custom
        <input type="color" class="size-5 cursor-pointer rounded border-0 bg-transparent p-0" :value="settings.data?.ui.accent ?? '#F7931A'" aria-label="Pick a custom accent colour" @change="(e) => patch({ ui: { accent: (e.target as HTMLInputElement).value.toUpperCase() } })" />
      </label>
    </div>
  </SettingsCard>

  <SettingsCard title="Layout &amp; motion">
    <div class="flex flex-wrap items-center justify-between gap-3 pb-4">
      <div><p class="text-sm font-medium text-fg">Density</p><p class="text-xs text-subtle">Compact fits more on screen.</p></div>
      <Segmented :model-value="settings.data?.ui.density ?? 'comfortable'" label="Density" :options="[{ value: 'comfortable', label: 'Comfortable' }, { value: 'compact', label: 'Compact' }]" @update:model-value="(v) => patch({ ui: { density: v as 'compact' } })" />
    </div>
    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-line py-4">
      <div><p class="text-sm font-medium text-fg">Miners page</p><p class="text-xs text-subtle">Cards or a table when you open the list.</p></div>
      <Segmented :model-value="settings.data?.ui.view_miners ?? 'grid'" label="Miners layout" :options="[{ value: 'grid', label: 'Cards' }, { value: 'table', label: 'Table' }]" @update:model-value="(v) => patch({ ui: { view_miners: v as 'grid' } })" />
    </div>
    <div class="divide-y divide-line border-t border-line">
      <ToggleRow :model-value="settings.data?.ui.reduce_motion ?? false" title="Reduce motion" description="Turns off animations and the confetti. Your device’s own setting is respected too." @update:model-value="(v) => patch({ ui: { reduce_motion: v } })" />
      <ToggleRow :model-value="settings.data?.ui.sound_on_block ?? false" title="Play a sound when a block is found" description="A short chime in this browser. Your browser may need a click on the page first." @update:model-value="(v) => patch({ ui: { sound_on_block: v } })" />
    </div>
  </SettingsCard>

  <SettingsCard title="Dashboard &amp; wall display" description="Rearrange the dashboard from the dashboard itself. The wall display turns it into a full-screen screen for a TV or spare tablet.">
    <div class="flex flex-wrap gap-2">
      <Button to="/" variant="secondary">Customize the dashboard</Button>
      <Button to="/kiosk" variant="secondary"><template #icon><Tv class="size-4" /></template>Open the wall display</Button>
      <Button variant="ghost" @click="patch({ ui: { dashboard: null } })">Reset dashboard layout</Button>
    </div>
  </SettingsCard>
</template>
