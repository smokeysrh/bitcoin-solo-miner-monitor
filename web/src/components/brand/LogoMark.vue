<script setup lang="ts">
// The supplied HashHurdr symbol (the full-body Hashling), used exactly as drawn. It is pixel art on a 32 x 32 grid,
// so pass whole-number multiples of 32 for `size` to keep every pixel sharp. Pass alt="" when the name is written next to it.
withDefaults(defineProps<{ size?: number; alt?: string }>(), { size: 32, alt: 'HashHurdr logo' })
</script>

<template>
  <img src="/brand/hashhurdr-symbol.svg" :width="size" :height="size" :alt="alt" class="shrink-0" />
</template>
