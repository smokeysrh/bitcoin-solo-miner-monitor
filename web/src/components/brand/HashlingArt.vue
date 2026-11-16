<script setup lang="ts">
// One of Hashling's kit poses, drawn exactly as supplied. The art is pixel art on a 52 x 44 grid, so it is scaled by
// whole numbers only and the browser is told not to smooth it (.hashling-art in main.css). The alt text is Becky's
// (U01a to U01g) unless the caller passes its own.
import { computed } from 'vue'
import { HASHLING_ART, HASHLING_GRID, type HashlingPose } from '@/lib/brand'
import { poseAlt } from '@/lib/hashlingMoments'

const props = withDefaults(defineProps<{ pose: HashlingPose; scale?: number; alt?: string }>(), { scale: 2 })
const k = computed(() => Math.max(1, Math.round(props.scale)))
</script>

<template>
  <img :src="HASHLING_ART[pose]" :width="HASHLING_GRID.width * k" :height="HASHLING_GRID.height * k" :alt="alt ?? poseAlt(pose)" class="hashling-art shrink-0" draggable="false" />
</template>
