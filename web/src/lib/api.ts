/**
 * Thin typed client for the REST API. Every failure becomes an `ApiError` carrying the server's stable
 * `code`, a plain-English `message` and a `hint` that says what to do next.
 */
import type {
  ActionResult,
  AlertRule,
  ActiveAlert,
  ApiToken,
  AppEvent,
  AuditEntry,
  BlockInfo,
  Channel,
  ChannelType,
  ConnectionTest,
  CreatedToken,
  Device,
  DeviceHistoryResult,
  DeviceView,
  Diagnostics,
  DiscoveryJob,
  FleetSummary,
  FoundBlock,
  HistoryResult,
  ImplicitSource,
  Insight,
  Me,
  Meta,
  NetworkState,
  NodeStatus,
  Odds,
  PoolStatus,
  RuleType,
  Scope,
  SendResult,
  Settings,
  Source,
  SourceKind,
  SystemInfo,
  TuningInfo,
  UpdateStatus,
} from './types'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly hint: string | null
  readonly details: unknown

  constructor(status: number, code: string, message: string, hint: string | null = null, details: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.hint = hint
    this.details = details
  }

  get isAuth(): boolean {
    return this.status === 401
  }

  /** The server could not be reached at all (as opposed to answering with an error). */
  get isNetwork(): boolean {
    return this.code === 'network'
  }
}

type Query = Record<string, string | number | boolean | null | undefined | string[]>

interface RequestOptions {
  query?: Query
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
}

export const API_BASE = '/api/v1'

/** Called whenever the server answers 401, so the session store can send the user to the login page. */
let unauthorizedHandler: ((err: ApiError) => void) | null = null
export function onUnauthorized(fn: ((err: ApiError) => void) | null): void {
  unauthorizedHandler = fn
}

