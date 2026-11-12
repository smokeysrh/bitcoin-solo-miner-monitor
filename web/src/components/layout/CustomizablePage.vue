<script setup lang="ts">
import { Check, ChevronLeft, ChevronRight, EyeOff, GripVertical, Pencil, Plus, RotateCcw } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { useLayoutEditor } from '@/composables/useLayoutEditor'
import { describeError } from '@/lib/api'
import { resolvePageLayout, type PageCard, type PageKey } from '@/lib/pageLayout'
import type { PageLayout } from '@/lib/types'
import { useSession } from '@/stores/session'
import { useSettings, type SettingsPatch } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'
import Button from '@/components/ui/Button.vue'

/**
 * A page whose cards can be reordered and hidden, like the Dashboard. The page supplies a slot per card id (plus
 * `heading`, optional `actions` and `aside`); the layout is saved per page in `ui.<pageKey>`.
 */
const props = defineProps<{
  pageKey: PageKey
  cards: PageCard[]
  /** Tailwind classes of the card grid. */
  gridClass: string
  /** Tailwind classes of the element around the grid and the optional `aside` slot. */
  wrapClass?: string
}>()

interface Placement {
  id: string
}

const settings = useSettings()
const session = useSession()
const toasts = useToasts()

const card = (id: string): PageCard | undefined => props.cards.find((c) => c.id === id)
const root = ref<HTMLElement | null>(null)
const { draft, announcement, begin, hide, append, move } = useLayoutEditor<Placement>((id) => card(id)?.title ?? id, root)
const editing = ref(false)
const saving = ref(false)

// Layouts are saved with PATCH /settings, which needs admin rights; a control token would only get a 403.
const canEdit = computed(() => session.canAdmin)
const saved = computed(() => resolvePageLayout(settings.data?.ui[props.pageKey], props.cards))
// What is on screen: the draft while editing, the saved layout otherwise.
const shown = computed(() => (editing.value ? draft.value.map((p) => p.id) : saved.value).flatMap((id) => card(id) ?? []))
const tray = computed(() => props.cards.filter((c) => !draft.value.some((p) => p.id === c.id)))

function layoutPatch(layout: PageLayout | null): SettingsPatch {
  return props.pageKey === 'bitcoin_page' ? { ui: { bitcoin_page: layout } } : { ui: { odds_page: layout } }
}

function startEdit(): void {
  begin(saved.value.map((id) => ({ id })))
  editing.value = true
}

async function finish(): Promise<void> {
  saving.value = true
  try {
    await settings.patch(layoutPatch({ version: 1, cards: draft.value.map((p) => p.id) }))
    editing.value = false
    toasts.success('Layout saved')
  } catch (e) {
    toasts.error('Could not save the layout', describeError(e))
  } finally {
    saving.value = false
  }
}

async function reset(): Promise<void> {
  try {
    await settings.patch(layoutPatch(null))
    draft.value = props.cards.map((c) => ({ id: c.id }))
    toasts.success('Back to the default layout')
  } catch (e) {
    toasts.error('Could not reset the layout', describeError(e))
  }
}
</script>

