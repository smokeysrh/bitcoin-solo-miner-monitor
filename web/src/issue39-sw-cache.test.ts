// @vitest-environment node
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

// Runs the real web/public/sw.js against an in-memory CacheStorage. Nothing is copied from the worker.
const WORKER_SOURCE = readFileSync(fileURLToPath(new URL('../public/sw.js', import.meta.url)), 'utf8')
const ORIGIN = 'https://bsmm.test'
const CURRENT_CACHE = 'bsmm-shell-v2'
const PREVIOUS_CACHE = 'bsmm-shell-v1'
const OLD_OWNED_CACHE = 'bsmm-shell-v0'
const FONT_PATH = '/fonts/Inter-latin.woff2'
const FOREIGN_CACHE = 'other-app-offline'

type CacheKey = string | { url: string }
type Listener = (event: FakeEvent) => void

interface FakeEvent {
  request?: { method: string; url: string; mode: string }
  extended: Promise<unknown>[]
  responded?: Promise<Response>
  waitUntil: (work: Promise<unknown>) => void
  respondWith: (response: Promise<Response>) => void
}

const keyOf = (key: CacheKey) => (typeof key === 'string' ? key : key.url)

class FakeCache {
  entries = new Map<string, Response>()
  put = vi.fn<(key: CacheKey, res: Response) => Promise<void>>(async (key, res) => {
    this.entries.set(keyOf(key), res)
  })
  async match(key: CacheKey): Promise<Response | undefined> {
    return this.entries.get(keyOf(key))
  }
}

let spaces: Map<string, FakeCache>
let listeners: Map<string, Listener>
let failOpen: boolean
let network: Mock<(req: unknown) => Promise<Response>>

function installWorker() {
  const caches = {
    keys: async () => [...spaces.keys()],
    delete: async (name: string) => spaces.delete(name),
    open: async (name: string) => {
      if (failOpen) throw new Error('storage unavailable')
      let space = spaces.get(name)
      if (!space) {
        space = new FakeCache()
        spaces.set(name, space)
      }
      return space
    },
    match: async (key: CacheKey) => {
      for (const space of spaces.values()) {
        const hit = await space.match(key)
        if (hit) return hit
      }
      return undefined
    },
  }
  const scope = {
    location: { origin: ORIGIN },
    skipWaiting: vi.fn(),
    clients: { claim: vi.fn(async () => undefined) },
    addEventListener: (type: string, listener: Listener) => listeners.set(type, listener),
  }
  new Function('self', 'caches', 'fetch', WORKER_SOURCE)(scope, caches, network)
}

function makeEvent(request?: FakeEvent['request']): FakeEvent {
  const event: FakeEvent = {
    request,
    extended: [],
    waitUntil: (work) => {
      event.extended.push(work)
    },
    respondWith: (response) => {
      event.responded = response
    },
  }
  return event
}

function listener(type: string): Listener {
  const found = listeners.get(type)
  if (!found) throw new Error(`worker registered no ${type} listener`)
  return found
}

async function activate() {
  const event = makeEvent()
  listener('activate')(event)
  await Promise.all(event.extended)
}

async function fetchThroughWorker(path: string, mode: string) {
  const event = makeEvent({ method: 'GET', url: `${ORIGIN}${path}`, mode })
  listener('fetch')(event)
  if (!event.responded) throw new Error('worker did not handle the request')
  const response = await event.responded
  return { event, response }
}

const nextTurn = () => new Promise<void>((resolve) => setTimeout(resolve, 0))

function ownedCache() {
  const space = new FakeCache()
  spaces.set(CURRENT_CACHE, space)
  return space
}