function qs(query?: Query): string {
  if (!query) return ''
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue
    p.set(k, Array.isArray(v) ? v.join(',') : String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

export async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE}${path}${qs(opts.query)}`
  const headers: Record<string, string> = { Accept: 'application/json' }
  let body: BodyInit | undefined
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(new DOMException('timeout', 'TimeoutError')), opts.timeoutMs ?? 30_000)
  opts.signal?.addEventListener('abort', () => controller.abort(opts.signal?.reason))

  let res: Response
  try {
    res = await fetch(url, { method, headers, body, credentials: 'same-origin', signal: controller.signal })
  } catch (e) {
    if (opts.signal?.aborted) throw e
    const timedOut = e instanceof DOMException && e.name === 'TimeoutError'
    throw new ApiError(0, 'network', timedOut ? 'The server took too long to answer.' : 'Could not reach the server.', 'Check that Solo Miner Monitor is still running.')
  } finally {
    clearTimeout(timer)
  }

  if (res.status === 204) return undefined as T
  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }
  if (!res.ok) {
    const e = (data as { error?: { code?: string; message?: string; hint?: string; details?: unknown } } | null)?.error
    const err = new ApiError(res.status, e?.code ?? `http_${res.status}`, e?.message ?? (text.slice(0, 200) || res.statusText), e?.hint ?? null, e?.details ?? null)
    if (res.status === 401 && unauthorizedHandler) unauthorizedHandler(err)
    throw err
  }
  return data as T
}

const get = <T>(path: string, query?: Query, signal?: AbortSignal) => request<T>('GET', path, { query, signal })
const post = <T>(path: string, body?: unknown, query?: Query) => request<T>('POST', path, { body, query })
const patch = <T>(path: string, body: unknown) => request<T>('PATCH', path, { body })
const del = <T>(path: string, query?: Query) => request<T>('DELETE', path, { query })

// ------------------------------------------------------------------------------------------------ endpoints

export interface Overview {
  summary: FleetSummary
  odds: Odds
  network: NetworkState
  alerts: ActiveAlert[]
  events: AppEvent[]
  blocks_found: FoundBlock[]
  leaderboard: { device_id: string; difficulty: number; ts: number }[]
  demo: boolean
}

export interface HistoryQuery {
  range?: string
  metrics: string[]
  step?: number
  start?: number
  end?: number
  per_device?: boolean
}

export interface RuleBody {
  kind: string
  name?: string
  enabled?: boolean
  severity?: string
  scope?: AlertRule['scope']
  params?: Record<string, unknown>
  channel_ids?: string[]
  cooldown_s?: number
}

export interface ChannelBody {
  kind: string
  name: string
  config?: Record<string, unknown>
  secret?: Record<string, string>
  enabled?: boolean
  min_severity?: string
}

export interface SourceBody {
  kind: string
  name?: string
  url?: string | null
  secret?: Record<string, string>
  options?: Record<string, unknown>
  enabled?: boolean
}

export interface UpdateDeviceBody {
  name?: string
  tags?: string[]
  group?: string | null
  notes?: string | null
  enabled?: boolean
  allow_control?: boolean
  poll_interval_s?: number | null
  model_override?: string | null
  host?: string
  port?: number
  power_override_w?: number | null
}

export const api = {
  // system
  health: () => get<{ status: string; version: string; uptime_s: number }>('/health'),
  meta: () => get<Meta>('/meta'),
  me: () => get<Me>('/auth/me'),
  systemInfo: () => get<SystemInfo>('/system/info'),
  diagnostics: () => get<Diagnostics>('/system/diagnostics'),
  updateStatus: () => get<UpdateStatus>('/system/update'),
  checkUpdate: () => post<UpdateStatus>('/system/update/check'),
  exportConfig: () => get<Record<string, unknown>>('/system/export'),
  importConfig: (data: Record<string, unknown>) => post<{ ok: boolean; added: Record<string, number>; note: string }>('/system/import', data),

  // overview & fleet
  overview: (signal?: AbortSignal) => get<Overview>('/overview', undefined, signal),
  fleet: () => get<FleetSummary>('/fleet'),
  fleetHistory: (q: HistoryQuery, signal?: AbortSignal) =>
    get<HistoryResult>('/fleet/history', { range: q.range, metrics: q.metrics, step: q.step, start: q.start, end: q.end, per_device: q.per_device }, signal),
  insights: () => get<{ insights: Insight[] }>('/insights').then((r) => r.insights),
  dismissInsight: (id: string) => post<{ ok: boolean }>(`/insights/${encodeURIComponent(id)}/dismiss`),

  // devices
  devices: () => get<DeviceView[]>('/devices'),
  device: (id: string) => get<DeviceView>(`/devices/${id}`),
  addDevice: (b: { host: string; port?: number; name?: string; tags?: string[]; group?: string }) =>
    post<{ created: boolean; merged: boolean; note: string | null; device: DeviceView }>('/devices', b),
  updateDevice: (id: string, b: UpdateDeviceBody) => patch<DeviceView>(`/devices/${id}`, b),
  removeDevice: (id: string, keepHistory = false) => del<{ ok: boolean }>(`/devices/${id}`, { keep_history: keepHistory }),
  pollDevice: (id: string) => post<DeviceView>(`/devices/${id}/poll`),
  deviceHistory: (id: string, q: { range?: string; metrics: string[]; step?: number }, signal?: AbortSignal) =>
    get<DeviceHistoryResult>(`/devices/${id}/history`, { range: q.range, metrics: q.metrics, step: q.step }, signal),
  deviceRaw: (id: string) => get<{ driver: string; raw: unknown }>(`/devices/${id}/raw`),
  deviceTuning: (id: string) => get<TuningInfo>(`/devices/${id}/tuning`),
  deviceAudit: (id: string, limit = 50) => get<{ audit: AuditEntry[] }>(`/devices/${id}/audit`, { limit }).then((r) => r.audit),
  action: (id: string, action: string, params: Record<string, unknown> = {}, dryRun = false) =>
    post<ActionResult>(`/devices/${id}/actions/${action}`, { params, dry_run: dryRun }),
  bulkAction: (b: { action: string; params?: Record<string, unknown>; device_ids?: string[]; tag?: string; all?: boolean; dry_run: boolean }) =>
    post<{ dry_run: boolean; results: ActionResult[]; ok: boolean }>('/devices/actions', b),

  // discovery
  suggestRanges: () => get<{ cidrs: string[] }>('/discovery/suggest').then((r) => r.cidrs),
  startDiscovery: (b: { cidrs?: string[]; ports?: number[]; include_sources?: boolean }) => post<DiscoveryJob>('/discovery', b),
  discovery: (id: string) => get<DiscoveryJob>(`/discovery/${id}`),
  cancelDiscovery: (id: string) => del<{ ok: boolean }>(`/discovery/${id}`),
  adopt: (id: string, b: { keys?: string[]; tags?: string[] }) =>
    post<{ added: DeviceView[]; merged: { device: string; note: string }[] }>(`/discovery/${id}/adopt`, b),

  // bitcoin
  network: () => get<NetworkState>('/network'),
  node: () => get<{ configured: boolean; node: NodeStatus | null; behind_by: number | null }>('/node'),
  pool: () => get<{ pools: PoolStatus[] }>('/pool'),
  recentBlocks: () => get<{ blocks: BlockInfo[] }>('/blocks/recent').then((r) => r.blocks),
  blocksFound: () => get<{ count: number; total_reward_sats: number; blocks: FoundBlock[] }>('/blocks/found'),
  odds: (q: { hashrate_ths?: number; difficulty?: number; power_w?: number; growth?: number } = {}, signal?: AbortSignal) =>
    get<Odds>('/odds', q, signal),

  // sources
  sourceKinds: () => get<{ kinds: SourceKind[] }>('/sources/kinds').then((r) => r.kinds),
  sources: () => get<{ sources: Source[]; implicit: ImplicitSource[] }>('/sources'),
  testSource: (b: SourceBody) => post<ConnectionTest>('/sources/test', b),
  addSource: (b: SourceBody, force = false) => post<{ source: Source; test: ConnectionTest }>('/sources', b, { force }),
  updateSource: (id: string, b: Partial<SourceBody>) => patch<{ source: Source }>(`/sources/${id}`, b),
  deleteSource: (id: string) => del<{ ok: boolean }>(`/sources/${id}`),

  // alerts, events
  events: (q: { limit?: number; before_id?: number | null; type?: string; device_id?: string; min_severity?: string; unacked?: boolean } = {}) =>
    get<{ events: AppEvent[]; next_before_id: number | null }>('/events', q),
  ackEvent: (id: number) => post<{ ok: boolean }>(`/events/${id}/ack`),
  ackAllEvents: () => post<{ acknowledged: number }>('/events/ack-all'),
  ruleTypes: () => get<{ rule_types: RuleType[] }>('/alerts/rule-types').then((r) => r.rule_types),
  rules: () => get<{ rules: AlertRule[] }>('/alerts/rules').then((r) => r.rules),
  createRule: (b: RuleBody) => post<{ rule: AlertRule }>('/alerts/rules', b).then((r) => r.rule),
  updateRule: (id: string, b: Partial<RuleBody>) => patch<{ rule: AlertRule }>(`/alerts/rules/${id}`, b).then((r) => r.rule),
  deleteRule: (id: string) => del<{ ok: boolean }>(`/alerts/rules/${id}`),
  activeAlerts: () => get<{ active: ActiveAlert[] }>('/alerts/active').then((r) => r.active),

  // notifications
  channelTypes: () => get<{ channel_types: ChannelType[] }>('/notifications/channel-types').then((r) => r.channel_types),
  channels: () => get<{ channels: Channel[] }>('/notifications/channels').then((r) => r.channels),
  createChannel: (b: ChannelBody) => post<{ channel: Channel }>('/notifications/channels', b).then((r) => r.channel),
  updateChannel: (id: string, b: Partial<ChannelBody>) => patch<{ channel: Channel }>(`/notifications/channels/${id}`, b).then((r) => r.channel),
  deleteChannel: (id: string) => del<{ ok: boolean }>(`/notifications/channels/${id}`),
  testChannel: (id: string) => post<SendResult>(`/notifications/channels/${id}/test`),
  testChannelInline: (b: ChannelBody) => post<SendResult>('/notifications/test', b),

  // settings & auth
  settings: () => get<Settings>('/settings'),
  updateSettings: (patchBody: Record<string, unknown>) => patch<Settings>('/settings', patchBody),
  login: (password: string) => post<{ ok: boolean }>('/auth/login', { password }),
  logout: () => post<{ ok: boolean }>('/auth/logout'),
  setPassword: (b: { new_password: string; current_password?: string; enable?: boolean }) =>
    post<{ ok: boolean; auth_mode: string }>('/auth/password', b),
  tokens: () => get<{ tokens: ApiToken[] }>('/auth/tokens').then((r) => r.tokens),
  createToken: (b: { name: string; scope: Scope; expires_days?: number | null }) => post<CreatedToken>('/auth/tokens', b),
  deleteToken: (id: string) => del<{ ok: boolean }>(`/auth/tokens/${id}`),

  // demo
  demoScenario: (scenario: string, device?: string) => post<{ ok: boolean }>('/demo/scenario', { scenario, device }),
}

/** Plain text endpoints that live outside /api/v1. */
export async function fetchText(path: string): Promise<string> {
  const res = await fetch(path, { credentials: 'same-origin' })
  if (!res.ok) throw new ApiError(res.status, `http_${res.status}`, res.statusText)
  return res.text()
}

/** Turn anything thrown into a short sentence a person can act on. */
export function describeError(e: unknown): string {
  if (e instanceof ApiError) return e.hint && !e.message.includes(e.hint) ? `${e.message} ${e.hint}` : e.message
  if (e instanceof Error) return e.message
  return String(e)
}

export type { Device }
