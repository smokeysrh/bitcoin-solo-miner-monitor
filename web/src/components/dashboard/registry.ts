import { Activity, Bell, Blocks, CheckCheck, Coins, Cpu, Dices, Fuel, Gauge, Lightbulb, LineChart, Network, Server, Thermometer, Trophy, Zap } from 'lucide-vue-next'
import { defineAsyncComponent, type Component } from 'vue'
import type { DashboardLayout, DashboardWidgetPlacement } from '@/lib/types'

export type Span = DashboardWidgetPlacement['span']

export interface WidgetDef {
  id: string
  title: string
  description: string
  icon: Component
  component: Component
  /** column spans this widget looks good at, smallest first */
  spans: Span[]
  defaultSpan: Span
  /** part of the trimmed-down layout for newcomers */
  simple: boolean
  /** meaningless until at least one miner exists */
  needsMiners: boolean
}

const lazy = (loader: () => Promise<{ default: Component }>): Component => defineAsyncComponent({ loader, delay: 200 })

export const WIDGETS: WidgetDef[] = [
  {
    id: 'checklist',
    title: 'Getting started',
    description: 'A short checklist for new setups. Hides itself when you are done.',
    icon: CheckCheck,
    component: lazy(() => import('./widgets/ChecklistWidget.vue')),
    spans: [12],
    defaultSpan: 12,
    simple: true,
    needsMiners: false,
  },
  {
    id: 'hero',
    title: 'Fleet hashrate',
    description: 'Total hashrate with a live chart, power, efficiency, temperature and shares.',
    icon: Gauge,
    component: lazy(() => import('./widgets/HeroWidget.vue')),
    spans: [6, 8, 12],
    defaultSpan: 8,
    simple: true,
    needsMiners: true,
  },
  {
    id: 'odds',
    title: 'Your odds',
    description: 'Your chance of finding a block, in plain numbers.',
    icon: Dices,
    component: lazy(() => import('./widgets/OddsWidget.vue')),
    spans: [3, 4, 6],
    defaultSpan: 4,
    simple: true,
    needsMiners: true,
  },
  {
    id: 'miners',
    title: 'Miners',
    description: 'A tile for every miner, problems first.',
    icon: Cpu,
    component: lazy(() => import('./widgets/MinersWidget.vue')),
    spans: [6, 8, 12],
    defaultSpan: 12,
    simple: true,
    needsMiners: false,
  },
  {
    id: 'hashrate-chart',
    title: 'Hashrate chart',
    description: 'Hashrate over time, all together or one line per miner.',
    icon: LineChart,
    component: lazy(() => import('./widgets/HashrateChartWidget.vue')),
    spans: [6, 8, 12],
    defaultSpan: 8,
    simple: false,
    needsMiners: true,
  },
  {
    id: 'best-share',
    title: 'Closest call',
    description: 'Your best share so far and how far it is from a block.',
    icon: Trophy,
    component: lazy(() => import('./widgets/BestShareWidget.vue')),
    spans: [3, 4, 6],
    defaultSpan: 4,
    simple: false,
    needsMiners: true,
  },
  {
    id: 'power-chart',
    title: 'Power & efficiency chart',
    description: 'Watts and joules per terahash over time.',
    icon: Zap,
    component: lazy(() => import('./widgets/PowerChartWidget.vue')),
    spans: [4, 6, 8, 12],
    defaultSpan: 6,
    simple: false,
    needsMiners: true,
  },
  {
    id: 'temperatures',
    title: 'Temperature chart',
    description: 'Chip and regulator temperatures of your hottest miner.',
    icon: Thermometer,
    component: lazy(() => import('./widgets/TemperatureWidget.vue')),
    spans: [4, 6, 8, 12],
    defaultSpan: 6,
    simple: false,
    needsMiners: true,
  },
  {
    id: 'network',
    title: 'Bitcoin network',
    description: 'Block height, difficulty, next adjustment and halving.',
    icon: Network,
    component: lazy(() => import('./widgets/NetworkWidget.vue')),
    spans: [3, 4, 6],
    defaultSpan: 4,
    simple: false,
    needsMiners: false,
  },
  {
    id: 'money',
    title: 'Electricity & value',
    description: 'What mining costs and what the lottery pays on average.',
    icon: Coins,
    component: lazy(() => import('./widgets/MoneyWidget.vue')),
    spans: [3, 4, 6],
    defaultSpan: 4,
    simple: false,
    needsMiners: true,
  },
  {
    id: 'node-pool',
    title: 'Your node & pool',
    description: 'Sync state, peers, pool-side hashrate and workers.',
    icon: Server,
    component: lazy(() => import('./widgets/NodePoolWidget.vue')),
    spans: [4, 6],
    defaultSpan: 4,
    simple: false,
    needsMiners: false,
  },
  {
    id: 'alerts',
    title: 'Needs attention',
    description: 'Problems that are happening right now.',
    icon: Bell,
    component: lazy(() => import('./widgets/AlertsWidget.vue')),
    spans: [4, 6, 12],
    defaultSpan: 6,
    simple: true,
    needsMiners: false,
  },
  {
    id: 'activity',
    title: 'Recent activity',
    description: 'Restarts, outages, new records and blocks.',
    icon: Activity,
    component: lazy(() => import('./widgets/ActivityWidget.vue')),
    spans: [4, 6, 12],
    defaultSpan: 6,
    simple: true,
    needsMiners: false,
  },
  {
    id: 'blocks',
    title: 'Latest blocks',
    description: 'The newest blocks on the chain. Yours get a badge.',
    icon: Blocks,
    component: lazy(() => import('./widgets/BlocksWidget.vue')),
    spans: [3, 4, 6],
    defaultSpan: 4,
    simple: false,
    needsMiners: false,
  },
  {
    id: 'fees',
    title: 'Fees & price',
    description: 'Transaction fee estimates and the Bitcoin price.',
    icon: Fuel,
    component: lazy(() => import('./widgets/FeesWidget.vue')),
    spans: [3, 4, 6],
    defaultSpan: 4,
    simple: false,
    needsMiners: false,
  },
  {
    id: 'insights',
    title: 'Tips & observations',
    description: 'Plain-language notes: weak WiFi, inefficient miners, stale node.',
    icon: Lightbulb,
    component: lazy(() => import('./widgets/InsightsWidget.vue')),
    spans: [4, 6, 12],
    defaultSpan: 4,
    simple: false,
    needsMiners: false,
  },
]

