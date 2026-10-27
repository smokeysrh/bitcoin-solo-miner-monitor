<script setup lang="ts">
import { AlertTriangle, CheckCircle2, Info, OctagonAlert, X } from 'lucide-vue-next'
import { useToasts, type ToastKind } from '@/stores/toasts'

const toasts = useToasts()
const icon = { info: Info, success: CheckCircle2, warning: AlertTriangle, error: OctagonAlert } as const
const tone: Record<ToastKind, string> = {
  info: 'text-info',
  success: 'text-ok',
  warning: 'text-warn',
  error: 'text-bad',
}
</script>

<template>
  <div
    class="pointer-events-none fixed inset-x-3 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-[80] flex flex-col items-end gap-2 lg:bottom-5 lg:left-auto lg:right-5"
    aria-live="polite"
    aria-atomic="false"
  >
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts.items"
        :key="t.id"
        :role="t.kind === 'error' ? 'alert' : 'status'"
        class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-line-strong bg-surface-2 p-3.5 shadow-pop"
      >
        <component :is="icon[t.kind]" :class="['mt-0.5 size-5 shrink-0', tone[t.kind]]" aria-hidden="true" />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-fg">{{ t.title }}</p>
          <p v-if="t.body" class="mt-0.5 text-xs leading-relaxed text-muted">{{ t.body }}</p>
          <button
            v-if="t.action"
            class="mt-2 text-xs font-medium text-accent-text underline underline-offset-2 hover:no-underline"
            @click="
              t.action.run();
              toasts.dismiss(t.id)
            "
          >
            {{ t.action.label }}
          </button>
        </div>
        <button class="-m-1 grid size-7 place-items-center rounded-md text-subtle hover:bg-surface-3 hover:text-fg" aria-label="Dismiss" @click="toasts.dismiss(t.id)">
          <X class="size-3.5" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(24px);
}
.toast-leave-active {
  position: absolute;
}
</style>
