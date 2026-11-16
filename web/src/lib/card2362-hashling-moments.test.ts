// @vitest-environment node
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { HASHLING_ART, HASHLING_POSES } from '@/lib/brand'
import { HASHLING_MOMENTS, HASHLING_UI, fill, listMiners } from '@/lib/hashlingText'
import { alertMomentFor, momentFor, planPopups, poseAlt, toneOf, type Candidate, type Moment } from '@/lib/hashlingMoments'
import type { ActiveAlert, AppEvent, Severity } from '@/lib/types'

// Card #2362: Hashling moments. `momentFor` maps an existing server event to the moment Hashling shows (or none);
// `planPopups` turns the moments of one short window into the pop-ups the person sees.

function ev(type: string, severity: Severity, over: Partial<AppEvent> = {}): AppEvent {
  return { id: 1, ts: 1_700_000_000, type, severity, device_id: 'd1', title: 'title', body: null, data: {}, dedupe_key: null, ack_ts: null, ...over }
}
function alert(ruleId: string, over: Partial<ActiveAlert> = {}): ActiveAlert {
  return { key: `${ruleId}:d1`, rule_id: ruleId, since: 1_700_000_000, title: 'title', body: null, device_id: 'd1', severity: 'warning', ...over }
}
const CONFIRMED_BLOCK = { height: 900_001, hash: 'ab'.repeat(32), source: 'chain' }

describe('momentFor: each existing server event picks its moment and pose', () => {
  const table: Array<[string, AppEvent, string, string]> = [
    ['pool or payout changed', ev('pool_settings_changed', 'critical'), 'M01', 'alert'],
    ['miner offline', ev('device_offline', 'critical'), 'M02', 'alert'],
    ['fallback pool', ev('pool_failover', 'warning'), 'M08', 'alert'],
    ['on but not hashing', ev('device_degraded', 'warning', { body: 'Not hashing' }), 'M12', 'sleeping'],
    ['not hashing among other reasons', ev('device_degraded', 'warning', { body: 'Not connected to its pool; Not hashing' }), 'M12', 'sleeping'],
    ['any other needs-attention', ev('device_degraded', 'warning', { body: 'Fault reported: overcurrent' }), 'M11', 'alert'],
    ['needs attention with no reason given', ev('device_degraded', 'warning', { body: null }), 'M11', 'alert'],
    ['confirmed block', ev('block_found', 'success', { device_id: null, data: CONFIRMED_BLOCK }), 'M13', 'found-block'],
    ['new best share', ev('new_best_share', 'success'), 'M14', 'celebrate'],
    ['miner added', ev('device_added', 'info'), 'M15', 'celebrate'],
    ['quiet miner is back', ev('device_online', 'success'), 'M16', 'thumbs-up'],
  ]
  it.each(table)('%s', (_name, event, id, pose) => {
    const m = momentFor(event)
    expect(m?.id).toBe(id)
    expect(m?.pose).toBe(pose)
  })

  it('carries the severity of the event, so the pop-up can use the same tones as the toaster', () => {
    expect(momentFor(ev('device_offline', 'critical'))?.severity).toBe('critical')
    expect(momentFor(ev('pool_failover', 'warning'))?.severity).toBe('warning')
    expect(toneOf('critical')).toBe('bad')
    expect(toneOf('warning')).toBe('warn')
    expect(toneOf('success')).toBe('ok')
    expect(toneOf('info')).toBe('info')
  })
})

describe('momentFor: nothing happens for healthy, info and history events', () => {
  const quiet: Array<[string, Severity]> = [
    ['device_restarted', 'info'],
    ['firmware_changed', 'info'],
    ['difficulty_adjusted', 'info'],
    ['device_paused', 'info'],
    ['device_removed', 'info'],
    ['device_moved', 'info'],
    ['block_restored', 'info'],
    ['device_recovered', 'success'],
    ['pool_restored', 'success'],
    ['source_up', 'success'],
    ['custom_notification', 'info'],
    ['notification_failed', 'warning'],
    ['block_orphaned', 'warning'],
    ['source_down', 'warning'],
    ['an_event_type_nobody_has_heard_of', 'critical'],
  ]
  it.each(quiet)('%s (%s) shows no Hashling', (type, severity) => {
    expect(momentFor(ev(type, severity))).toBeNull()
  })
})

