/**
 * Number formatting for humans. Mirrors `src/bsmm/units.py` so the dashboard, the CLI and AI agents
 * all say the same thing ("4.73 TH/s", "1 in 1,480", "3d 4h").
 */

export type TempUnit = 'c' | 'f'
export type HashrateUnitPref = 'auto' | 'th' | 'gh' | 'ph'

const SI: [number, string][] = [
  [1e21, 'Z'],
  [1e18, 'E'],
  [1e15, 'P'],
  [1e12, 'T'],
  [1e9, 'G'],
  [1e6, 'M'],
  [1e3, 'k'],
]

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

/** Significant digits, but never more decimals than needed (`4.7`, not `4.70`). */
export function sig(x: number, digits = 3): string {
  if (x === 0) return '0'
  const magnitude = Math.floor(Math.log10(Math.abs(x)))
  const decimals = Math.max(0, digits - 1 - magnitude)
  let s = x.toFixed(decimals)
  if (s.includes('.')) s = s.replace(/0+$/, '').replace(/\.$/, '')
  return s
}

export interface Quantity {
  value: string
  unit: string
}

/** `4_726_646_000_000` -> `{ value: '4.73', unit: 'T' }` */
export function splitSI(value: number | null | undefined, digits = 3): Quantity {
  if (!isNum(value)) return { value: '–', unit: '' }
  const sign = value < 0 ? '-' : ''
  const v = Math.abs(value)
  for (const [factor, prefix] of SI) {
    if (v >= factor) return { value: sign + sig(v / factor, digits), unit: prefix }
  }
  return { value: sign + sig(v, digits), unit: '' }
}

export function formatSI(value: number | null | undefined, unit = '', digits = 3): string {
  if (!isNum(value)) return '–'
  const q = splitSI(value, digits)
  return `${q.value} ${q.unit}${unit}`.trim()
}

/** Hashrate split into a big value and a small unit, honouring the user's unit preference. */
export function splitHashrate(hs: number | null | undefined, pref: HashrateUnitPref = 'auto', digits = 3): Quantity {
  if (!isNum(hs)) return { value: '–', unit: 'H/s' }
  const fixed = { th: [1e12, 'TH/s'], gh: [1e9, 'GH/s'], ph: [1e15, 'PH/s'] } as const
  if (pref !== 'auto') {
    const [factor, unit] = fixed[pref]
    return { value: sig(hs / factor, digits), unit }
  }
  const q = splitSI(hs, digits)
  return { value: q.value, unit: `${q.unit}H/s` }
}

export function formatHashrate(hs: number | null | undefined, pref: HashrateUnitPref = 'auto', digits = 3): string {
  const q = splitHashrate(hs, pref, digits)
  return isNum(hs) ? `${q.value} ${q.unit}` : '–'
}

export function formatDifficulty(d: number | null | undefined, digits = 3): string {
  return formatSI(d, '', digits)
}

const YEAR = 365.25 * 86400
const DURATION_UNITS: [string, number][] = [
  ['y', YEAR],
  ['mo', 30.4375 * 86400],
  ['d', 86400],
  ['h', 3600],
  ['m', 60],
  ['s', 1],
]

/** `90061` -> `1d 1h`; huge values become years (`1,595 years`). */
export function formatDuration(seconds: number | null | undefined, parts = 2): string {
  if (!isNum(seconds)) return '–'
  let s = Math.max(0, seconds)
  if (s < 1) return '<1s'
  if (s >= 1000 * YEAR) return `${Math.round(s / YEAR).toLocaleString('en-US')} years`
  if (s >= 10 * YEAR) return `${(s / YEAR).toLocaleString('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 1 })} years`
  const start = Math.max(0, DURATION_UNITS.findIndex(([, size]) => s >= size))
  const out: [string, number][] = []
  for (const [label, size] of DURATION_UNITS.slice(start, start + parts)) {
    const n = Math.floor(s / size)
    s -= n * size
    out.push([label, n])
  }
  while (out.length > 1 && out[out.length - 1]![1] === 0) out.pop()
  return out.map(([label, n]) => `${n}${label}`).join(' ')
}

/** 0.000582 -> `1 in 1,718`. */
export function formatOdds(probability: number | null | undefined): string {
  if (!isNum(probability) || probability <= 0) return '–'
  if (probability >= 1) return 'certain'
  const oneIn = 1 / probability
  if (oneIn >= 1e15) return `1 in ${oneIn.toExponential(2)}`
  if (oneIn >= 100) return `1 in ${Math.round(oneIn).toLocaleString('en-US')}`
  return `1 in ${oneIn.toLocaleString('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 1 })}`
}

/** Input is a fraction (0.0123 = 1.23%). Tiny values switch to scientific notation instead of "0.00%". */
export function formatFraction(fraction: number | null | undefined, digits = 2): string {
  if (!isNum(fraction)) return '–'
  const pct = fraction * 100
  if (pct === 0) return '0%'
  if (Math.abs(pct) < 10 ** -digits) return `${pct.toExponential(1)}%`
  return `${pct.toFixed(digits)}%`
}

/** Input is already a percentage (45.2 = 45.2%). */
export function formatPercent(pct: number | null | undefined, digits = 1): string {
  if (!isNum(pct)) return '–'
  return `${pct.toFixed(digits)}%`
}