export const WIDGET_BY_ID: Record<string, WidgetDef> = Object.fromEntries(WIDGETS.map((w) => [w.id, w]))

/** Tailwind needs the full class names to exist in source, hence the lookup instead of string building. */
export const SPAN_CLASS: Record<Span, string> = {
  3: 'md:col-span-3 xl:col-span-3',
  4: 'md:col-span-3 xl:col-span-4',
  6: 'md:col-span-3 xl:col-span-6',
  8: 'md:col-span-6 xl:col-span-8',
  12: 'md:col-span-6 xl:col-span-12',
}

export const SPAN_LABEL: Record<Span, string> = { 3: 'S', 4: 'S', 6: 'M', 8: 'L', 12: 'Full' }

const place = (id: string, span?: Span): DashboardWidgetPlacement => ({ id, span: span ?? WIDGET_BY_ID[id]!.defaultSpan })

export const DEFAULT_LAYOUT: DashboardWidgetPlacement[] = [
  place('checklist'),
  place('hero'),
  place('odds'),
  place('miners'),
  place('hashrate-chart'),
  place('best-share'),
  place('power-chart'),
  place('temperatures'),
  place('network'),
  place('money'),
  place('node-pool'),
  place('alerts'),
  place('activity'),
  place('blocks'),
  place('fees'),
  place('insights'),
]

export const SIMPLE_LAYOUT: DashboardWidgetPlacement[] = [place('checklist'), place('hero'), place('odds'), place('miners'), place('alerts'), place('activity')]

/**
 * Turn whatever was saved on the server into a layout that is safe to render:
 * unknown widgets are dropped (a widget removed in an upgrade), duplicates collapse, and a span the widget
 * no longer supports snaps to its default. Nothing saved means the default for the user's mode.
 */
export function resolveLayout(saved: DashboardLayout | null | undefined, simple: boolean): DashboardWidgetPlacement[] {
  const base = simple ? SIMPLE_LAYOUT : DEFAULT_LAYOUT
  if (!saved || saved.version !== 1 || !Array.isArray(saved.widgets)) return base.map((p) => ({ ...p }))
  const seen = new Set<string>()
  const out: DashboardWidgetPlacement[] = []
  for (const p of saved.widgets) {
    const def = p && typeof p.id === 'string' ? WIDGET_BY_ID[p.id] : undefined
    if (!def || seen.has(def.id)) continue
    seen.add(def.id)
    out.push({ id: def.id, span: def.spans.includes(p.span) ? p.span : def.defaultSpan })
  }
  return out
}

/** Widgets that are not on the dashboard right now (for the "add widget" tray). */
export function availableWidgets(layout: DashboardWidgetPlacement[]): WidgetDef[] {
  const used = new Set(layout.map((p) => p.id))
  return WIDGETS.filter((w) => !used.has(w.id))
}

/** Next larger/smaller span the widget supports, wrapping around. */
export function cycleSpan(def: WidgetDef, current: Span): Span {
  const i = def.spans.indexOf(current)
  return def.spans[(i + 1) % def.spans.length] ?? def.defaultSpan
}
