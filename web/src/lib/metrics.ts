import type { Fmt } from '@/composables/useFmt'

/** What the history API can chart, with a friendly name, a colour token and how to print a value. */
export type MetricKind = 'hashrate' | 'power' | 'temp' | 'percent' | 'efficiency' | 'rpm' | 'mhz' | 'mv' | 'volt' | 'amp' | 'dbm' | 'ms' | 'bytes' | 'count' | 'difficulty' | 'seconds' | 'flag'

export interface MetricMeta {
  key: string
  label: string
  kind: MetricKind
  /** CSS variable or hex; resolved at draw time because canvases cannot read var() */
  color: string
  help?: string
}

export const METRIC_LIST: MetricMeta[] = [
  { key: 'hashrate_hs', label: 'Hashrate', kind: 'hashrate', color: 'var(--accent)', help: 'How many guesses per second' },
  { key: 'power_w', label: 'Power', kind: 'power', color: 'var(--info)', help: 'Electricity used' },
  { key: 'efficiency_j_th', label: 'Efficiency', kind: 'efficiency', color: 'var(--ok)', help: 'Joules per terahash. Lower is better' },
  { key: 'temp_asic_c', label: 'ASIC temperature', kind: 'temp', color: 'var(--bad)' },
  { key: 'temp_vr_c', label: 'Regulator temperature', kind: 'temp', color: 'var(--warn)' },
  { key: 'temp_board_c', label: 'Board temperature', kind: 'temp', color: '#f472b6' },
  { key: 'fan_pct', label: 'Fan speed', kind: 'percent', color: '#22d3ee' },
  { key: 'fan_rpm', label: 'Fan speed (rpm)', kind: 'rpm', color: '#22d3ee' },
  { key: 'frequency_mhz', label: 'Frequency', kind: 'mhz', color: 'var(--violet)' },
  { key: 'core_voltage_mv', label: 'Core voltage', kind: 'mv', color: '#f472b6' },
  { key: 'voltage_in_v', label: 'Input voltage', kind: 'volt', color: 'var(--warn)' },
  { key: 'current_a', label: 'Input current', kind: 'amp', color: 'var(--info)' },
  { key: 'hw_error_pct', label: 'Hardware errors', kind: 'percent', color: 'var(--bad)' },
  { key: 'reject_rate_pct', label: 'Rejected shares', kind: 'percent', color: 'var(--warn)' },
  { key: 'wifi_rssi_dbm', label: 'WiFi signal', kind: 'dbm', color: '#22d3ee' },
  { key: 'pool_ping_ms', label: 'Pool latency', kind: 'ms', color: 'var(--violet)' },
  { key: 'free_heap_bytes', label: 'Free memory', kind: 'bytes', color: 'var(--ok)' },
  { key: 'shares_accepted', label: 'Accepted shares', kind: 'count', color: 'var(--ok)' },
  { key: 'shares_rejected', label: 'Rejected shares (count)', kind: 'count', color: 'var(--bad)' },
  { key: 'best_diff', label: 'Best share', kind: 'difficulty', color: 'var(--accent)' },
  { key: 'uptime_s', label: 'Uptime', kind: 'seconds', color: 'var(--info)' },
  { key: 'online', label: 'Miners online', kind: 'flag', color: 'var(--ok)' },
]

export const METRICS: Record<string, MetricMeta> = Object.fromEntries(METRIC_LIST.map((m) => [m.key, m]))

/** `temp_asic_c:max` -> the base metric's meta. */
export function metricMeta(spec: string): MetricMeta | undefined {
  return METRICS[spec.split(':')[0] ?? spec]
}

export function formatMetric(kind: MetricKind, v: number, fmt: Fmt): string {
  switch (kind) {
    case 'hashrate':
      return fmt.hashrate(v)
    case 'power':
      return fmt.formatPower(v)
    case 'temp':
      return fmt.temp(v, 1)
    case 'percent':
      return `${v.toFixed(v < 10 ? 2 : 1)}%`
    case 'efficiency':
      return fmt.formatEfficiency(v)
    case 'rpm':
      return `${Math.round(v).toLocaleString('en-US')} rpm`
    case 'mhz':
      return `${Math.round(v)} MHz`
    case 'mv':
      return `${Math.round(v)} mV`
    case 'volt':
      return `${v.toFixed(2)} V`
    case 'amp':
      return `${v.toFixed(2)} A`
    case 'dbm':
      return `${Math.round(v)} dBm`
    case 'ms':
      return `${Math.round(v)} ms`
    case 'bytes':
      return fmt.formatBytes(v)
    case 'count':
      return fmt.formatNumber(v)
    case 'difficulty':
      return fmt.formatDifficulty(v)
    case 'seconds':
      return fmt.formatDuration(v)
    case 'flag':
      return String(Math.round(v * 10) / 10)
  }
}

/** Axis labels want short text ("12 TH/s", "62°"). */
export function formatAxis(kind: MetricKind, v: number, fmt: Fmt): string {
  switch (kind) {
    case 'hashrate':
      return fmt.splitHash(v, 3).value + ' ' + fmt.splitHash(v, 3).unit
    case 'temp':
      return `${fmt.tempValue(v, 0)}°`
    case 'power':
      return fmt.formatPower(v)
    case 'percent':
      return `${Math.round(v * 10) / 10}%`
    default:
      return formatMetric(kind, v, fmt)
  }
}

/** Same hue family for N devices drawn on one chart. */
export const DEVICE_COLORS = ['var(--accent)', 'var(--info)', 'var(--ok)', 'var(--violet)', '#f472b6', '#22d3ee', 'var(--warn)', 'var(--bad)', '#a3e635', '#fb923c']

export const RANGES: { value: string; label: string; seconds: number }[] = [
  { value: '1h', label: '1h', seconds: 3600 },
  { value: '6h', label: '6h', seconds: 6 * 3600 },
  { value: '24h', label: '24h', seconds: 86400 },
  { value: '7d', label: '7d', seconds: 7 * 86400 },
  { value: '30d', label: '30d', seconds: 30 * 86400 },
  { value: '90d', label: '90d', seconds: 90 * 86400 },
  { value: '1y', label: '1y', seconds: 365 * 86400 },
]
