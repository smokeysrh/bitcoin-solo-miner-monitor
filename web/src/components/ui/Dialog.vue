<script setup lang="ts">
import { DialogClose, DialogContent, DialogDescription, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import { X } from 'lucide-vue-next'
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/cn'

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
    /** show as a side sheet instead of a centred dialog */
    side?: boolean
    hideTitle?: boolean
    dismissible?: boolean
    class?: HTMLAttributes['class']
  }>(),
  { size: 'md', dismissible: true },
)
const open = defineModel<boolean>('open', { default: false })

const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl', '2xl': 'max-w-6xl' } as const

function guard(e: Event): void {
  if (!props.dismissible) e.preventDefault()
}
</script>

<template>
  <DialogRoot v-model:open="open">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 animate-fade-in bg-overlay backdrop-blur-sm" />
      <DialogContent
        :class="
          cn(
            'fixed z-50 flex flex-col overflow-hidden bg-surface-1 text-fg shadow-pop outline-none',
            side
              ? 'inset-y-0 right-0 w-full animate-slide-in-right border-l border-line sm:rounded-l-2xl ' + widths[size]
              : 'top-1/2 left-1/2 max-h-[88dvh] w-[calc(100vw-1.5rem)] -translate-x-1/2 -translate-y-1/2 animate-pop-in rounded-2xl border border-line ' + widths[size],
            props.class,
          )
        "
        @interact-outside="guard"
        @escape-key-down="guard"
      >
        <header class="flex items-start justify-between gap-4 border-b border-line px-5 py-4" :class="hideTitle && 'sr-only'">
          <div class="min-w-0">
            <DialogTitle class="text-base font-semibold text-fg">{{ title }}</DialogTitle>
            <DialogDescription :class="description ? 'mt-1 text-sm text-muted' : 'sr-only'">{{ description ?? title }}</DialogDescription>
          </div>
          <DialogClose
            v-if="dismissible"
            class="-mr-1.5 grid size-8 shrink-0 place-items-center rounded-lg text-subtle transition-colors hover:bg-surface-3 hover:text-fg"
            aria-label="Close"
          >
            <X class="size-4" />
          </DialogClose>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="flex flex-wrap items-center justify-end gap-2 border-t border-line bg-surface-2/60 px-5 py-3">
          <slot name="footer" />
        </footer>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
