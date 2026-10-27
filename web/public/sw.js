// Makes the dashboard installable and quick to reopen. It never caches API data:
// what you see about your miners always comes live from the server.
const CACHE = 'bsmm-shell-v1'
const LIVE = /^\/(api|mcp|metrics|docs|openapi\.json|llms\.txt)/

self.addEventListener('install', () => self.skipWaiting())

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) if (key !== CACHE) await caches.delete(key)
      await self.clients.claim()
    })(),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  const url = new URL(req.url)
  if (req.method !== 'GET' || url.origin !== self.location.origin || LIVE.test(url.pathname)) return

  // built files have a content hash in their name, so a cached copy is always correct
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {
        const hit = await cache.match(req)
        if (hit) return hit
        const res = await fetch(req)
        if (res.ok) cache.put(req, res.clone())
        return res
      }),
    )
    return
  }

  // pages: the network first (so a new release shows up), the last good copy when the server is unreachable
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) caches.open(CACHE).then((c) => c.put('/', res.clone()))
          return res
        })
        .catch(async () => (await caches.match('/')) ?? new Response('Solo Miner Monitor is not reachable right now.', { status: 503, headers: { 'Content-Type': 'text/plain' } })),
    )
  }
})
