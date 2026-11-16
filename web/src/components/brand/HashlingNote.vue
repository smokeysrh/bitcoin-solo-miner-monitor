<script setup lang="ts">
// Hashling with one of his lines next to him, for the places where he is page content and not a pop-up
// (setup, and the one joke on the Odds page). The pose and the words come from his moment (hashlingText.ts).
import { computed } from 'vue'
import { MOMENT_POSE } from '@/lib/hashlingMoments'
import { HASHLING_MOMENTS, type MomentId } from '@/lib/hashlingText'
import HashlingArt from './HashlingArt.vue'

const props = withDefaults(defineProps<{ moment: MomentId; scale?: number; as?: 'p' | 'h1' | 'h2'; centered?: boolean }>(), { scale: 2, as: 'p', centered: false })
const text = computed(() => HASHLING_MOMENTS[props.moment])
const TITLE_CLASS = {
  p: 'text-sm font-bold text-fg',
  h1: 'text-gradient-accent text-3xl font-bold tracking-tight',
  h2: 'text-2xl font-bold tracking-tight text-fg',
} as const
</script>

<template>
  <div :class="['flex gap-4', centered ? 'flex-col items-center text-center' : 'items-center']" :data-moment="moment">
    <HashlingArt :pose="MOMENT_POSE[moment]" :scale="scale" />
    <div class="min-w-0">
      <component :is="as" v-if="text.title" :class="TITLE_CLASS[as]">{{ text.title }}</component>
      <p :class="['text-sm leading-relaxed', as === 'p' ? 'text-muted' : 'mt-1 text-base text-muted']">{{ text.line }}</p>
    </div>
  </div>
</template>
