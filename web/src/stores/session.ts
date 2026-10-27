import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, api, onUnauthorized } from '@/lib/api'
import type { Me, Meta, Scope } from '@/lib/types'

export type SessionState = 'loading' | 'ready' | 'login' | 'unreachable'

const RANK: Record<Scope, number> = { read: 0, control: 1, admin: 2 }

export const useSession = defineStore('session', () => {
  const meta = ref<Meta | null>(null)
  const me = ref<Me | null>(null)
  const state = ref<SessionState>('loading')
  const error = ref<string | null>(null)

  const scope = computed<Scope>(() => me.value?.scope ?? 'read')
  const can = (needed: Scope): boolean => RANK[scope.value] >= RANK[needed]
  const canControl = computed(() => can('control'))
  const canAdmin = computed(() => can('admin'))
  const authEnabled = computed(() => meta.value?.auth.mode === 'password')
  const readOnly = computed(() => state.value === 'ready' && !canControl.value)
  const demo = computed(() => meta.value?.demo ?? false)

  async function bootstrap(): Promise<void> {
    state.value = 'loading'
    error.value = null
    try {
      meta.value = await api.meta()
    } catch (e) {
      state.value = 'unreachable'
      error.value = e instanceof Error ? e.message : String(e)
      return
    }
    try {
      me.value = await api.me()
      state.value = 'ready'
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) state.value = 'login'
      else {
        state.value = 'unreachable'
        error.value = e instanceof Error ? e.message : String(e)
      }
    }
  }

  async function login(password: string): Promise<void> {
    await api.login(password)
    await bootstrap()
  }

  async function logout(): Promise<void> {
    try {
      await api.logout()
    } finally {
      me.value = null
      state.value = 'login'
    }
  }

  /** The server said 401 mid-session (expired cookie, password changed): go back to the login page. */
  function expire(): void {
    if (state.value === 'ready') state.value = 'login'
  }
  onUnauthorized((err) => {
    if (err.code === 'auth_required') expire()
  })

  async function refreshMeta(): Promise<void> {
    meta.value = await api.meta()
  }

  return { meta, me, state, error, scope, can, canControl, canAdmin, authEnabled, readOnly, demo, bootstrap, login, logout, expire, refreshMeta }
})