<template>
  <div ref="root" class="space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div class="min-w-0"><slot name="heading" /></div>
      <div class="flex flex-wrap items-center gap-2">
        <slot name="actions" />
        <template v-if="canEdit">
          <Button v-if="!editing" variant="ghost" size="sm" data-testid="customize" @click="startEdit">
            <template #icon><Pencil class="size-4" /></template>
            Customize
          </Button>
          <template v-else>
            <Button variant="ghost" size="sm" @click="reset">
              <template #icon><RotateCcw class="size-4" /></template>
              Reset
            </Button>
            <Button variant="primary" size="sm" :loading="saving" data-testid="customize-done" @click="finish">
              <template #icon><Check class="size-4" /></template>
              Done
            </Button>
          </template>
        </template>
      </div>
    </header>

    <p v-if="editing" class="rounded-xl border border-accent-line bg-accent-soft px-4 py-3 text-sm text-accent-text" role="status">
      Drag a card by its handle, or use the arrow buttons to move it earlier or later. Hide what you do not need. Press Done to save.
    </p>
    <p v-if="editing" class="sr-only" role="status" aria-live="polite" data-testid="reorder-announcement">{{ announcement }}</p>

    <div :class="wrapClass">
      <VueDraggable
        v-if="editing"
        v-model="draft"
        :animation="180"
        handle=".drag-handle"
        filter=".no-drag"
        :prevent-on-filter="false"
        :delay="140"
        :delay-on-touch-only="true"
        ghost-class="opacity-40"
        :class="gridClass"
      >
        <div v-for="(p, index) in draft" :key="p.id" :class="['relative min-h-[84px] min-w-0', card(p.id)?.cell]">
          <!-- inert: the preview is a picture while editing, so Tab and assistive tech only meet the editing controls -->
          <div inert class="pointer-events-none h-full"><slot :name="p.id" /></div>
          <div class="drag-handle absolute inset-0 z-10 flex cursor-grab items-start justify-between rounded-[var(--radius-card)] bg-bg/40 p-2.5 ring-2 ring-accent/50 backdrop-blur-[1px] active:cursor-grabbing">
            <span class="inline-flex items-center gap-1.5 rounded-lg bg-surface-3 px-2 py-1.5 text-xs font-medium text-fg shadow">
              <GripVertical class="size-4 text-muted" aria-hidden="true" /> {{ card(p.id)?.title }}
            </span>
            <span class="no-drag flex gap-1.5">
              <button
                class="grid size-8 place-items-center rounded-lg bg-surface-3 text-fg shadow hover:bg-surface-2 disabled:opacity-40 disabled:hover:bg-surface-3"
                :aria-label="`Move ${card(p.id)?.title} earlier`"
                :data-move="`${p.id}:earlier`"
                :disabled="index === 0"
                @click="move(p.id, 'earlier')"
              >
                <ChevronLeft class="size-4" aria-hidden="true" />
              </button>
              <button
                class="grid size-8 place-items-center rounded-lg bg-surface-3 text-fg shadow hover:bg-surface-2 disabled:opacity-40 disabled:hover:bg-surface-3"
                :aria-label="`Move ${card(p.id)?.title} later`"
                :data-move="`${p.id}:later`"
                :disabled="index === draft.length - 1"
                @click="move(p.id, 'later')"
              >
                <ChevronRight class="size-4" aria-hidden="true" />
              </button>
              <button
                class="grid size-8 place-items-center rounded-lg bg-surface-3 text-fg shadow hover:bg-bad-soft hover:text-bad"
                :aria-label="`Hide ${card(p.id)?.title}`"
                @click="hide(p.id)"
              >
                <EyeOff class="size-4" aria-hidden="true" />
              </button>
            </span>
          </div>
        </div>
      </VueDraggable>

      <div v-else :class="gridClass" data-testid="page-grid">
        <div v-for="c in shown" :key="c.id" :class="['min-w-0 empty:hidden', c.cell]"><slot :name="c.id" /></div>
      </div>

      <aside v-if="$slots.aside" class="xl:sticky xl:top-24 xl:self-start"><slot name="aside" /></aside>
    </div>

    <p v-if="!editing && !shown.length" class="text-sm text-muted">
      Every card on this page is hidden.<template v-if="canEdit"> Use Customize to show them again.</template>
    </p>

    <section v-if="editing && tray.length" class="card p-[var(--pad-card)]" aria-label="Hidden cards">
      <h3 class="text-sm font-semibold text-fg">Hidden cards</h3>
      <ul class="mt-3 flex flex-wrap gap-2">
        <li v-for="c in tray" :key="c.id">
          <button
            class="flex items-center gap-2 rounded-xl border border-line bg-surface-2/60 px-3 py-2 text-sm font-medium text-fg transition-colors hover:border-accent-line hover:bg-accent-softer"
            :aria-label="`Show ${c.title}`"
            @click="append({ id: c.id })"
          >
            <Plus class="size-4 shrink-0 text-muted" aria-hidden="true" /> Show {{ c.title }}
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>
