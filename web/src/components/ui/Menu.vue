<script setup lang="ts">
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from 'reka-ui'
import type { Component } from 'vue'

export interface MenuItem {
  label?: string
  icon?: Component
  danger?: boolean
  disabled?: boolean
  separator?: boolean
  heading?: string
  run?: () => void
}

withDefaults(defineProps<{ items: MenuItem[]; align?: 'start' | 'center' | 'end' }>(), { align: 'end' })
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger as-child><slot /></DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent
        :align="align"
        :side-offset="6"
        class="z-[70] min-w-48 animate-pop-in rounded-xl border border-line-strong bg-surface-2 p-1.5 shadow-pop"
      >
        <template v-for="(it, i) in items" :key="i">
          <DropdownMenuSeparator v-if="it.separator" class="my-1 h-px bg-line" />
          <DropdownMenuLabel v-else-if="it.heading" class="px-2.5 pt-1.5 pb-1 text-[11px] font-semibold tracking-wide text-subtle uppercase">
            {{ it.heading }}
          </DropdownMenuLabel>
          <DropdownMenuItem
            v-else
            :disabled="it.disabled"
            :class="[
              'flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm outline-none select-none',
              'data-[highlighted]:bg-surface-3 data-[disabled]:pointer-events-none data-[disabled]:opacity-45',
              it.danger ? 'text-bad data-[highlighted]:bg-bad-soft' : 'text-fg',
            ]"
            @select="it.run?.()"
          >
            <component :is="it.icon" v-if="it.icon" class="size-4 shrink-0 opacity-80" aria-hidden="true" />
            {{ it.label }}
          </DropdownMenuItem>
        </template>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
