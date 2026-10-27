import { Bell, Bitcoin, Bot, ChartLine, Cpu, Dices, LayoutDashboard, Settings } from 'lucide-vue-next'
import type { Component } from 'vue'

export interface NavItem {
  to: string
  name: string
  label: string
  icon: Component
  group: 'monitor' | 'manage'
  /** words people might type in the command palette */
  keywords?: string
}

export const NAV: NavItem[] = [
  { to: '/', name: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, group: 'monitor', keywords: 'home overview' },
  { to: '/miners', name: 'miners', label: 'Miners', icon: Cpu, group: 'monitor', keywords: 'devices bitaxe nerdqaxe avalon asic' },
  { to: '/bitcoin', name: 'bitcoin', label: 'Bitcoin', icon: Bitcoin, group: 'monitor', keywords: 'node pool network difficulty blocks mempool halving' },
  { to: '/odds', name: 'odds', label: 'Odds & costs', icon: Dices, group: 'monitor', keywords: 'chance probability lottery electricity profit calculator' },
  { to: '/analytics', name: 'analytics', label: 'Analytics', icon: ChartLine, group: 'monitor', keywords: 'charts history graphs export csv' },
  { to: '/alerts', name: 'alerts', label: 'Alerts & activity', icon: Bell, group: 'manage', keywords: 'notifications events log rules' },
  { to: '/agents', name: 'agents', label: 'Agents & API', icon: Bot, group: 'manage', keywords: 'ai mcp token api llms openapi claude' },
  { to: '/settings', name: 'settings', label: 'Settings', icon: Settings, group: 'manage', keywords: 'preferences theme units energy security backup' },
]

/** Bottom bar on phones: the four most used pages plus a "More" sheet. */
export const MOBILE_PRIMARY = ['dashboard', 'miners', 'bitcoin', 'alerts']
