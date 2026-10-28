<script setup lang="ts">
import { LockKeyhole } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/lib/api'
import { useSession } from '@/stores/session'
import LogoMark from '@/components/brand/LogoMark.vue'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'

const session = useSession()
const router = useRouter()
const route = useRoute()
const password = ref('')
const busy = ref(false)
const error = ref<string | null>(null)

async function submit(): Promise<void> {
  if (!password.value) {
    error.value = 'Enter the dashboard password.'
    return
  }
  busy.value = true
  error.value = null
  try {
    await session.login(password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') && !route.query.next.startsWith('//') ? route.query.next : '/'
    await router.replace(next)
  } catch (e) {
    error.value =
      e instanceof ApiError ? (e.status === 429 ? `${e.message} Wait a minute, then try again.` : e.code === 'bad_password' ? 'That password is not right.' : e.message) : 'Could not sign in.'
    password.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="grid min-h-dvh place-items-center p-4">
    <div class="w-full max-w-sm animate-fade-up">
      <div class="mb-8 flex flex-col items-center gap-3 text-center">
        <LogoMark :size="52" />
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-fg">Solo Miner Monitor</h1>
          <p class="mt-1 text-sm text-muted">{{ session.meta?.instance_name }}</p>
        </div>
      </div>
      <form class="card space-y-5 p-6" @submit.prevent="submit">
        <div class="flex items-center gap-3">
          <span class="grid size-10 place-items-center rounded-xl bg-accent-soft text-accent-text"><LockKeyhole class="size-5" aria-hidden="true" /></span>
          <div>
            <h2 class="text-base font-semibold text-fg">Sign in</h2>
            <p class="text-xs text-subtle">This dashboard is password protected.</p>
          </div>
        </div>
        <Field label="Password" :error="error">
          <template #default="{ id, describedBy, invalid }">
            <Input :id="id" v-model="password" type="password" :described-by="describedBy" :invalid="invalid" autocomplete="current-password" data-testid="login-password" />
          </template>
        </Field>
        <Button type="submit" variant="primary" size="lg" class="w-full" :loading="busy" data-testid="login-submit">Sign in</Button>
        <p class="text-center text-xs leading-relaxed text-subtle">
          Forgot it? On the computer running the app, run <code class="rounded bg-surface-3 px-1.5 py-0.5">bsmm password</code> to set a new one.
        </p>
      </form>
      <p v-if="session.error" class="mt-4 text-sm text-warn" role="alert">{{ session.error }}</p>
      <Button v-if="session.meta?.auth.public_read" class="mt-4 w-full" variant="ghost" @click="session.bootstrap().then(() => router.replace('/'))">Continue public monitoring</Button>
    </div>
  </main>
</template>
