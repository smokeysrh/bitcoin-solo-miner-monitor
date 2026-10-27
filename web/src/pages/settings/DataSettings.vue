<script setup lang="ts">
import { Download, Upload } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import { useFmt } from '@/composables/useFmt'
import { useSectionForm } from '@/composables/useSectionForm'
import { api, describeError } from '@/lib/api'
import { downloadText } from '@/lib/csv'
import type { SystemInfo } from '@/lib/types'
import { useSession } from '@/stores/session'
import { useToasts } from '@/stores/toasts'

const session = useSession()
const toasts = useToasts()
const fmt = useFmt()
const admin = computed(() => session.canAdmin)
const retention = useSectionForm('retention')
const info = ref<SystemInfo | null>(null)
const busy = ref<'export' | 'import' | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

onMounted(async () => {
  try {
    info.value = await api.systemInfo()
  } catch {
    info.value = null
  }
})

async function exportConfig(): Promise<void> {
  busy.value = 'export'
  try {
    const data = await api.exportConfig()
    downloadText(`bsmm-config-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(data, null, 2), 'application/json')
    toasts.success('Exported', 'Passwords and tokens are not included.')
  } catch (e) {
    toasts.error('Could not export', describeError(e))
  } finally {
    busy.value = null
  }
}

async function importFile(e: Event): Promise<void> {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  busy.value = 'import'
  try {
    const parsed = JSON.parse(await file.text()) as Record<string, unknown>
    const res = await api.importConfig(parsed)
    toasts.success('Imported', Object.entries(res.added).map(([k, n]) => `${n} ${k}`).join(', ') || res.note)
  } catch (err) {
    toasts.error('That file could not be imported', err instanceof SyntaxError ? 'It is not valid JSON.' : describeError(err))
  } finally {
    busy.value = null
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<template>
  <SettingsCard title="Back up" description="Everything lives in one small database on this computer: your miners, history, settings and rules.">
    <dl v-if="info" class="mb-5 grid gap-4 sm:grid-cols-3">
      <div><dt class="text-xs text-subtle">Database size</dt><dd class="tnum mt-1 text-lg font-semibold text-fg">{{ fmt.formatBytes(info.db_size_bytes) }}</dd></div>
      <div class="min-w-0 sm:col-span-2"><dt class="text-xs text-subtle">Stored in</dt><dd class="mt-1 truncate font-mono text-[13px] text-fg" :title="info.data_dir">{{ info.data_dir }}</dd></div>
    </dl>
    <div class="flex flex-wrap gap-2">
      <Button variant="secondary" href="/api/v1/system/backup" :disabled="!admin" download><template #icon><Download class="size-4" /></template>Download a full backup</Button>
    </div>
    <p class="mt-3 max-w-2xl text-xs leading-relaxed text-subtle">
      The backup keeps your passwords and tokens encrypted. To restore on another computer, copy the <code class="rounded bg-surface-3 px-1">secret.key</code> file from the folder above as well, otherwise saved secrets cannot be read.
    </p>
  </SettingsCard>

  <SettingsCard title="Move your setup" description="A portable list of your miners, settings, alert rules, channels and sources. Secrets are left out, so you will re-enter those.">
    <div class="flex flex-wrap gap-2">
      <Button variant="secondary" :loading="busy === 'export'" :disabled="!admin" @click="exportConfig"><template #icon><Download class="size-4" /></template>Export setup</Button>
      <Button variant="secondary" :loading="busy === 'import'" :disabled="!admin" @click="fileInput?.click()"><template #icon><Upload class="size-4" /></template>Import setup</Button>
      <input ref="fileInput" type="file" accept="application/json,.json" class="sr-only" aria-label="Choose a setup file to import" tabindex="-1" @change="importFile" />
    </div>
    <p class="mt-3 text-xs text-subtle">Importing adds what is missing and never overwrites miners you already have. Coming from the old version? Run <code class="rounded bg-surface-3 px-1">bsmm migrate-legacy</code> on the computer.</p>
  </SettingsCard>

  <SettingsCard
    title="How long to keep history"
    description="Charts use detailed data for recent time and averages for older time. Longer keeps more but uses more disk. The defaults are small."
    show-save
    :dirty="retention.dirty.value"
    :saving="retention.saving.value"
    :error="retention.error.value"
    @save="retention.save()"
    @discard="retention.discard()"
  >
    <div class="grid gap-5 sm:grid-cols-2">
      <Field label="Every reading" hint="Highest detail."><template #default="{ id, describedBy }"><Input :id="id" v-model="retention.form.raw_days" type="number" :min="0.5" suffix="days" :described-by="describedBy" :disabled="!admin" /></template></Field>
      <Field label="Per minute"><template #default="{ id }"><Input :id="id" v-model="retention.form.minute_days" type="number" :min="1" suffix="days" :disabled="!admin" /></template></Field>
      <Field label="Per hour"><template #default="{ id }"><Input :id="id" v-model="retention.form.hour_days" type="number" :min="1" suffix="days" :disabled="!admin" /></template></Field>
      <Field label="Activity log"><template #default="{ id }"><Input :id="id" v-model="retention.form.event_days" type="number" :min="1" suffix="days" :disabled="!admin" /></template></Field>
    </div>
  </SettingsCard>
</template>
