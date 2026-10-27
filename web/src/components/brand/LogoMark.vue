<script setup lang="ts">
import { useId } from 'vue'

defineProps<{ size?: number }>()
const gid = `logo-${useId()}`
</script>

<template>
  <svg :width="size ?? 32" :height="size ?? 32" viewBox="0 0 32 32" role="img" aria-label="Solo Miner Monitor logo" class="shrink-0">
    <defs>
      <linearGradient :id="gid" x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#FFB547" />
        <stop offset="0.55" stop-color="#F7931A" />
        <stop offset="1" stop-color="#E5600B" />
      </linearGradient>
    </defs>
    <path d="M16 2.2 27.2 8.6v12.8L16 27.8 4.8 21.4V8.6z" :fill="`url(#${gid})`" />
    <path d="M16 2.2 27.2 8.6v12.8L16 27.8 4.8 21.4V8.6z" fill="none" stroke="rgb(255 255 255 / 0.35)" stroke-width="0.8" />
    <path d="M17.6 8.5 11 17.2h4.1l-1 6.3 6.9-9.1h-4.3z" fill="#1b1203" fill-opacity="0.9" />
  </svg>
</template>
