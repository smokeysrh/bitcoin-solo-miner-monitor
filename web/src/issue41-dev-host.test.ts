// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Loads the real vite.config.ts fresh, so the environment it reads at import time is the one stubbed here.
async function loadServerConfig() {
  vi.resetModules()
  const mod = await import('../vite.config')
  return mod.default.server
}

beforeEach(() => {
  vi.stubEnv('BSMM_ALLOWED_HOSTS', '')
})

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('dev server Host check (issue #41)', () => {
  it('keeps LAN preview and does not accept every Host header', async () => {
    const server = await loadServerConfig()
    // `host: true` listens on every interface, so Vite's DNS-rebinding Host check must stay on.
    expect(server?.host).toBeTruthy()
    expect(server?.allowedHosts).not.toBe(true)
    expect(server?.allowedHosts).toEqual([])
  })

  it('allows only exact names listed in BSMM_ALLOWED_HOSTS', async () => {
    vi.stubEnv('BSMM_ALLOWED_HOSTS', ' Phone.Lan, ,miner.home ')
    const server = await loadServerConfig()
    expect(server?.allowedHosts).toEqual(['phone.lan', 'miner.home'])
  })
})
