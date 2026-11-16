import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fill, HASHLING_MOMENTS, type MomentId, type Vars } from '@/lib/hashlingText'
import {
  alertMomentFor,
  momentFor,
  MOMENT_POSE,
  NEEDS_MINER,
  NEEDS_SOURCE,
  planPopups,
  toneOf,
  type Candidate,
  type Moment,
  type PlannedPopup,
  type Tone,
} from '@/lib/hashlingMoments'
import type { HashlingPose } from '@/lib/brand'
import type { ActiveAlert, AppEvent, DeviceView } from '@/lib/types'
import { useLive } from './live'
import { useSettings } from './settings'

const SEEN_KEY = 'bsmm.hashlingSeen'
/** How many shown events and alerts are remembered across reloads (the newest are kept). */
const SEEN_MAX = 200

/** Times in milliseconds, and the queue length, shared with the tests. */
export const HASHLING_TIMING = {
  /** A burst is one burst until this long passes with nothing new... */
  coalesceMs: 3_000,
  /** ...but never held back longer than this, so a long storm still shows something. */
  maxWaitMs: 10_000,
  /** How long a pop-up stays when nobody dismisses it. */
  popupMs: 12_000,
  /** A found block stays longer: it is the one thing worth walking over to the wall display for. */
  blockMs: 60_000,
  /** At most this many pop-ups are held; the oldest waiting one is dropped first. */
  queueMax: 8,
} as const

export interface PopupItem {
  id: number
  momentId: MomentId
  pose: HashlingPose
  tone: Tone
  title: string
  line: string
  timeoutMs: number
}

/** Where Hashling is being shown: the dashboard, or the wall display (set by the pop-up component from the route). */
export type Surface = 'dashboard' | 'wall'

function loadSeen(): string[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]')
    return Array.isArray(stored) ? stored.filter((k): k is string => typeof k === 'string').slice(-SEEN_MAX) : []
  } catch (e) {
    console.warn('Could not read which Hashling pop-ups were already shown; starting fresh', e)
    return []
  }
}

/** An event is identified by its id and time: the server can reuse ids after a data reset. */
const eventKey = (e: AppEvent): string => `e:${e.id ?? e.type}:${Math.floor(e.ts)}`
/** An alert is identified by its key and when it started firing: a problem that clears and returns is a new alert. */
const alertKey = (a: ActiveAlert): string => `a:${a.key}@${a.since}`

/**
 * Hashling's pop-ups. Live events and newly active alerts are offered here; what is worth a pop-up is queued, a burst
 * is coalesced into one pop-up, one is visible at a time, and each event is shown once (remembered across reloads).
 * Pages offer their own moments (setup, notifications, checklist) through `show`.
 */