describe('momentFor: the found-block pose is only for a confirmed block_found event', () => {
  it('is used for a block_found event that carries its height and hash', () => {
    expect(momentFor(ev('block_found', 'success', { data: CONFIRMED_BLOCK }))?.pose).toBe('found-block')
  })

  it('is not used when the miner only reports it (no chain evidence, source "device")', () => {
    const reported = ev('block_found', 'success', { data: { source: 'device', blocks_found: 3 } })
    expect(momentFor(reported)).toBeNull()
    expect(momentFor(ev('block_found', 'success', { data: { ...CONFIRMED_BLOCK, source: 'device' } }))).toBeNull()
  })

  it('is not used when height or hash is missing', () => {
    expect(momentFor(ev('block_found', 'success', { data: { height: 5 } }))).toBeNull()
    expect(momentFor(ev('block_found', 'success', { data: { hash: 'ab' } }))).toBeNull()
    expect(momentFor(ev('block_found', 'success', { data: {} }))).toBeNull()
  })

  it('is never chosen for any other event type, even one that carries a height and a hash', () => {
    const types = ['new_best_share', 'device_online', 'device_added', 'device_offline', 'block_orphaned', 'block_restored', 'difficulty_adjusted', 'custom_notification', 'pool_settings_changed']
    for (const type of types) {
      for (const severity of ['info', 'success', 'warning', 'critical'] as const) {
        expect(momentFor(ev(type, severity, { data: CONFIRMED_BLOCK }))?.pose, `${type}/${severity}`).not.toBe('found-block')
      }
    }
  })

  it('is never chosen for an alert, whatever its rule', () => {
    for (const rule of ['temp_high', 'fan_failure', 'hashrate_drop', 'fleet_hashrate_drop', 'reject_rate_high', 'node_down', 'node_behind', 'block_found']) {
      expect(alertMomentFor(alert(`rule_${rule}`))?.pose).not.toBe('found-block')
    }
  })
})

describe('alertMomentFor: alert rules that have no event of their own', () => {
  const table: Array<[string, string]> = [
    ['rule_fan_failure', 'M03'],
    ['rule_temp_high', 'M04'],
    ['rule_hashrate_drop', 'M05'],
    ['rule_fleet_hashrate_drop', 'M06'],
    ['rule_reject_rate_high', 'M07'],
    ['rule_node_down', 'M09'],
    ['rule_node_behind', 'M10'],
  ]
  it.each(table)('%s is moment %s with the alert pose', (rule, id) => {
    const m = alertMomentFor(alert(rule))
    expect(m?.id).toBe(id)
    expect(m?.pose).toBe('alert')
  })

  it('leaves the rules whose events already show Hashling to those events, so nothing pops up twice', () => {
    for (const rule of ['rule_device_offline', 'rule_pool_fallback', 'rule_device_attention']) expect(alertMomentFor(alert(rule)), rule).toBeNull()
  })

  it('shows nothing for a rule it does not know (a custom rule has a random id)', () => {
    expect(alertMomentFor(alert('rule_9f8e7d6c'))).toBeNull()
  })

  it('keeps the alert severity', () => {
    expect(alertMomentFor(alert('rule_temp_high', { severity: 'critical' }))?.severity).toBe('critical')
  })
})

function cand(id: string, over: Partial<Candidate> & { severity?: Severity; pose?: Moment['pose'] } = {}): Candidate {
  const { severity, pose, ...rest } = over
  const attention = /^M(0[1-9]|1[0-2]|1XN)$/.test(id)
  const moment = { id, pose: pose ?? (id === 'M12' ? 'sleeping' : attention ? 'alert' : id === 'M16' ? 'thumbs-up' : id === 'M13' ? 'found-block' : 'celebrate'), severity: severity ?? (attention ? 'warning' : 'success') } as Moment
  return { key: `k-${id}-${rest.deviceId ?? 'none'}-${Math.random()}`, moment, deviceId: null, miner: null, source: null, ...rest }
}

