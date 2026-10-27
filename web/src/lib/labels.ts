/** Human names for things the API reports with machine identifiers. */
import type { AppEvent, Severity } from './types'

const SOURCES: Record<string, string> = {
  bitcoin_core: 'your node',
  public_pool: 'your pool',
  ckpool: 'ckpool',
  mempool_space: 'mempool.space',
  device: 'your miners',
  demo: 'demo data',
}

export function sourceLabel(source: string | null | undefined): string {
  if (!source) return 'unknown'
  return SOURCES[source] ?? source
}

const KINDS: Record<string, string> = {
  bitcoin_core: 'Bitcoin Core node',
  public_pool: 'Public Pool',
  ckpool: 'ckpool solo',
  mempool_space: 'mempool.space',
  demo: 'Demo data',
}
export function kindLabel(kind: string): string {
  return KINDS[kind] ?? kind
}

const FAMILIES: Record<string, string> = {
  bitaxe: 'Bitaxe',
  nerdqaxe: 'NerdQAxe',
  luckyminer: 'LuckyMiner',
  magicminer: 'Magic Miner',
  avalon: 'Avalon',
  antminer: 'Antminer',
  cgminer: 'cgminer-based',
  axeos: 'AxeOS',
  sim: 'Simulated',
}
export function familyLabel(family: string): string {
  return FAMILIES[family] ?? family
}

export const EVENT_LABELS: Record<string, string> = {
  device_offline: 'Went offline',
  device_online: 'Back online',
  device_degraded: 'Needs attention',
  device_restarted: 'Restarted',
  new_best_share: 'New best share',
  block_found: 'Block found',
  difficulty_adjusted: 'Difficulty change',
  firmware_changed: 'Firmware changed',
  pool_fallback: 'Using fallback pool',
  node_down: 'Node unreachable',
  node_behind: 'Node behind',
  custom_notification: 'Message',
}

export function eventLabel(e: Pick<AppEvent, 'type'>): string {
  return EVENT_LABELS[e.type] ?? e.type.replace(/_/g, ' ')
}

export const SEVERITY_ORDER: Severity[] = ['critical', 'warning', 'success', 'info']

/** Short, friendly name for how a rule scope reads in lists. */
export function scopeLabel(scope: { all?: boolean; device_ids?: string[]; tags?: string[] }, deviceName: (id: string) => string): string {
  if (scope.all || (!scope.device_ids?.length && !scope.tags?.length)) return 'All miners'
  const parts: string[] = []
  if (scope.device_ids?.length) parts.push(scope.device_ids.map(deviceName).join(', '))
  if (scope.tags?.length) parts.push(`tagged ${scope.tags.join(', ')}`)
  return parts.join(' + ')
}