beforeEach(() => {
  spaces = new Map()
  listeners = new Map()
  failOpen = false
  network = vi.fn<(req: unknown) => Promise<Response>>(async () => new Response('fresh', { status: 200 }))
  vi.spyOn(console, 'warn').mockImplementation(() => undefined)
  installWorker()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('service worker cache ownership', () => {
  it('removes only obsolete BSMM caches on activation', async () => {
    for (const name of [OLD_OWNED_CACHE, CURRENT_CACHE, FOREIGN_CACHE]) spaces.set(name, new FakeCache())
    await activate()
    expect([...spaces.keys()].sort()).toEqual([CURRENT_CACHE, FOREIGN_CACHE])
  })

  it('drops the previous release cache, which held no fonts, and keeps a foreign cache', async () => {
    for (const name of [PREVIOUS_CACHE, CURRENT_CACHE, FOREIGN_CACHE]) spaces.set(name, new FakeCache())
    await activate()
    expect(spaces.has(PREVIOUS_CACHE)).toBe(false)
    expect([...spaces.keys()].sort()).toEqual([CURRENT_CACHE, FOREIGN_CACHE])
  })
})

describe('service worker cache writes', () => {
  const cases = [
    { name: 'asset', path: '/assets/app-abc123.js', mode: 'cors', savedAs: `${ORIGIN}/assets/app-abc123.js` },
    { name: 'font', path: FONT_PATH, mode: 'cors', savedAs: `${ORIGIN}${FONT_PATH}` },
    { name: 'navigation', path: '/devices', mode: 'navigate', savedAs: '/' },
  ]

  it.each(cases)('keeps the $name cache write inside the event lifetime', async ({ path, mode }) => {
    const cache = ownedCache()
    let finishWrite: () => void = () => undefined
    cache.put.mockImplementationOnce(() => new Promise<void>((resolve) => { finishWrite = resolve }))

    const { event, response } = await fetchThroughWorker(path, mode)
    expect(response.status).toBe(200)
    expect(event.extended.length).toBeGreaterThan(0)

    let settled = false
    const lifetime = Promise.all(event.extended).then(() => { settled = true })
    await nextTurn()
    expect(settled).toBe(false)
    finishWrite()
    await lifetime
    expect(settled).toBe(true)
  })

  it.each(cases)('still answers an online $name request when the cache write fails', async ({ path, mode, savedAs }) => {
    const cache = ownedCache()
    cache.put.mockRejectedValueOnce(new Error('quota exceeded'))

    const { event, response } = await fetchThroughWorker(path, mode)
    expect(response.status).toBe(200)
    expect(await response.text()).toBe('fresh')
    expect(event.extended.length).toBeGreaterThan(0)
    await expect(Promise.all(event.extended)).resolves.toBeDefined()
    expect(cache.put).toHaveBeenCalledTimes(1)
    expect(keyOf(cache.put.mock.calls[0][0])).toBe(savedAs)
  })

  it.each(cases)('still answers an online $name request when the cache cannot be opened', async ({ path, mode }) => {
    failOpen = true
    const { event, response } = await fetchThroughWorker(path, mode)
    expect(response.status).toBe(200)
    expect(await response.text()).toBe('fresh')
    await expect(Promise.all(event.extended)).resolves.toBeDefined()
  })

  it('keeps serving the last saved page when the server is unreachable', async () => {
    const cache = ownedCache()
    cache.entries.set('/', new Response('saved page', { status: 200 }))
    network.mockRejectedValueOnce(new Error('offline'))

    const { response } = await fetchThroughWorker('/devices', 'navigate')
    expect(await response.text()).toBe('saved page')
  })
})

describe('service worker bundled fonts', () => {
  const fontKey = `${ORIGIN}${FONT_PATH}`

  it('answers a font request from the network and saves a copy in our cache', async () => {
    const cache = ownedCache()
    const { event, response } = await fetchThroughWorker(FONT_PATH, 'cors')
    expect(await response.text()).toBe('fresh')
    await Promise.all(event.extended)
    expect(network).toHaveBeenCalledTimes(1)
    expect(await (await cache.match(fontKey))?.text()).toBe('fresh')
  })

  it('prefers the network over an older saved font, since file names carry no hash', async () => {
    const cache = ownedCache()
    cache.entries.set(fontKey, new Response('old font', { status: 200 }))
    const { event, response } = await fetchThroughWorker(FONT_PATH, 'cors')
    expect(await response.text()).toBe('fresh')
    await Promise.all(event.extended)
    expect(await (await cache.match(fontKey))?.text()).toBe('fresh')
  })

  it('serves the saved font when the server is unreachable', async () => {
    const cache = ownedCache()
    cache.entries.set(fontKey, new Response('saved font', { status: 200 }))
    network.mockRejectedValueOnce(new Error('offline'))
    const { response } = await fetchThroughWorker(FONT_PATH, 'cors')
    expect(await response.text()).toBe('saved font')
  })

  it('does not save a failed font response', async () => {
    const cache = ownedCache()
    network.mockResolvedValueOnce(new Response('missing', { status: 404 }))
    const { event, response } = await fetchThroughWorker(FONT_PATH, 'cors')
    expect(response.status).toBe(404)
    await Promise.all(event.extended)
    expect(cache.put).not.toHaveBeenCalled()
  })

  it('passes the network error on when the server is unreachable and nothing was saved', async () => {
    ownedCache()
    network.mockRejectedValueOnce(new Error('offline'))
    const event = makeEvent({ method: 'GET', url: fontKey, mode: 'cors' })
    listener('fetch')(event)
    if (!event.responded) throw new Error('worker did not handle the request')
    await expect(event.responded).rejects.toThrow('offline')
  })
})
