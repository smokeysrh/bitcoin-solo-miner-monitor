<script setup lang="ts">
// Hashling's pop-up, one at a time, on the dashboard (top right, small) and on the wall display (bottom centre, large
// enough to read from across a room). It uses the toaster's tones and live-region roles. It never takes focus, goes
// away by itself, can be dismissed by button or Escape, and holds still for reduced motion.
import { useEventListener, useWindowSize } from '@vueuse/core'
import { X } from 'lucide-vue-next'
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import HashlingArt from '@/components/brand/HashlingArt.vue'
import { fill, HASHLING_UI } from '@/lib/hashlingText'
import type { Tone } from '@/lib/hashlingMoments'
import { prefersReducedMotion } from '@/lib/motion'
import { useHashling } from '@/stores/hashling'
import { useSettings } from '@/stores/settings'

const hashling = useHashling()
const settings = useSettings()
const route = useRoute()
const { height } = useWindowSize()

const wall = computed(() => route.name === 'kiosk')
watch(wall, (w) => { hashling.surface = w ? 'wall' : 'dashboard' }, { immediate: true })
const item = computed(() => hashling.current)

// Whole-number scales of the 52 x 44 art. The wall display grows with the screen.
const DASHBOARD_SCALE = 3
const WALL_MIN_SCALE = 4
const WALL_SCREEN_PX_PER_STEP = 160
const scale = computed(() => (wall.value ? Math.max(WALL_MIN_SCALE, Math.floor(height.value / WALL_SCREEN_PX_PER_STEP)) : DASHBOARD_SCALE))

/** The device setting or the in-app switch asks for stillness. Read at each render, so a change applies to the next pop-up. */
const still = (): boolean => (settings.data?.ui.reduce_motion ?? false) || prefersReducedMotion()

const TONE_BORDER: Record<Tone, string> = { bad: 'border-bad/50', warn: 'border-warn/50', ok: 'border-ok/50', info: 'border-info/50' }

// Escape dismisses on the dashboard, unless a dialog or menu is open (it takes the key). On the wall display Escape leaves it.
useEventListener(window, 'keydown', (e: KeyboardEvent) => {
  if (e.key !== 'Escape' || e.defaultPrevented || wall.value || !hashling.current) return
  if (document.querySelector('[role="dialog"], [role="menu"], [role="listbox"]')) return
  hashling.dismiss()
})

// Hold the pop-up while it is being read (pointer or keyboard focus on it). Never on the wall display: nobody is there.
const hold = (): void => { if (!wall.value) hashling.hold() }
const release = (): void => { if (!wall.value) hashling.release() }
</script>

<template>
  <div
    :class="[
      'pointer-events-none fixed z-[85] flex',
      wall ? 'inset-x-0 bottom-[3vmin] justify-center px-[3vmin]' : 'inset-x-3 top-[4.5rem] flex-col items-end gap-2 lg:left-auto lg:right-5',
    ]"
    aria-live="polite"
    aria-atomic="false"
    data-testid="hashling-popups"
  >
    <div
      v-if="item"
      :key="item.id"
      :role="item.tone === 'bad' ? 'alert' : 'status'"
      :class="[
        'pointer-events-auto flex w-full animate-pop-in items-center border bg-surface-2 shadow-pop',
        TONE_BORDER[item.tone],
        wall ? 'max-w-[min(92vw,90rem)] gap-[2.5vmin] rounded-3xl border-2 p-[2.5vmin]' : 'max-w-sm gap-3 rounded-2xl p-3.5',
      ]"
      data-testid="hashling-popup"
      :data-moment="item.momentId"
      @mouseenter="hold"
      @mouseleave="release"
      @focusin="hold"
      @focusout="release"
    >
      <HashlingArt :pose="item.pose" :scale="scale" :class="!still() && item.pose !== 'sleeping' && 'hashling-hop'" />
      <div class="min-w-0 flex-1">
        <p :class="wall ? 'text-[clamp(1.75rem,3.4vw,9rem)] leading-tight font-bold text-fg' : 'text-sm font-bold text-fg'">{{ item.title }}</p>
        <p :class="wall ? 'mt-[1vmin] text-[clamp(1.25rem,2.4vw,8rem)] leading-snug text-muted' : 'mt-0.5 text-xs leading-relaxed text-muted'">{{ item.line }}</p>
        <p v-if="hashling.waiting > 0" :class="wall ? 'mt-[1vmin] text-[clamp(1rem,1.6vw,5rem)] text-subtle' : 'mt-1 text-[11px] text-subtle'" data-testid="hashling-more">{{ fill(HASHLING_UI.U05, { count: hashling.waiting }) }}</p>
      </div>
      <button
        type="button"
        :class="['grid shrink-0 place-items-center self-start rounded-md text-subtle hover:bg-surface-3 hover:text-fg', wall ? 'size-[clamp(2.75rem,3vw,6rem)]' : '-m-1 size-7']"
        :aria-label="HASHLING_UI.U04"
        @click="hashling.dismiss()"
      >
        <X :class="wall ? 'size-[60%]' : 'size-3.5'" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