describe('planPopups: one pop-up per window, storms are coalesced', () => {
  it('plans nothing for nothing', () => {
    expect(planPopups([], false)).toEqual([])
  })

  it('keeps a single event as itself and names the miner', () => {
    const [p, ...rest] = planPopups([cand('M02', { deviceId: 'a', miner: 'Garage' })], false)
    expect(rest).toEqual([])
    expect(p).toMatchObject({ id: 'M02', pose: 'alert', vars: { miner: 'Garage' } })
  })

  it('several miners offline at once become ONE M02N that names them', () => {
    const plans = planPopups([cand('M02', { deviceId: 'a', miner: 'A' }), cand('M02', { deviceId: 'b', miner: 'B' })], false)
    expect(plans).toHaveLength(1)
    expect(plans[0]).toMatchObject({ id: 'M02N', pose: 'alert', vars: { count: 2, miners: 'A, B' } })
  })

  it('names two miners and counts the rest with the "{count} more" wording', () => {
    const offline = ['A', 'B', 'C', 'D', 'E'].map((n) => cand('M02', { deviceId: n, miner: n }))
    const [p] = planPopups(offline, false)
    expect(p.vars).toEqual({ count: 5, miners: 'A, B, 3 more' })
    expect(listMiners(['A', 'B', 'C', 'D', 'E'])).toBe('A, B, 3 more')
    expect(listMiners(['A', 'B'])).toBe('A, B')
    expect(listMiners(['A'])).toBe('A')
  })

  it('a storm of mixed warnings becomes ONE M1XN with a count', () => {
    const plans = planPopups([cand('M02', { deviceId: 'a', miner: 'A' }), cand('M04', { deviceId: 'b', miner: 'B' }), cand('M09', { source: 'Node' })], false)
    expect(plans).toHaveLength(1)
    expect(plans[0]).toMatchObject({ id: 'M1XN', pose: 'alert', vars: { count: 3 } })
  })

  it('takes the most serious severity of a storm', () => {
    const [p] = planPopups([cand('M04', { deviceId: 'a', miner: 'A', severity: 'warning' }), cand('M02', { deviceId: 'b', miner: 'B', severity: 'critical' })], false)
    expect(p.severity).toBe('critical')
  })

  it('two moments about the same miner in one window are one: the more specific one wins', () => {
    const plans = planPopups([cand('M11', { deviceId: 'a', miner: 'A' }), cand('M08', { deviceId: 'a', miner: 'A' })], false)
    expect(plans).toHaveLength(1)
    expect(plans[0].id).toBe('M08')
  })

  it('several miners added in one batch become ONE M15N', () => {
    const plans = planPopups([cand('M15', { deviceId: 'a', miner: 'A' }), cand('M15', { deviceId: 'b', miner: 'B' }), cand('M15', { deviceId: 'c', miner: 'C' })], false)
    expect(plans).toHaveLength(1)
    expect(plans[0]).toMatchObject({ id: 'M15N', pose: 'celebrate', vars: { count: 3 } })
  })

  it('one added miner is M15 with its name', () => {
    expect(planPopups([cand('M15', { deviceId: 'a', miner: 'A' })], false)[0]).toMatchObject({ id: 'M15', vars: { miner: 'A' } })
  })

  it('several quiet miners coming back become ONE M16N', () => {
    const plans = planPopups([cand('M16', { deviceId: 'a', miner: 'A' }), cand('M16', { deviceId: 'b', miner: 'B' })], false)
    expect(plans).toHaveLength(1)
    expect(plans[0]).toMatchObject({ id: 'M16N', pose: 'thumbs-up', vars: { count: 2 } })
  })

  it('when the outage is over and every miner hashes, M17 replaces the single "back" pop-up', () => {
    const [p, ...rest] = planPopups([cand('M16', { deviceId: 'a', miner: 'A' })], true)
    expect(rest).toEqual([])
    expect(p).toMatchObject({ id: 'M17', pose: 'thumbs-up' })
  })

  it('M17 also replaces M16N when the last quiet miners return together', () => {
    const plans = planPopups([cand('M16', { deviceId: 'a', miner: 'A' }), cand('M16', { deviceId: 'b', miner: 'B' })], true)
    expect(plans.map((p) => p.id)).toEqual(['M17'])
  })

  it('M17 needs an M16 to replace: a clear outage with nothing coming back shows nothing', () => {
    expect(planPopups([], true)).toEqual([])
    expect(planPopups([cand('M14', { deviceId: 'a', miner: 'A' })], true).map((p) => p.id)).toEqual(['M14'])
  })

  it('a found block is its own pop-up and goes first', () => {
    const plans = planPopups([cand('M02', { deviceId: 'a', miner: 'A' }), cand('M13')], false)
    expect(plans.map((p) => p.id)).toEqual(['M13', 'M02'])
  })

  it('each new best share stays its own pop-up (there is no combined wording for them)', () => {
    const plans = planPopups([cand('M14', { deviceId: 'a', miner: 'A' }), cand('M14', { deviceId: 'b', miner: 'B' })], false)
    expect(plans.map((p) => p.id)).toEqual(['M14', 'M14'])
  })
})

