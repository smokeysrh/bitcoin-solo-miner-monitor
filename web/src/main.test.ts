// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const startup = vi.hoisted(() => ({
  bootstrap: vi.fn<() => Promise<void>>(),
  loadSettings: vi.fn<() => Promise<void>>(),
  mount: vi.fn(),
}))

// Isolate UI/transport dependencies, not main.ts or its registration logic.
vi.mock('pinia', () => ({ createPinia: () => ({}) }))
vi.mock('vue', () => ({ createApp: () => ({ use: vi.fn(), mount: startup.mount }) }))
vi.mock('./App.vue', () => ({ default: {} }))
vi.mock('./router', () => ({ router: {} }))
vi.mock('./stores/session', () => ({ useSession: () => ({ state: 'ready', bootstrap: startup.bootstrap }) }))
vi.mock('./stores/settings', () => ({ useSettings: () => ({ load: startup.loadSettings, look: {} }) }))
vi.mock('./lib/theme', () => ({ applyLook: vi.fn() }))
vi.mock('./styles/main.css', () => ({}))

const register = vi.fn<() => Promise<void>>()
let page: { readyState: DocumentReadyState }
let events: EventTarget

beforeEach(() => {
  vi.resetModules()
  vi.resetAllMocks()
  vi.stubEnv('PROD', true)
  startup.bootstrap.mockResolvedValue(undefined)
  startup.loadSettings.mockResolvedValue(undefined)
  register.mockResolvedValue(undefined)
  page = { readyState: 'loading' }
  // Native EventTarget exercises one-shot listeners without automatic DOM-emulator load events.
  events = new EventTarget()
  vi.stubGlobal('document', page)
  vi.stubGlobal('window', events)
  vi.stubGlobal('navigator', { serviceWorker: { register } })
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected startup transport') }))
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function finishLoad() {
  page.readyState = 'complete'
  events.dispatchEvent(new Event('load'))
}

function expectRegisteredOnce() {
  expect(register).toHaveBeenCalledTimes(1)
  expect(register).toHaveBeenCalledWith('/sw.js')
}

describe('service-worker registration through actual main.ts startup', () => {
  it.each(['loading', 'interactive'] as const)('waits for load when startup finishes while %s', async (state) => {
    page.readyState = state
    await import('./main')
    expect(startup.mount).toHaveBeenCalledWith('#app')
    expect(register).not.toHaveBeenCalled()

    finishLoad()
    expectRegisteredOnce()
    finishLoad()
    expectRegisteredOnce()
  })

  it.each(['bootstrap', 'loadSettings'] as const)('registers when load fires during pending %s', async (step) => {
    let release!: () => void
    startup[step].mockReturnValue(new Promise<void>((resolve) => { release = resolve }))
    const boot = import('./main')
    try {
      await vi.waitFor(() => expect(startup[step]).toHaveBeenCalledTimes(1))
      expect(startup.mount).not.toHaveBeenCalled()
      finishLoad()
      expect(register).not.toHaveBeenCalled()
    } finally {
      release()
      await boot
    }

    expect(startup.mount).toHaveBeenCalledWith('#app')
    // No second load event: late startup must register as soon as it resumes.
    expectRegisteredOnce()
    finishLoad()
    expectRegisteredOnce()
  })

  it('registers when the document was already complete before startup', async () => {
    finishLoad()
    await import('./main')
    expectRegisteredOnce()
    finishLoad()
    expectRegisteredOnce()
  })

  it.each(['loading', 'complete'] as const)('does not register in development while %s', async (state) => {
    vi.stubEnv('PROD', false)
    page.readyState = state
    await import('./main')
    finishLoad()
    expect(startup.mount).toHaveBeenCalledWith('#app')
    expect(register).not.toHaveBeenCalled()
  })

  it.each(['loading', 'complete'] as const)('mounts without the browser service-worker API while %s', async (state) => {
    vi.stubGlobal('navigator', {})
    page.readyState = state
    await import('./main')
    finishLoad()
    expect(startup.mount).toHaveBeenCalledWith('#app')
    expect(register).not.toHaveBeenCalled()
  })

  it.each(['loading', 'complete'] as const)('keeps registration rejection nonfatal while %s', async (state) => {
    register.mockRejectedValue(new Error('Service worker unavailable'))
    page.readyState = state
    await import('./main')
    finishLoad()
    await Promise.resolve()
    expect(startup.mount).toHaveBeenCalledWith('#app')
    expectRegisteredOnce()
  })
})
