<script setup lang="ts">
import { TooltipContent, TooltipPortal, TooltipRoot, TooltipTrigger } from 'reka-ui'

withDefaults(defineProps<{ text?: string; side?: 'top' | 'right' | 'bottom' | 'left'; delay?: number }>(), { side: 'top', delay: 250 })
</script>

<template>
  <TooltipRoot :delay-duration="delay">
    <TooltipTrigger as-child><slot /></TooltipTrigger>
    <TooltipPortal>
      <TooltipContent
        :side="side"
        :side-offset="6"
        class="z-[70] max-w-xs animate-pop-in rounded-lg border border-line-strong bg-surface-3 px-2.5 py-1.5 text-xs leading-snug text-fg shadow-pop"
      >
        <slot name="content">{{ text }}</slot>
      </TooltipContent>
    </TooltipPortal>
  </TooltipRoot>
</template>
