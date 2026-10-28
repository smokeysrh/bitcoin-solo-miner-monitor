import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useSession } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    /** render without the app shell (login, wizard, kiosk) */
    bare?: boolean
    /** works without signing in */
    public?: boolean
  }
}

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'dashboard', component: () => import('@/pages/DashboardPage.vue'), meta: { title: 'Dashboard' } },
  { path: '/miners', name: 'miners', component: () => import('@/pages/MinersPage.vue'), meta: { title: 'Miners' } },
  { path: '/miners/:id', name: 'miner', component: () => import('@/pages/MinerDetailPage.vue'), meta: { title: 'Miner' }, props: true },
  { path: '/bitcoin', name: 'bitcoin', component: () => import('@/pages/BitcoinPage.vue'), meta: { title: 'Bitcoin network' } },
  { path: '/odds', name: 'odds', component: () => import('@/pages/OddsPage.vue'), meta: { title: 'Odds & costs' } },
  { path: '/analytics', name: 'analytics', component: () => import('@/pages/AnalyticsPage.vue'), meta: { title: 'Analytics' } },
  { path: '/alerts', name: 'alerts', component: () => import('@/pages/AlertsPage.vue'), meta: { title: 'Alerts & activity' } },
  { path: '/agents', name: 'agents', component: () => import('@/pages/AgentsPage.vue'), meta: { title: 'Agents & API' } },
  {
    path: '/settings',
    component: () => import('@/pages/settings/SettingsLayout.vue'),
    meta: { title: 'Settings' },
    children: [
      { path: '', redirect: { name: 'settings-general' } },
      { path: 'general', name: 'settings-general', component: () => import('@/pages/settings/GeneralSettings.vue'), meta: { title: 'General' } },
      { path: 'appearance', name: 'settings-appearance', component: () => import('@/pages/settings/AppearanceSettings.vue'), meta: { title: 'Appearance' } },
      { path: 'sources', name: 'settings-sources', component: () => import('@/pages/settings/SourcesSettings.vue'), meta: { title: 'Node & pool' } },
      { path: 'notifications', name: 'settings-notifications', component: () => import('@/pages/settings/NotificationsSettings.vue'), meta: { title: 'Notifications' } },
      { path: 'energy', name: 'settings-energy', component: () => import('@/pages/settings/EnergySettings.vue'), meta: { title: 'Energy & money' } },
      { path: 'safety', name: 'settings-safety', component: () => import('@/pages/settings/SafetySettings.vue'), meta: { title: 'Safety' } },
      { path: 'security', name: 'settings-security', component: () => import('@/pages/settings/SecuritySettings.vue'), meta: { title: 'Security' } },
      { path: 'data', name: 'settings-data', component: () => import('@/pages/settings/DataSettings.vue'), meta: { title: 'Data & backup' } },
      { path: 'about', name: 'settings-about', component: () => import('@/pages/settings/AboutSettings.vue'), meta: { title: 'About & health' } },
    ],
  },
  { path: '/setup', name: 'setup', component: () => import('@/pages/SetupPage.vue'), meta: { title: 'Welcome', bare: true } },
  { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue'), meta: { title: 'Sign in', bare: true, public: true } },
  { path: '/kiosk', name: 'kiosk', component: () => import('@/pages/KioskPage.vue'), meta: { title: 'Wall display', bare: true } },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/pages/NotFoundPage.vue'), meta: { title: 'Not found' } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.path === from.path) return false
    return { top: 0 }
  },
})

let offeredSetup = false

router.beforeEach((to) => {
  const session = useSession()
  if (session.state === 'login' && !to.meta.public) {
    return { name: 'login', query: to.fullPath !== '/' ? { next: to.fullPath } : undefined }
  }
  if (session.authenticated && to.name === 'login') return { name: 'dashboard' }

  // First run: offer the guided setup once per visit, never in demo mode and never if they already have miners.
  if (session.state === 'ready' && !offeredSetup && to.name === 'dashboard') {
    offeredSetup = true
    const m = session.meta
    if (m && !m.setup.onboarding_done && m.setup.devices === 0 && !m.demo && session.canControl) return { name: 'setup' }
  }
  return true
})

router.afterEach((to) => {
  const session = useSession()
  const name = session.meta?.instance_name
  const title = (to.meta.title as string | undefined) ?? 'Solo Miner Monitor'
  document.title = name && name !== 'My solo mining fleet' ? `${title} · ${name}` : `${title} · Solo Miner Monitor`
})
