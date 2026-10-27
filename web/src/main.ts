import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { applyLook } from './lib/theme'
import { router } from './router'
import { useSession } from './stores/session'
import { useSettings } from './stores/settings'
import './styles/main.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// Find out who we are talking to (and whether a login is needed) before the router makes its first decision.
const session = useSession(pinia)
await session.bootstrap()
if (session.state === 'ready') {
  const settings = useSettings(pinia)
  try {
    await settings.load()
    applyLook(settings.look)
  } catch {
    /* defaults are fine; the app retries when it mounts */
  }
}

app.use(router)
app.mount('#app')

// Installable app + instant repeat loads. Never caches API calls (see public/sw.js).
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => undefined)
  })
}
