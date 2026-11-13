// Makes the dashboard installable and quick to reopen. It never caches API data:
// what you see about your miners always comes live from the server.
// CacheStorage is shared by every app on this origin, so only names with our prefix are ours to delete.
const CACHE_PREFIX = 'bsmm-shell-'
const CACHE = `${CACHE_PREFIX}v2`
const LIVE = /^\/(api|mcp|metrics|docs|openapi\.json|llms\.txt)/

// Saving a copy is a bonus. The event waits for it, but a failure never breaks a page that loaded fine.
const remember = (event, key, res) =>
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.put(key, res))
      .catch((err) => console.warn('HashHurdr could not save a copy for offline use:', err)),
  )
const recall = (key) =>
  caches
    .open(CACHE)
    .then((cache) => cache.match(key))
    .catch(() => undefined)

self.addEventListener('install', () => self.skipWaiting())

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) if (key.startsWith(CACHE_PREFIX) && key !== CACHE) await caches.delete(key)
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
      (async () => {
        const hit = await recall(req)
        if (hit) return hit
        const res = await fetch(req)
        if (res.ok) remember(event, req, res.clone())
        return res
      })(),
    )
    return
  }

  // bundled fonts have no hash in their name, so like pages: the network first, the last good copy when the server is unreachable
  if (url.pathname.startsWith('/fonts/')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) remember(event, req, res.clone())
          return res
        })
        .catch(async (err) => {
          const hit = await recall(req)
          if (hit) return hit
          throw err
        }),
    )
    return
  }

  // pages: the network first (so a new release shows up), the last good copy when the server is unreachable
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) remember(event, '/', res.clone())
          return res
        })
        .catch(async () => (await recall('/')) ?? new Response('HashHurdr is not reachable right now.', { status: 503, headers: { 'Content-Type': 'text/plain' } })),
    )
  }
})
