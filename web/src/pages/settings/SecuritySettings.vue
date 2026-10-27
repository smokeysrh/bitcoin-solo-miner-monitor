<script setup lang="ts">
import { KeyRound, Plus, ShieldCheck, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import SettingsCard from '@/components/settings/SettingsCard.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import Dialog from '@/components/ui/Dialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import ToggleRow from '@/components/ui/ToggleRow.vue'
import { confirmDialog } from '@/composables/useConfirm'
import { useFmt } from '@/composables/useFmt'
import { api, describeError } from '@/lib/api'
import type { ApiToken, CreatedToken, Scope } from '@/lib/types'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'

const session = useSession()
const settings = useSettings()
const toasts = useToasts()
const fmt = useFmt()

const admin = computed(() => session.canAdmin)
const protectedNow = computed(() => settings.data?.auth.mode === 'password')

// ---- password
const pw = reactive({ current: '', next: '', again: '' })
const pwBusy = ref(false)
const pwError = ref<string | null>(null)
const hasPassword = computed(() => session.meta?.auth.password_set ?? false)

async function savePassword(): Promise<void> {
  pwError.value = null
  if (pw.next.length < 8) return void (pwError.value = 'Use at least 8 characters.')
  if (pw.next !== pw.again) return void (pwError.value = 'The two passwords are different.')
  pwBusy.value = true
  try {
    await api.setPassword({ new_password: pw.next, current_password: hasPassword.value ? pw.current : undefined, enable: true })
    toasts.success(hasPassword.value ? 'Password changed' : 'Password set', 'The dashboard now asks for it.')
    Object.assign(pw, { current: '', next: '', again: '' })
    await Promise.all([session.refreshMeta(), settings.load()])
  } catch (e) {
    pwError.value = describeError(e)
  } finally {
    pwBusy.value = false
  }
}

async function turnOff(): Promise<void> {
  const ok = await confirmDialog({
    title: 'Remove password protection?',
    message: 'Anyone who can reach this page, on your network, will be able to restart your miners and change their pools.',
    confirmLabel: 'Remove protection',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await settings.patch({ auth: { mode: 'none' } })
    await session.refreshMeta()
  } catch (e) {
    toasts.error('Could not change that', describeError(e))
  }
}

async function setPublicRead(on: boolean): Promise<void> {
  try {
    await settings.patch({ auth: { public_read: on } })
  } catch (e) {
    toasts.error('Could not change that', describeError(e))
  }
}

// ---- tokens
const tokens = ref<ApiToken[]>([])
const tokenDialog = ref(false)
const created = ref<CreatedToken | null>(null)
const tokenForm = reactive<{ name: string; scope: Scope; days: number | null }>({ name: '', scope: 'read', days: null })
const tokenBusy = ref(false)
const tokenError = ref<string | null>(null)

async function loadTokens(): Promise<void> {
  try {
    tokens.value = await api.tokens()
  } catch {
    tokens.value = []
  }
}
onMounted(() => void loadTokens())

async function createToken(): Promise<void> {
  tokenError.value = null
  if (!tokenForm.name.trim()) return void (tokenError.value = 'Give it a name so you recognise it later, for example “Claude on my laptop”.')
  tokenBusy.value = true
  try {
    created.value = await api.createToken({ name: tokenForm.name.trim(), scope: tokenForm.scope, expires_days: tokenForm.days })
    await loadTokens()
  } catch (e) {
    tokenError.value = describeError(e)
  } finally {
    tokenBusy.value = false
  }
}
function openCreate(): void {
  Object.assign(tokenForm, { name: '', scope: 'read', days: null })
  created.value = null
  tokenError.value = null
  tokenDialog.value = true
}
async function revoke(t: ApiToken): Promise<void> {
  if (!(await confirmDialog({ title: `Revoke “${t.name}”?`, message: 'Anything using this token stops working immediately.', confirmLabel: 'Revoke', tone: 'danger' }))) return
  try {
    await api.deleteToken(t.id)
    await loadTokens()
  } catch (e) {
    toasts.error('Could not revoke it', describeError(e))
  }
}
const scopeHelp: Record<Scope, string> = {
  read: 'Can look at everything but change nothing. Safest for dashboards and most agents.',
  control: 'Can also restart, pause and change pools on miners. Still cannot change settings.',
  admin: 'Can do everything, including settings and creating other tokens.',
}
</script>

<template>
  <SettingsCard title="Password" description="Without one, anyone on your network who opens this page can control your miners. A password takes ten seconds.">
    <div class="mb-5 flex flex-wrap items-center gap-3">
      <Badge :tone="protectedNow ? 'ok' : 'warn'" dot>{{ protectedNow ? 'Password protected' : 'Open to your network' }}</Badge>
      <Button v-if="protectedNow && admin" variant="ghost" size="sm" @click="turnOff">Remove protection</Button>
    </div>
    <form class="grid max-w-xl gap-4" @submit.prevent="savePassword">
      <Field v-if="hasPassword" label="Current password"><template #default="{ id }"><Input :id="id" v-model="pw.current" type="password" autocomplete="current-password" :disabled="!admin" /></template></Field>
      <Field :label="hasPassword ? 'New password' : 'Choose a password'" hint="At least 8 characters. A few random words is great."><template #default="{ id, describedBy }"><Input :id="id" v-model="pw.next" type="password" autocomplete="new-password" :described-by="describedBy" :disabled="!admin" data-testid="new-password" /></template></Field>
      <Field label="Repeat it"><template #default="{ id }"><Input :id="id" v-model="pw.again" type="password" autocomplete="new-password" :disabled="!admin" /></template></Field>
      <p v-if="pwError" class="text-sm text-bad" role="alert">{{ pwError }}</p>
      <div><Button type="submit" variant="primary" :loading="pwBusy" :disabled="!admin">{{ hasPassword ? 'Change password' : 'Set password' }}</Button></div>
    </form>
  </SettingsCard>

  <SettingsCard v-if="protectedNow" title="Read-only visitors" description="Handy for a TV or a family member: they can look but never change anything.">
    <ToggleRow :model-value="settings.data?.auth.public_read ?? false" :disabled="!admin" title="Let anyone on the network view the dashboard" description="No sign-in needed to look. Changing anything still needs the password." @update:model-value="setPublicRead" />
  </SettingsCard>

  <SettingsCard title="API tokens" description="Give an AI agent, a script or Home Assistant its own key instead of sharing your password. Each token has a limited power and can be revoked.">
    <div class="mb-4 flex justify-end"><Button v-if="admin" variant="secondary" size="sm" data-testid="new-token" @click="openCreate"><template #icon><Plus class="size-4" /></template>New token</Button></div>
    <ul v-if="tokens.length" class="divide-y divide-line rounded-xl border border-line" data-testid="token-list">
      <li v-for="t in tokens" :key="t.id" class="flex flex-wrap items-center gap-3 px-4 py-3">
        <KeyRound class="size-4 shrink-0 text-muted" aria-hidden="true" />
        <div class="min-w-0 flex-1 basis-48">
          <p class="text-sm font-medium text-fg">{{ t.name }}</p>
          <p class="text-xs text-subtle">Created {{ fmt.formatAgo(t.created_at) }} · {{ t.last_used_at ? `last used ${fmt.formatAgo(t.last_used_at)}` : 'never used' }}<template v-if="t.expires_at"> · expires {{ fmt.formatDate(t.expires_at) }}</template></p>
        </div>
        <Badge :tone="t.scope === 'admin' ? 'bad' : t.scope === 'control' ? 'warn' : 'info'" size="sm">{{ t.scope }}</Badge>
        <Button v-if="admin" size="iconSm" variant="ghost" :aria-label="`Revoke ${t.name}`" @click="revoke(t)"><Trash2 class="size-4" /></Button>
      </li>
    </ul>
    <EmptyState v-else compact :icon="ShieldCheck" title="No tokens yet" description="Create one when you want to connect an AI agent or a script." />
    <p class="mt-4 text-xs text-subtle">Prefer the command line? <code class="rounded bg-surface-3 px-1.5 py-0.5">bsmm token create --scope read</code></p>
  </SettingsCard>

  <Dialog v-model:open="tokenDialog" :title="created ? 'Copy your token now' : 'New API token'" :description="created ? undefined : 'Choose how much this token may do.'" size="md">
    <div v-if="created" class="space-y-4">
      <p class="rounded-xl border border-warn/30 bg-warn-soft px-4 py-3 text-sm text-warn">This is the only time it is shown. Store it somewhere safe, like a password manager.</p>
      <CodeBlock :code="created.token" label="Token" />
      <CodeBlock :code="created.usage" label="How to use it" />
    </div>
    <form v-else class="space-y-4" @submit.prevent="createToken">
      <Field label="Name"><template #default="{ id }"><Input :id="id" v-model="tokenForm.name" placeholder="Claude on my laptop" data-testid="token-name" /></template></Field>
      <Field label="Power" :hint="scopeHelp[tokenForm.scope]">
        <template #default="{ id, describedBy }"><Select :id="id" v-model="tokenForm.scope" :described-by="describedBy" :options="[{ value: 'read', label: 'Read only' }, { value: 'control', label: 'Read and control miners' }, { value: 'admin', label: 'Full access' }]" /></template>
      </Field>
      <Field label="Expires after (days)" hint="Leave empty for no expiry."><template #default="{ id }"><Input :id="id" v-model="tokenForm.days" type="number" :min="1" :max="3650" suffix="days" /></template></Field>
      <p v-if="tokenError" class="text-sm text-bad" role="alert">{{ tokenError }}</p>
    </form>
    <template #footer>
      <Button v-if="created" variant="primary" @click="tokenDialog = false">Done</Button>
      <template v-else>
        <Button variant="ghost" @click="tokenDialog = false">Cancel</Button>
        <Button variant="primary" :loading="tokenBusy" data-testid="token-create" @click="createToken">Create token</Button>
      </template>
    </template>
  </Dialog>
</template>
