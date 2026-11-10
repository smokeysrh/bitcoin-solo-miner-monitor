import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { cancelPendingRequests, onUnauthorized } from '@/lib/api'
import { useSession } from '@/stores/session'
import SourcesSettings from './SourcesSettings.vue'

const SAVED_URL = 'http://192.168.1.10:8332'
const SAVED_COOKIE = '/fixture/node/.cookie'
const OTHER_HOST_URL = 'http://203.0.113.9:8332'
const NEW_COOKIE = '/fixture/other-node/.cookie'
const SOURCE = {
  id: 'fixture-node', kind: 'bitcoin_core', name: 'Home node', url: SAVED_URL, enabled: true,
  options: { cookie_path: SAVED_COOKIE }, has_secret: false, created_at: 1, health: null,
}
const KIND = {
  kind: 'bitcoin_core', label: 'Bitcoin Core', title: 'Bitcoin Core node (RPC)', url_example: 'http://umbrel.local:8332',
  secret_fields: [{ name: 'rpc_user', label: 'RPC user name' }, { name: 'rpc_password', label: 'RPC password', secret: true }],
  option_fields: [{ name: 'cookie_path', label: 'Cookie file (alternative to user/password, same computer only)' }],
  gives: [], where_to_find_login: '',
}

interface Sent { method: string; path: string; body: { url?: string | null; options?: Record<string, unknown> } | null }
let sent: Sent[] = []
let wrapper: ReturnType<typeof mount> | undefined

function respond(method: string, path: string): unknown {
  if (method === 'GET' && path === '/sources/kinds') return { kinds: [KIND] }
  if (method === 'GET' && path === '/sources') return { sources: [SOURCE], implicit: [] }
  if (method === 'POST' && path === '/sources/test') return { ok: true, message: 'Connected', details: {}, hints: [] }
  if (method === 'PATCH' && path === `/sources/${SOURCE.id}`) return { source: SOURCE }
  throw new Error(`Unexpected transport: ${method} ${path}`)
}

beforeEach(() => {
  setActivePinia(createPinia())
  sent = []
  vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const path = new URL(url, 'http://localhost').pathname.replace(/^\/api\/v1/, '')
    sent.push({ method, path, body: typeof init?.body === 'string' ? JSON.parse(init.body) : null })
    return Promise.resolve(new Response(JSON.stringify(respond(method, path)), { status: 200 }))
  }))
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  cancelPendingRequests(); onUnauthorized(null)
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

async function openEditor() {
  const session = useSession()
  session.state = 'ready'; session.me = { name: 'admin', scope: 'admin', via: 'session' }
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  // Render the dialog inline so the form can be found without a portal.
  const Dialog = { props: ['open'], template: '<div v-if="open"><slot /><slot name="footer" /></div>' }
  wrapper = mount(SourcesSettings, { global: { plugins: [router], stubs: { Dialog } } })
  await flushPromises()
  await wrapper.get('[aria-label="Edit Home node"]').trigger('click')
  await flushPromises()
  return wrapper
}
function cookieInput(w: ReturnType<typeof mount>) {
  const label = w.findAll('label').find((l) => l.text().startsWith('Cookie file'))!
  return w.get(`input#${label.attributes('for')}`)
}
async function setAddress(w: ReturnType<typeof mount>, url: string) {
  await w.get('[data-testid="source-url"]').setValue(url)
}
async function clickTest(w: ReturnType<typeof mount>) {
  await w.get('[data-testid="source-test-btn"]').trigger('click')
  await flushPromises()
}
const posted = (path: string) => sent.filter((s) => s.method !== 'GET' && s.path === path)

describe('editing a saved node keeps its cookie file with that node', () => {
  it('shows the saved cookie file in the edit form', async () => {
    const w = await openEditor()
    expect((cookieInput(w).element as HTMLInputElement).value).toBe(SAVED_COOKIE)
  })

  it('does not send the saved cookie file to a changed host when testing', async () => {
    const w = await openEditor()
    await setAddress(w, OTHER_HOST_URL)
    await clickTest(w)
    const tests = posted('/sources/test')
    expect(tests).toHaveLength(1)
    expect(tests[0]!.body!.url).toBe(OTHER_HOST_URL)
    expect(tests[0]!.body!.options?.cookie_path).toBeUndefined()
    expect(JSON.stringify(sent)).not.toContain(SAVED_COOKIE)
  })

  it('does not send the saved cookie file to a changed host when saving', async () => {
    const w = await openEditor()
    await setAddress(w, OTHER_HOST_URL)
    await w.get('[data-testid="source-save"]').trigger('click')
    await flushPromises()
    const saves = posted(`/sources/${SOURCE.id}`)
    expect(saves).toHaveLength(1)
    expect(saves[0]!.body!.options?.cookie_path).toBeUndefined()
  })

  it('still sends the saved cookie file when only the port changes', async () => {
    const w = await openEditor()
    await setAddress(w, 'http://192.168.1.10:18332')
    await clickTest(w)
    expect(posted('/sources/test')[0]!.body!.options?.cookie_path).toBe(SAVED_COOKIE)
  })

  it('still sends the saved cookie file when the address is changed back before testing', async () => {
    const w = await openEditor()
    await setAddress(w, OTHER_HOST_URL)
    await setAddress(w, SAVED_URL)
    await clickTest(w)
    expect(posted('/sources/test')[0]!.body!.options?.cookie_path).toBe(SAVED_COOKIE)
  })

  it('sends a cookie file the user enters for the new host', async () => {
    const w = await openEditor()
    await setAddress(w, OTHER_HOST_URL)
    await cookieInput(w).setValue(NEW_COOKIE)
    await clickTest(w)
    const body = posted('/sources/test')[0]!.body!
    expect(body.url).toBe(OTHER_HOST_URL)
    expect(body.options?.cookie_path).toBe(NEW_COOKIE)
    expect(JSON.stringify(sent)).not.toContain(SAVED_COOKIE)
  })
})
