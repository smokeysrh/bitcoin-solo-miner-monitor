/**
 * Which moment Hashling shows for something that happened, and how a burst of moments becomes pop-ups.
 *
 * Everything here is deterministic and has no side effects: `momentFor(event)` and `alertMomentFor(alert)` map what the
 * server already sends (events on the live stream, active alerts) to a moment or to nothing, and `planPopups` turns the
 * moments of one short window into the pop-ups to show. The words live in `hashlingText.ts`, the art in `brand.ts`.
 */
import type { HashlingPose } from './brand'
import { HASHLING_UI, listMiners, type MomentId, type Vars } from './hashlingText'
import type { ActiveAlert, AppEvent, Severity } from './types'

export type Tone = 'bad' | 'warn' | 'ok' | 'info'

const TONES: Record<Severity, Tone> = { critical: 'bad', warning: 'warn', success: 'ok', info: 'info' }
/** The same severity tones the toaster uses. */
export const toneOf = (severity: Severity): Tone => TONES[severity]

const POSE_ALT: Record<HashlingPose, keyof typeof HASHLING_UI> = {
  alert: 'U01a',
  sleeping: 'U01b',
  'found-block': 'U01c',
  celebrate: 'U01d',
  'thumbs-up': 'U01e',
  tinkering: 'U01f',
  'lottery-ticket': 'U01g',
}
/** Real alt text for a pose (Becky's U01a to U01g). */
export const poseAlt = (pose: HashlingPose): string => HASHLING_UI[POSE_ALT[pose]]

/** The pose of every moment (the kit's table of when he shows up). */
export const MOMENT_POSE: Record<MomentId, HashlingPose> = {
  M01: 'alert', M02: 'alert', M02N: 'alert', M03: 'alert', M04: 'alert', M05: 'alert', M06: 'alert', M07: 'alert',
  M08: 'alert', M09: 'alert', M10: 'alert', M11: 'alert', M1XN: 'alert',
  M12: 'sleeping',
  M13: 'found-block',
  M14: 'celebrate', M15: 'celebrate', M15N: 'celebrate',
  M16: 'thumbs-up', M16N: 'thumbs-up', M17: 'thumbs-up', M19: 'thumbs-up', M21: 'thumbs-up', M22: 'thumbs-up', M23: 'thumbs-up', M24: 'thumbs-up',
  M18: 'tinkering', M20: 'tinkering',
  M25: 'lottery-ticket',
}

export interface Moment {
  id: MomentId
  pose: HashlingPose
  severity: Severity
}

const moment = (id: MomentId, severity: Severity): Moment => ({ id, pose: MOMENT_POSE[id], severity })

/** `device_degraded` carries the server's reason; "Not hashing" is the one that means a miner is on but doing no work. */
const NOT_HASHING = /\bnot hashing\b/i
/** Does the reason the server gives for a miner's status (or for `device_degraded`) say it is on but doing no work? */
export const reportsNotHashing = (reason: string | null | undefined): boolean => NOT_HASHING.test(reason ?? '')

/** A found block is confirmed when it carries the block's height and hash and did not come from the miner's own counter. */
function isConfirmedBlock(e: AppEvent): boolean {
  return typeof e.data.height === 'number' && typeof e.data.hash === 'string' && e.data.source !== 'device'
}

/**
 * The moment for an event the server published, or null when Hashling stays out of it. Decided by event type (never by
 * severity alone), so healthy, info and history events show nothing, and the found-block pose needs a confirmed
 * `block_found`.
 */
export function momentFor(e: AppEvent): Moment | null {
  switch (e.type) {
    case 'pool_settings_changed':
      return moment('M01', e.severity)
    case 'device_offline':
      return moment('M02', e.severity)
    case 'pool_failover':
      return moment('M08', e.severity)
    case 'device_degraded':
      return moment(reportsNotHashing(e.body) ? 'M12' : 'M11', e.severity)
    case 'block_found':
      return isConfirmedBlock(e) ? moment('M13', e.severity) : null
    case 'new_best_share':
      return moment('M14', e.severity)
    case 'device_added':
      return moment('M15', e.severity)
    case 'device_online':
      return moment('M16', e.severity)
    default:
      return null
  }
}

/** Sleeping for a miner seen going from hashing to not hashing in its views, with the severity of the server's `device_degraded`. */
export const sleepingMoment = (): Moment => moment('M12', 'warning')

const RULE_ID_PREFIX = 'rule_'
/**
 * Alert rules that reach the web app only as active alerts. The offline, fallback-pool and needs-attention rules are left
 * out on purpose: their events (device_offline, pool_failover, device_degraded) already show Hashling, and a second
 * pop-up for the same thing minutes later would nag.
 */
