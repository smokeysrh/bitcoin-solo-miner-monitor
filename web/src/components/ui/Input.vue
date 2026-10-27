<script setup lang="ts">
import { computed, ref, type HTMLAttributes } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import { cn } from '@/lib/cn'

// extra attributes (aria-label, data-testid, name...) belong on the <input>, not on the styled wrapper
defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    type?: string
    placeholder?: string
    prefix?: string
    suffix?: string
    mono?: boolean
    invalid?: boolean
    disabled?: boolean
    readonly?: boolean
    id?: string
    describedBy?: string
    autocomplete?: string
    min?: number
    max?: number
    step?: number | string
    size?: 'sm' | 'md'
    class?: HTMLAttributes['class']
  }>(),
  { type: 'text', size: 'md' },
)

// strings stay strings; <input type="number"> yields a number (or null when empty)
const model = defineModel<string | number | null>({ default: '' })
const reveal = ref(false)
const inputType = computed(() => (props.type === 'password' && reveal.value ? 'text' : props.type))

function onInput(e: Event): void {
  const el = e.target as HTMLInputElement
  if (props.type === 'number') {
    model.value = el.value === '' ? null : Number(el.value)
  } else {
    model.value = el.value
  }
}
</script>

<template>
  <div
    :class="
      cn(
        'group flex w-full items-center rounded-xl border bg-surface-2 transition-colors',
        'focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/25',
        invalid ? 'border-bad' : 'border-line hover:border-line-strong',
        disabled && 'opacity-55',
        size === 'sm' ? 'h-8' : 'h-10',
        props.class,
      )
    "
  >
    <span v-if="prefix" class="pl-3 text-sm text-subtle select-none">{{ prefix }}</span>
    <input
      v-bind="$attrs"
      :id="id"
      :type="inputType"
      :value="model ?? ''"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :autocomplete="autocomplete"
      :min="min"
      :max="max"
      :step="step"
      :aria-invalid="invalid || undefined"
      :aria-describedby="describedBy"
      :class="
        cn(
          'h-full min-w-0 flex-1 bg-transparent px-3 text-sm text-fg outline-none placeholder:text-subtle',
          mono && 'font-mono text-[13px]',
          type === 'number' && 'tnum',
        )
      "
      @input="onInput"
    />
    <span v-if="suffix" class="pr-3 text-sm text-subtle select-none">{{ suffix }}</span>
    <button
      v-if="type === 'password'"
      type="button"
      class="mr-1.5 grid size-7 place-items-center rounded-lg text-subtle hover:bg-surface-3 hover:text-fg"
      :aria-label="reveal ? 'Hide' : 'Show'"
      @click="reveal = !reveal"
    >
      <EyeOff v-if="reveal" class="size-4" />
      <Eye v-else class="size-4" />
    </button>
    <slot name="end" />
  </div>
</template>