export const useHashling = defineStore('hashling', () => {
  const settings = useSettings()
  const items = ref<PopupItem[]>([])
  const surface = ref<Surface>('dashboard')
  /** On unless switched off (settings saved before the switch existed count as on). Never before settings have loaded. */
  const enabled = computed(() => (settings.data ? settings.data.ui.hashling_popups !== false : false))
  const current = computed(() => items.value[0] ?? null)
  const waiting = computed(() => Math.max(0, items.value.length - 1))

  let seen: string[] = loadSeen()
  let pending: Candidate[] = []
  let firstPendingAt = 0
  let windowTimer: ReturnType<typeof setTimeout> | null = null
  let dismissTimer: ReturnType<typeof setTimeout> | null = null
  let held = false
  let outageOpen = false
  let nextItemId = 0

  function remember(key: string): void {
    seen = [...seen.filter((k) => k !== key), key].slice(-SEEN_MAX)
    try {
      localStorage.setItem(SEEN_KEY, JSON.stringify(seen))
    } catch (e) {
      console.warn('Could not remember which Hashling pop-ups were shown', e)
    }
  }

  function nameOf(deviceId: string | null): string | null {
    return deviceId ? (useLive().byId(deviceId)?.name ?? null) : null
  }

  /** The node or pool an alert is about: by source id for "unreachable", the node itself for "behind". */
  function sourceNameFor(a: ActiveAlert, id: MomentId): string | null {
    const sources = useLive().network?.sources ?? []
    if (id === 'M09') return sources.find((s) => s.id === a.key.split(':')[1])?.name ?? null
    if (id === 'M10') return sources.find((s) => s.kind === 'bitcoin_core' && !s.implicit)?.name ?? null
    return null
  }

  // ------------------------------------------------------------------------------------------------ the pop-up queue

  function startDismissTimer(): void {
    if (dismissTimer) clearTimeout(dismissTimer)
    dismissTimer = null
    const first = items.value[0]
    if (first && !held) dismissTimer = setTimeout(dismiss, first.timeoutMs)
  }

  function push(item: PopupItem): void {
    const next = [...items.value, item]
    while (next.length > HASHLING_TIMING.queueMax) next.splice(1, 1) // the visible one stays; the oldest waiting one goes
    items.value = next
    if (next.length === 1) startDismissTimer()
  }

  function dismiss(): void {
    held = false // whatever was holding it is gone with it
    items.value = items.value.slice(1)
    startDismissTimer()
  }

  /** Someone is reading it (pointer or keyboard focus on it): do not take it away. */
  function hold(): void {
    held = true
    if (dismissTimer) clearTimeout(dismissTimer)
    dismissTimer = null
  }

  /** They let go: it gets its full time again. */
  function release(): void {
    held = false
    startDismissTimer()
  }

  function build(id: MomentId, severity: Moment['severity'], vars: Vars): PopupItem {
    const text = HASHLING_MOMENTS[id]
    return {
      id: ++nextItemId,
      momentId: id,
      pose: MOMENT_POSE[id],
      tone: toneOf(severity),
      title: text.title ?? '',
      line: fill(text.line, vars),
      timeoutMs: id === 'M13' ? HASHLING_TIMING.blockMs : HASHLING_TIMING.popupMs,
    }
  }

  // -------------------------------------------------------------------------------------------------- coalescing

  function enqueue(candidate: Candidate): void {
    const now = Date.now()
    if (pending.length === 0) firstPendingAt = now
    pending.push(candidate)
    if (windowTimer) clearTimeout(windowTimer)
    const wait = Math.min(HASHLING_TIMING.coalesceMs, Math.max(0, firstPendingAt + HASHLING_TIMING.maxWaitMs - now))
    windowTimer = setTimeout(flush, wait)
  }

  /** Is every miner other than the ones that just came back doing work? A disabled miner is not part of the fleet. */
  function everyOtherMinerHashing(devices: readonly DeviceView[], returning: ReadonlySet<string | null>): boolean {
    const fleet = devices.filter((d) => d.status !== 'disabled')
    return fleet.length > 0 && fleet.every((d) => returning.has(d.id) || (d.status === 'online' && (d.hashrate_smooth_hs ?? d.telemetry?.hashrate_hs ?? 0) > 0))
  }

  function flush(): void {
    windowTimer = null
    const batch = pending
    pending = []
    if (!enabled.value) return
    const live = useLive()
    const ready: Candidate[] = []
    for (const c of batch) {
      const resolved = { ...c, miner: c.miner ?? nameOf(c.deviceId) }
      if ((NEEDS_MINER.has(c.moment.id) && resolved.miner === null) || (NEEDS_SOURCE.has(c.moment.id) && resolved.source === null)) {
        console.warn(`Hashling ${c.moment.id} skipped: the miner or node it names is not known (${c.key})`)
        continue
      }
      ready.push(resolved)
    }
    const returning = new Set(ready.filter((c) => c.moment.id === 'M16').map((c) => c.deviceId))
    const outageClear = outageOpen && returning.size > 0 && everyOtherMinerHashing(live.devices, returning)
    const plans: PlannedPopup[] = planPopups(ready, outageClear)
    if (plans.some((p) => p.id === 'M17')) outageOpen = false
    for (const p of plans) push(build(p.id, p.severity, p.vars))
  }

  // ----------------------------------------------------------------------------------------------------- inputs

  /**
   * A live event. Returns true when Hashling owns it (so the toaster should stay quiet) and false when it is none of
   * Hashling's business or the switch is off. Whatever is returned, an event already seen never shows again.
   */
  function offer(e: AppEvent): boolean {
    if (!enabled.value) return false
    const moment = momentFor(e)
    if (!moment) return false
    if (e.type === 'device_offline') outageOpen = true
    const key = eventKey(e)
    if (seen.includes(key)) return true
    remember(key)
    // On the dashboard the celebration dialog is the pop-up for a found block (it shows the same pose and line).
    if (moment.id === 'M13' && surface.value !== 'wall') return true
    enqueue({ key, moment, deviceId: e.device_id, miner: nameOf(e.device_id), source: null })
    return true
  }

  /** Alerts that are active when the page loads are history: remember them, never show them. */
  function seedAlerts(active: readonly ActiveAlert[]): void {
    for (const a of active) {
      const key = alertKey(a)
      if (!seen.includes(key)) remember(key)
    }
  }

  /** The full list of active alerts, as the server repeats it every few seconds: only a newly started alert is news. */
  function observeAlerts(active: readonly ActiveAlert[]): void {
    for (const a of active) {
      const key = alertKey(a)
      if (seen.includes(key)) continue
      remember(key)
      if (!enabled.value) continue
      const moment = alertMomentFor(a)
      if (!moment) continue
      enqueue({ key, moment, deviceId: a.device_id, miner: nameOf(a.device_id), source: sourceNameFor(a, moment.id) })
    }
  }

  /**
   * A moment the app itself decides (setup, notifications, checklist, an accepted pool change). Shows at once.
   * Returns true when Hashling took it, false when the switch is off so the caller can keep its own toast.
   * `once` makes it a one-time moment, remembered across reloads.
   */
  function show(id: MomentId, vars: Vars = {}, opts: { once?: string } = {}): boolean {
    if (!enabled.value) return false
    if (opts.once) {
      const key = `ui:${opts.once}`
      if (seen.includes(key)) return true
      remember(key)
    }
    push(build(id, 'success', vars))
    return true
  }

  /** Forget the queue and the timers (sign-out). What was already shown stays remembered. */
  function clear(): void {
    if (windowTimer) clearTimeout(windowTimer)
    if (dismissTimer) clearTimeout(dismissTimer)
    windowTimer = dismissTimer = null
    pending = []
    items.value = []
    held = false
    outageOpen = false
  }

  return { items, current, waiting, enabled, surface, offer, seedAlerts, observeAlerts, show, dismiss, hold, release, clear }
})