const ALERT_RULE_MOMENTS = new Map<string, MomentId>([
  ['fan_failure', 'M03'],
  ['temp_high', 'M04'],
  ['hashrate_drop', 'M05'],
  ['fleet_hashrate_drop', 'M06'],
  ['reject_rate_high', 'M07'],
  ['node_down', 'M09'],
  ['node_behind', 'M10'],
])

/** The moment for a newly active alert. Built-in rules have the id `rule_<kind>`; a custom rule has a random id and shows nothing. */
export function alertMomentFor(a: ActiveAlert): Moment | null {
  if (!a.rule_id.startsWith(RULE_ID_PREFIX)) return null
  const id = ALERT_RULE_MOMENTS.get(a.rule_id.slice(RULE_ID_PREFIX.length))
  return id ? moment(id, a.severity) : null
}

/** Moments whose line names a miner / a node or pool. */
export const NEEDS_MINER: ReadonlySet<MomentId> = new Set<MomentId>(['M01', 'M02', 'M03', 'M04', 'M05', 'M07', 'M08', 'M11', 'M12', 'M14', 'M15', 'M16'])
export const NEEDS_SOURCE: ReadonlySet<MomentId> = new Set<MomentId>(['M09', 'M10'])

/**
 * The needs-attention moments, most specific first. When one miner has several in the same window only the first
 * of these is shown, so a fallback pool is "fallback pool" and not also "needs attention".
 */
const ATTENTION_ORDER: readonly MomentId[] = ['M01', 'M02', 'M03', 'M04', 'M08', 'M05', 'M07', 'M12', 'M11', 'M06', 'M09', 'M10']
const ATTENTION: ReadonlySet<MomentId> = new Set(ATTENTION_ORDER)

/** One moment that happened, with what its line needs to name. */
export interface Candidate {
  /** Identity of the event or alert it came from (used to remember it was shown). */
  key: string
  moment: Moment
  deviceId: string | null
  /** The miner's name, when the moment is about one. */
  miner: string | null
  /** The node or pool's name, for node trouble. */
  source: string | null
}

export interface PlannedPopup {
  id: MomentId
  pose: HashlingPose
  severity: Severity
  vars: Vars
}

const RANK: Record<Severity, number> = { info: 0, success: 1, warning: 2, critical: 3 }
const worst = (list: readonly Candidate[]): Severity => list.reduce<Severity>((w, c) => (RANK[c.moment.severity] > RANK[w] ? c.moment.severity : w), list[0]!.moment.severity)

function single(c: Candidate): PlannedPopup {
  return { id: c.moment.id, pose: c.moment.pose, severity: c.moment.severity, vars: { miner: c.miner ?? undefined, source: c.source ?? undefined } }
}
function combined(id: MomentId, list: readonly Candidate[], vars: Vars = {}): PlannedPopup {
  return { id, pose: MOMENT_POSE[id], severity: worst(list), vars }
}

function onePerDevice(list: readonly Candidate[]): Candidate[] {
  const best = new Map<string, Candidate>()
  const unattached: Candidate[] = []
  for (const c of list) {
    if (c.deviceId === null) {
      unattached.push(c)
      continue
    }
    const held = best.get(c.deviceId)
    if (!held || ATTENTION_ORDER.indexOf(c.moment.id) < ATTENTION_ORDER.indexOf(held.moment.id)) best.set(c.deviceId, c)
  }
  return [...best.values(), ...unattached]
}

/**
 * Turn the moments of one window into the pop-ups to show, in the order to show them: a found block, then trouble, then
 * the good news. Several offline miners become one "several miners offline", other mixed trouble becomes one "several
 * things need a look", added miners and returning miners are counted. `outageClear` says the outage is over and every
 * miner is hashing, which makes the returning miners one "every miner is hashing".
 */
export function planPopups(candidates: readonly Candidate[], outageClear: boolean): PlannedPopup[] {
  const out: PlannedPopup[] = []
  const of = (id: MomentId): Candidate[] => candidates.filter((c) => c.moment.id === id)

  for (const c of of('M13')) out.push(single(c))

  const attention = onePerDevice(candidates.filter((c) => ATTENTION.has(c.moment.id)))
  if (attention.length === 1) out.push(single(attention[0]!))
  else if (attention.length > 1) {
    if (attention.every((c) => c.moment.id === 'M02')) {
      const names = attention.map((c) => c.miner).filter((n): n is string => n !== null)
      out.push(combined('M02N', attention, { count: attention.length, miners: listMiners(names) }))
    } else out.push(combined('M1XN', attention, { count: attention.length }))
  }

  for (const c of of('M14')) out.push(single(c))

  const added = of('M15')
  if (added.length === 1) out.push(single(added[0]!))
  else if (added.length > 1) out.push(combined('M15N', added, { count: added.length }))

  const back = of('M16')
  if (back.length > 0) {
    if (outageClear) out.push(combined('M17', back))
    else if (back.length === 1) out.push(single(back[0]!))
    else out.push(combined('M16N', back, { count: back.length }))
  }
  return out
}