describe('Hashling text', () => {
  it('fills {miner}, {count}, {miners} and {source}', () => {
    expect(fill('{miner} is on', { miner: 'Garage' })).toBe('Garage is on')
    expect(fill('{count} miners: {miners}', { count: 3, miners: 'A, B, 1 more' })).toBe('3 miners: A, B, 1 more')
    expect(fill('{source} stopped', { source: 'My node' })).toBe('My node stopped')
  })

  it('leaves a placeholder visible rather than printing "undefined"', () => {
    expect(fill('{miner} is on', {})).toBe('{miner} is on')
  })

  it('has a title and line for every moment that can pop up, and a line for the static ones', () => {
    const popup = ['M01', 'M02', 'M02N', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08', 'M09', 'M10', 'M11', 'M1XN', 'M12', 'M13', 'M14', 'M15', 'M15N', 'M16', 'M16N', 'M17', 'M21', 'M22', 'M23', 'M24'] as const
    for (const id of popup) {
      expect(HASHLING_MOMENTS[id].title, id).toBeTruthy()
      expect(HASHLING_MOMENTS[id].line, id).toBeTruthy()
    }
    for (const id of ['M18', 'M19', 'M20', 'M25'] as const) expect(HASHLING_MOMENTS[id].line, id).toBeTruthy()
  })

  it('contains Becky\'s wording verbatim (spot checks, including a placeholder line)', () => {
    expect(HASHLING_MOMENTS.M02.line).toBe('{miner} went quiet. Power or Wi-Fi is a good first look.')
    expect(HASHLING_MOMENTS.M13.title).toBe('We found a block')
    expect(HASHLING_MOMENTS.M17.line).toBe('The outage is over. I checked twice. Then once more, for fun.')
    expect(HASHLING_UI.U02).toBe('Hashling pop-ups')
    expect(HASHLING_UI.U04).toBe('Dismiss')
    expect(HASHLING_UI.U05).toBe('{count} more')
  })

  it('only uses the four placeholders the planner fills', () => {
    const all = [...Object.values(HASHLING_MOMENTS).flatMap((m) => [m.title ?? '', m.line]), ...Object.values(HASHLING_UI)]
    for (const text of all) for (const found of text.match(/\{[^}]*\}/g) ?? []) expect(['{miner}', '{count}', '{miners}', '{source}']).toContain(found)
  })

  it('has real alt text for every pose (U01a to U01g), none empty', () => {
    for (const pose of HASHLING_POSES) expect(poseAlt(pose).length, pose).toBeGreaterThan(10)
    expect(poseAlt('alert')).toBe(HASHLING_UI.U01a)
    expect(poseAlt('sleeping')).toBe(HASHLING_UI.U01b)
    expect(poseAlt('found-block')).toBe(HASHLING_UI.U01c)
    expect(poseAlt('celebrate')).toBe(HASHLING_UI.U01d)
    expect(poseAlt('thumbs-up')).toBe(HASHLING_UI.U01e)
    expect(poseAlt('tinkering')).toBe(HASHLING_UI.U01f)
    expect(poseAlt('lottery-ticket')).toBe(HASHLING_UI.U01g)
  })

  it('uses no dashes as punctuation (en or em)', () => {
    const all = [...Object.values(HASHLING_MOMENTS).flatMap((m) => [m.title ?? '', m.line]), ...Object.values(HASHLING_UI)]
    for (const text of all) expect(text).not.toMatch(/[\u2013\u2014]/)
  })

  it('has a pose file URL for each pose', () => {
    for (const pose of HASHLING_POSES) expect(HASHLING_ART[pose]).toBe(`/brand/hashling/hashling-${pose}.svg`)
  })
})

describe('all Hashling words live in one module', () => {
  const SRC = fileURLToPath(new URL('..', import.meta.url))
  function sources(dir: string): string[] {
    return readdirSync(dir).flatMap((name) => {
      const path = join(dir, name)
      if (statSync(path).isDirectory()) return sources(path)
      return /\.(vue|ts)$/.test(name) && !/\.test\.ts$/.test(name) && !path.endsWith(join('lib', 'hashlingText.ts')) ? [path] : []
    })
  }

  it('no other source file repeats a Hashling line', () => {
    const lines = [...Object.values(HASHLING_MOMENTS).map((m) => m.line), HASHLING_UI.U03]
    for (const file of sources(SRC)) {
      const text = readFileSync(file, 'utf8')
      for (const line of lines) expect(text.includes(line), `${file} repeats "${line}"`).toBe(false)
    }
  })
})

describe('card 2362: the one joke on the Odds page (M25)', () => {
  it('has exactly one such spot on the Odds page, and none on the other pages that show numbers', () => {
    const read = (name: string): string => readFileSync(fileURLToPath(new URL(`../pages/${name}`, import.meta.url)), 'utf8')
    const odds = read('OddsPage.vue')
    expect(odds.match(/<HashlingNote/g)).toHaveLength(1)
    expect(odds).toContain('moment="M25"')
    for (const page of ['BitcoinPage.vue', 'AnalyticsPage.vue', 'AlertsPage.vue', 'LoginPage.vue', 'NotFoundPage.vue', 'SoloBlocksPage.vue']) {
      expect(read(page), page).not.toMatch(/Hashling/)
    }
  })
})