export function formatNumber(n: number | null | undefined, digits = 0): string {
  if (!isNum(n)) return '–'
  return n.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: 0 })
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!isNum(bytes)) return '–'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = bytes
  let i = 0
  while (v >= 1000 && i < units.length - 1) {
    v /= 1000
    i++
  }
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`
}

export function toDisplayTemp(c: number | null | undefined, unit: TempUnit): number | null {
  if (!isNum(c)) return null
  return unit === 'f' ? c * 1.8 + 32 : c
}

export function formatTemp(c: number | null | undefined, unit: TempUnit = 'c', digits = 0): string {
  const v = toDisplayTemp(c, unit)
  if (v === null) return '–'
  return `${v.toFixed(digits)}°${unit === 'f' ? 'F' : 'C'}`
}

export function formatPower(w: number | null | undefined): string {
  if (!isNum(w)) return '–'
  if (Math.abs(w) >= 1000) return `${sig(w / 1000, 3)} kW`
  return `${w >= 100 ? Math.round(w) : w.toFixed(1)} W`
}

export function splitPower(w: number | null | undefined): Quantity {
  if (!isNum(w)) return { value: '–', unit: 'W' }
  if (Math.abs(w) >= 1000) return { value: sig(w / 1000, 3), unit: 'kW' }
  return { value: w >= 100 ? String(Math.round(w)) : w.toFixed(1), unit: 'W' }
}

export function formatEfficiency(jth: number | null | undefined): string {
  if (!isNum(jth)) return '–'
  return `${jth >= 100 ? Math.round(jth) : jth.toFixed(1)} J/TH`
}

export function formatMoney(amount: number | null | undefined, currency = 'USD', digits?: number): string {
  if (!isNum(amount)) return '–'
  try {
    const abs = Math.abs(amount)
    const d = digits ?? (abs >= 1000 ? 0 : abs >= 10 ? 2 : abs >= 0.01 ? 2 : 4)
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: d, minimumFractionDigits: Math.min(d, 2) }).format(amount)
  } catch {
    return `${amount.toFixed(2)} ${currency}`
  }
}

export function formatBtc(btc: number | null | undefined, digits = 4): string {
  if (!isNum(btc)) return '–'
  return `₿ ${btc.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: 0 })}`
}

export function formatSats(sats: number | null | undefined): string {
  if (!isNum(sats)) return '–'
  return `${sats.toLocaleString('en-US')} sats`
}

/** `bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq` -> `bc1qar0s…zwf5mdq` */
export function shortAddress(addr: string | null | undefined, head = 8, tail = 6): string {
  if (!addr) return '–'
  return addr.length <= head + tail + 1 ? addr : `${addr.slice(0, head)}…${addr.slice(-tail)}`
}

export function shortHash(h: string | null | undefined, head = 6, tail = 6): string {
  if (!h) return '–'
  const trimmed = h.replace(/^0+/, '')
  const base = trimmed.length < 12 ? h : trimmed
  return base.length <= head + tail + 1 ? base : `${base.slice(0, head)}…${base.slice(-tail)}`
}

/** Seconds-since-epoch -> "5s ago", "3m ago", "2h ago", "4d ago". */
export function formatAgo(ts: number | null | undefined, now = Date.now() / 1000): string {
  if (!isNum(ts)) return 'never'
  const d = Math.max(0, now - ts)
  if (d < 5) return 'just now'
  if (d < 60) return `${Math.floor(d)}s ago`
  if (d < 3600) return `${Math.floor(d / 60)}m ago`
  if (d < 86400) return `${Math.floor(d / 3600)}h ago`
  if (d < 86400 * 60) return `${Math.floor(d / 86400)}d ago`
  return `${Math.floor(d / (86400 * 30.4375))}mo ago`
}

/** "in 3d 4h" for future timestamps, "3d 4h ago" for past ones. */
export function formatWhen(ts: number | null | undefined, now = Date.now() / 1000): string {
  if (!isNum(ts)) return '–'
  return ts > now ? `in ${formatDuration(ts - now)}` : formatAgo(ts, now)
}

export function formatDateTime(ts: number | null | undefined, opts: Intl.DateTimeFormatOptions = {}): string {
  if (!isNum(ts)) return '–'
  return new Date(ts * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short', ...opts })
}

export function formatDate(ts: number | string | null | undefined): string {
  if (ts === null || ts === undefined) return '–'
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  if (Number.isNaN(d.getTime())) return '–'
  return d.toLocaleDateString(undefined, { dateStyle: 'medium' })
}

export function formatTime(ts: number | null | undefined): string {
  if (!isNum(ts)) return '–'
  return new Date(ts * 1000).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export function formatUptime(seconds: number | null | undefined): string {
  return isNum(seconds) ? formatDuration(seconds, 2) : '–'
}

/** Clamp a number into [lo, hi]. */
export const clamp = (x: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, x))

/** Plural helper: `plural(3, 'miner')` -> `3 miners`. */
export function plural(n: number, word: string, many = `${word}s`): string {
  return `${formatNumber(n)} ${n === 1 ? word : many}`
}

/** Tailwind-free helper that maps a temperature to a severity level for colouring. */
export function tempLevel(c: number | null | undefined, warn = 75, crit = 85): 'ok' | 'warn' | 'crit' | 'none' {
  if (!isNum(c)) return 'none'
  if (c >= crit) return 'crit'
  if (c >= warn) return 'warn'
  return 'ok'
}
