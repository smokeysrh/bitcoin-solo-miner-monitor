<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { pendingConfirm } from '@/composables/useConfirm'
import Button from './Button.vue'
import Dialog from './Dialog.vue'
import Input from './Input.vue'

const typed = ref('')
const open = computed({
  get: () => pendingConfirm.value !== null,
  set: (v: boolean) => {
    if (!v) settle(false)
  },
})
watch(pendingConfirm, () => (typed.value = ''))

const canConfirm = computed(() => !pendingConfirm.value?.typeToConfirm || typed.value.trim() === pendingConfirm.value.typeToConfirm)

function settle(ok: boolean): void {
  const p = pendingConfirm.value
  pendingConfirm.value = null
  p?.resolve(ok)
}
</script>

<template>
  <Dialog v-if="pendingConfirm" v-model:open="open" :title="pendingConfirm.title" :description="pendingConfirm.message" size="sm">
    <div v-if="pendingConfirm.typeToConfirm" class="space-y-2">
      <p class="text-sm text-muted">
        Type <code class="rounded bg-surface-3 px-1.5 py-0.5 text-fg">{{ pendingConfirm.typeToConfirm }}</code> to confirm.
      </p>
      <Input v-model="typed" autocomplete="off" @keydown.enter="canConfirm && settle(true)" />
    </div>
    <template #footer>
      <Button variant="ghost" @click="settle(false)">{{ pendingConfirm.cancelLabel ?? 'Cancel' }}</Button>
      <Button :variant="pendingConfirm.tone === 'danger' ? 'danger' : 'primary'" :disabled="!canConfirm" @click="settle(true)">
        {{ pendingConfirm.confirmLabel ?? 'Confirm' }}
      </Button>
    </template>
  </Dialog>
</template>
