/**
 * Types for the Solo Miner Monitor REST API (v1). They mirror the Python models in
 * `src/bsmm/models.py`, `settings.py` and the route modules. Field names carry their unit.
 */

export type DeviceStatus = 'online' | 'degraded' | 'offline' | 'paused' | 'unknown' | 'disabled'
export type Severity = 'info' | 'success' | 'warning' | 'critical'
export type Scope = 'read' | 'control' | 'admin'

export type Capability =
  | 'restart'
  | 'identify'
  | 'pause'
  | 'set_pool'
  | 'set_fan'
  | 'set_frequency'
  | 'set_voltage'
  | 'set_hostname'
  | 'scoreboard'
  | 'history'

export interface PoolInfo {
  role: string
  url: string | null
  port: number | null
  user: string | null
  address: string | null
  worker: string | null
  active: boolean | null
  connected: boolean | null
  difficulty: number | null
  ping_ms: number | null
  tls: boolean | null
  protocol: string | null
}

export interface Telemetry {
  ts: number
  online: boolean
  hashrate_hs: number | null
  hashrate_1m_hs: number | null
  hashrate_10m_hs: number | null
  hashrate_1h_hs: number | null
  hashrate_1d_hs: number | null
  hashrate_avg_hs: number | null
  hashrate_expected_hs: number | null
  hw_error_pct: number | null
  power_w: number | null
  power_source: string | null
  voltage_in_v: number | null
  current_a: number | null
  efficiency_j_th: number | null
  temp_asic_c: number | null
  temp_vr_c: number | null
  temp_board_c: number | null
  fan_pct: number | null
  fan_rpm: number | null
  fan2_rpm: number | null
  frequency_mhz: number | null
  frequency_actual_mhz: number | null
  core_voltage_mv: number | null
  core_voltage_actual_mv: number | null
  shares_accepted: number | null
  shares_rejected: number | null
  reject_rate_pct: number | null
  best_diff: number | null
  best_session_diff: number | null
  rejected_reasons: Record<string, number> | null
  pools: PoolInfo[]
  using_fallback: boolean | null
  pool_connected: boolean | null
  pool_difficulty: number | null
  pool_ping_ms: number | null
  uptime_s: number | null
  firmware: string | null
  wifi_rssi_dbm: number | null
  free_heap_bytes: number | null
  cpu_usage_pct: number | null
  mining_paused: boolean | null
  overheat: boolean | null
  fault: string | null
  blocks_found: number | null
  block_height: number | null
  network_difficulty: number | null
}

export interface Device {
  id: string
  name: string
  driver: string
  family: string
  model: string
  host: string
  port: number
  mac: string | null
  hostname: string | null
  serial: string | null
  firmware: string | null
  asic_model: string | null
  asic_count: number | null
  board_version: string | null
  capabilities: Capability[]
  tags: string[]
  group: string | null
  notes: string | null
  enabled: boolean
  allow_control: boolean
  poll_interval_s: number | null
  model_override: string | null
  created_at: number
  last_seen_at: number | null
  alt_hosts: string[]
  extra: Record<string, unknown>
}

export interface DeviceView extends Device {
  status: DeviceStatus
  status_since: number | null
  status_reason: string | null
  consecutive_failures: number
  last_error: string | null
  telemetry: Telemetry | null
  web_url: string | null
  hashrate_smooth_hs: number | null
  spark_hashrate_hs: (number | null)[]
  last_poll_ms: number | null
}

export interface PoolUsage {
  endpoint: string
  devices: number
  is_fallback: boolean
}

export interface FleetSummary {
  updated_at: number
  devices_total: number
  devices_online: number
  devices_degraded: number
  devices_offline: number
  devices_paused: number
  hashrate_hs: number
  hashrate_raw_hs: number
  expected_hashrate_hs: number | null
  /** actual / expected, counting only miners that report an expectation */
  performance_pct: number | null
  power_w: number | null
  power_wall_w: number | null
  efficiency_j_th: number | null
  temp_avg_c: number | null
  temp_max_c: number | null
  shares_accepted: number
  shares_rejected: number
  reject_rate_pct: number | null
  best_diff: number | null
  best_diff_device_id: string | null
  best_session_diff: number | null
  blocks_found_by_devices: number
  pools: PoolUsage[]
  addresses: string[]
  demo: boolean
}

// ----------------------------------------------------------------------------------- Bitcoin network

export interface BlockInfo {
  hash: string
  height: number
  ts: number
  tx_count: number | null
  pool_name: string | null
  reward_sats: number | null
  fees_sats: number | null
  coinbase_addresses: string[]
  yours?: boolean
}

export interface EpochInfo {
  height: number
  epoch_start_height: number
  next_retarget_height: number
  blocks_into_epoch: number
  blocks_remaining: number
  progress: number
  seconds_remaining: number
  estimated_date: string
  estimated_change_pct: number | null
}

export interface HalvingInfo {
  height: number
  next_halving_height: number
  blocks_remaining: number
  seconds_remaining: number
  estimated_date: string
  subsidy_now_btc: number
  subsidy_next_btc: number
  progress: number
}

export interface NodeStatus {
  kind: string
  reachable: boolean
  error: string | null
  version: string | null
  subversion: string | null
  chain: string | null
  blocks: number | null
  headers: number | null
  initial_block_download: boolean | null
  verification_progress: number | null
  connections: number | null
  connections_in: number | null
  connections_out: number | null
  mempool_tx_count: number | null
  mempool_bytes: number | null
  mempool_max_bytes: number | null
  min_relay_fee_sat_vb: number | null
  size_on_disk: number | null
  pruned: boolean | null
  uptime_s: number | null
  network_active: boolean | null
  best_block_hash: string | null
  difficulty: number | null
  network_hashrate_hs: number | null
  warnings: string[]
  checked_at: number
}

export interface PoolWorker {
  name: string
  hashrate_hs: number | null
  best_difficulty: number | null
  last_seen: number | null
  started: number | null
  shares: number | null
}

export interface PoolStatus {
  kind: string
  name: string
  reachable: boolean
  error: string | null
  pool_hashrate_hs: number | null
  pool_miners: number | null
  blocks_found: number | null
  blocks: Record<string, unknown>[]
  address: string | null
  hashrate_hs: number | null
  best_difficulty: number | null
  best_difficulty_ever: number | null
  workers: PoolWorker[]
  last_share: number | null
  shares: number | null
  extra: Record<string, unknown>
  checked_at: number
}

export interface SourceHealth {
  id: string
  kind: string
  name: string
  ok: boolean | null
  error: string | null
  last_ok: number | null
  last_poll: number | null
  implicit: boolean
}

export interface NetworkState {
  updated_at: number
  available: boolean
  source: string | null
  height: number | null
  tip_hash: string | null
  tip_time: number | null
  difficulty: number | null
  network_hashrate_hs: number | null
  block_reward_btc: number | null
  subsidy_btc: number | null
  avg_fees_btc: number | null
  epoch: EpochInfo | null
  halving: HalvingInfo | null
  mempool_tx_count: number | null
  mempool_vsize: number | null
  fees_sat_vb: Record<string, number> | null
  prices: Record<string, number> | null
  btc_price: number | null
  recent_blocks?: BlockInfo[]
  node: NodeStatus | null
  pools: PoolStatus[]
  sources: SourceHealth[]
  warnings: string[]
  stale: boolean
  node_behind_by: number | null
}

// ----------------------------------------------------------------------------------- odds

export type HorizonKey = 'ten_minutes' | 'hour' | 'day' | 'week' | 'month' | 'year' | 'five_years' | 'ten_years'

export interface OddsHorizon {
  seconds: number
  probability: number
  one_in: number | null
}

export interface Economics {
  price_per_kwh: number
  btc_price: number | null
  cost_per_day: number
  cost_per_month: number
  cost_per_year: number
  block_reward_btc: number
  expected_value_per_day: number | null
  expected_value_per_year: number | null
  ev_to_cost_ratio: number | null
  break_even_btc_price: number | null
  power_w: number | null
  currency: string
}

export interface OddsAvailable {
  available: true
  hashrate: number
  difficulty: number
  network_hashrate: number | null
  share_of_network: number
  blocks_per_day: number
  expected_seconds: number
  median_seconds: number
  difficulty_growth_per_year: number
  horizons: Record<HorizonKey, OddsHorizon>
  live: boolean
  economics: Economics
  work: {
    total_hashes: number
    expected_blocks_of_work: number
    chance_found_by_now: number
    blocks_found: number
  }
  best_share: { difficulty: number | null; progress_to_block: number | null; device_id: string | null }
  plain_english: string[]
}

export interface OddsUnavailable {
  available: false
  reason: string
}

export type Odds = OddsAvailable | OddsUnavailable

export interface FoundBlock {
  hash: string
  height: number
  ts: number
  device_id: string | null
  address: string | null
  reward_sats: number | null
  source: string
  data: Record<string, unknown>
}

// ----------------------------------------------------------------------------------- events & alerts

export interface AppEvent {
  id: number | null
  ts: number
  type: string
  severity: Severity
  device_id: string | null
  title: string
  body: string | null
  data: Record<string, unknown>
  dedupe_key: string | null
  ack_ts: number | null
}

export interface ActiveAlert {
  key: string
  rule_id: string
  since: number
  title: string
  body: string | null
  device_id: string | null
  severity: Severity
}

export interface AlertRule {
  id: string
  name: string
  kind: string
  enabled: boolean
  severity: Severity
  scope: { all?: boolean; device_ids?: string[]; tags?: string[] }
  params: Record<string, number | string | boolean>
  channel_ids: string[]
  cooldown_s: number
  builtin: boolean
  created_at: number
}

export interface ParamSpec {
  name: string
  label: string
  type: string
  default: number
  min: number | null
  max: number | null
  unit: string
  help: string
}

export interface RuleType {
  kind: string
  label: string
  description: string
  mode: string
  severity: Severity
  enabled_by_default: boolean
  scope: 'device' | 'fleet' | string
  cooldown_s: number
  params: ParamSpec[]
}

export interface ChannelField {
  name: string
  label: string
  kind: 'text' | 'password' | 'url' | 'number' | 'boolean' | 'select' | 'email'
  secret: boolean
  required: boolean
  placeholder: string
  help: string
  default: string | number | boolean | null
  options: string[]
}

export interface ChannelType {
  kind: string
  label: string
  help: string
  fields: ChannelField[]
}

export interface Channel {
  id: string
  kind: string
  name: string
  enabled: boolean
  config: Record<string, unknown>
  has_secret: boolean
  min_severity: Severity
  created_at: number
}

export interface SendResult {
  ok: boolean
  channel_id?: string
  channel?: string
  error?: string | null
  message?: string
  [k: string]: unknown
}

// ----------------------------------------------------------------------------------- sources

export interface SourceKind {
  kind: string
  label: string
  title: string
  url_example: string
  secret_fields: { name: string; label: string; secret?: boolean }[]
  option_fields?: { name: string; label: string }[]
  gives: string[]
  where_to_find_login: string
}

export interface Source {
  id: string
  kind: string
  name: string
  url: string | null
  enabled: boolean
  options: Record<string, unknown>
  has_secret: boolean
  created_at: number
  health: SourceHealth | null
}

export interface ImplicitSource {
  id: string
  kind: string
  name: string
  implicit: true
  health: SourceHealth
}

export interface ConnectionTest {
  ok: boolean
  message: string
  details: Record<string, unknown>
  hints: string[]
}

// ----------------------------------------------------------------------------------- discovery

export interface MinerCandidate {
  host: string
  port: number
  driver: string
  family: string
  model: string
  mac: string | null
  serial: string | null
  firmware: string | null
  hostname: string | null
  identity: string
  hashrate_hs: number | null
  evidence: string[]
  already_added: string | null
  duplicate_of: string | null
  key: string
}

export interface SourceCandidate {
  kind: string
  url: string
  name: string
  needs_credentials: boolean
  reason: string
  verified: boolean
}

export interface DiscoveryJob {
  id: string
  cidrs: string[]
  status: 'running' | 'finished' | 'cancelled' | 'failed'
  phase: string
  started_at: number
  finished_at: number | null
  total_hosts: number
  scanned_hosts: number
  progress: number
  miners: MinerCandidate[]
  sources: SourceCandidate[]
  error: string | null
}

// ----------------------------------------------------------------------------------- misc

export interface Insight {
  id: string
  level: 'tip' | 'info' | 'warning' | 'critical' | string
  title: string
  body: string
  action: { label: string; type: 'route' | 'api' | string; target: string } | null
  device_id: string | null
}

export interface Meta {
  app: string
  version: string
  api_version: string
  demo: boolean
  instance_name: string
  auth: { mode: 'none' | 'password'; password_set: boolean; public_read: boolean; token_header: string }
  setup: {
    onboarding_done: boolean
    devices: number
    has_node_or_pool: boolean
    has_notification_channel: boolean
    network_data: boolean
  }
  ui: { theme: string; accent: string }
  links: { openapi: string; docs: string; llms_txt: string; agent_guide: string; mcp: string; metrics: string }
}

export interface Me {
  name: string
  scope: Scope
  via: string
}

export interface ApiToken {
  id: string
  name: string
  scope: Scope
  created_at: number
  last_used_at: number | null
  expires_at: number | null
}

export interface CreatedToken {
  id: string
  name: string
  scope: Scope
  token: string
  expires_at: number | null
  usage: string
  warning: string
}

export interface Check {
  id: string
  status: 'pass' | 'warn' | 'fail'
  message: string
  fix?: string
}

export interface Diagnostics {
  version: string
  python: string
  platform: string
  data_dir: string
  listening: string
  lan_networks: string[]
  checks: Check[]
  ok: boolean
  devices: {
    id: string
    name: string
    host: string
    status: string
    reason: string | null
    last_error: string | null
    model: string
    firmware: string | null
  }[]
  sources: SourceHealth[]
}

export interface SystemInfo {
  version: string
  python: string
  platform: string
  uptime_s: number
  data_dir: string
  db_size_bytes: number
  schema_version: number
  devices: number
  stream_subscribers: number
  demo: boolean
  offline_mode: boolean
}

export interface UpdateStatus {
  current: string
  latest: string | null
  update_available: boolean
  disabled?: boolean
  url?: string | null
  notes?: string | null
  checked_at?: number | null
  error?: string | null
}

export interface TuningInfo {
  allowed: boolean
  tuning_enabled_in_settings: boolean
  options: {
    frequency_mhz: number[]
    core_voltage_mv: number[]
    default_frequency_mhz: number | null
    default_core_voltage_mv: number | null
    max_power_w: number | null
    max_temp_c: number | null
  } | null
  current: {
    frequency_mhz: number | null
    core_voltage_mv: number | null
    power_w: number | null
    hashrate_hs: number | null
    efficiency_j_th: number | null
    temp_asic_c: number | null
  } | null
}

export interface AuditEntry {
  id: number
  ts: number
  actor: string
  action: string
  device_id: string | null
  params: Record<string, unknown>
  result: { ok?: boolean; message?: string; error?: string }
}

export interface ActionResult {
  ok: boolean
  action?: string
  device?: string
  device_id?: string
  name?: string
  dry_run?: boolean
  params?: Record<string, unknown>
  message?: string
  error?: string
}

export interface HistoryResult {
  step: number
  source: string
  t: number[]
  series: Record<string, (number | null)[]>
  devices?: Record<string, Record<string, (number | null)[]>>
}

export interface DeviceHistoryResult {
  step: number
  source: string
  t: number[]
  series: Record<string, (number | null)[]>
}

// ----------------------------------------------------------------------------------- settings

export interface Settings {
  general: { instance_name: string; onboarding_done: boolean; first_run_at: number | null }
  units: { temperature: 'c' | 'f'; hashrate: 'auto' | 'th' | 'gh' | 'ph'; currency: string; locale: string | null }
  polling: { interval_s: number; offline_interval_s: number; timeout_s: number; concurrency: number; offline_after_failures: number }
  energy: { price_per_kwh: number; psu_overhead_pct: number }
  network: {
    use_public_apis: boolean
    mempool_url: string
    price_source: 'mempool' | 'manual' | 'none'
    manual_btc_price: number | null
    difficulty_growth_per_year: number
    avg_block_fees_btc: number | null
  }
  mining: { addresses: string[] }
  retention: { raw_days: number; minute_days: number; hour_days: number; event_days: number }
  safety: { allow_control: boolean; allow_tuning: boolean; max_temp_c: number }
  alerts: {
    temp_warn_c: number
    temp_crit_c: number
    vr_temp_warn_c: number
    hashrate_drop_pct: number
    reject_rate_pct: number
    offline_after_s: number
    quiet_hours: { start: string; end: string } | null
  }
  ui: {
    theme: 'system' | 'dark' | 'light' | 'amoled'
    accent: string
    density: 'comfortable' | 'compact'
    view_miners: 'grid' | 'table'
    reduce_motion: boolean
    sound_on_block: boolean
    simple_mode: boolean
    dashboard: DashboardLayout | null
    kiosk: KioskConfig | null
  }
  auth: { mode: 'none' | 'password'; public_read: boolean }
}

export interface DashboardWidgetPlacement {
  id: string
  /** column span on the 12-column grid at desktop width */
  span: 3 | 4 | 6 | 8 | 12
}

export interface DashboardLayout {
  version: 1
  widgets: DashboardWidgetPlacement[]
}

export interface KioskConfig {
  rotate_s: number
  panels: string[]
  show_clock: boolean
}

// ----------------------------------------------------------------------------------- live stream

export interface BlockFoundEvent {
  height: number
  hash: string
  address?: string | null
  source?: string
  device_id?: string
}

export interface StreamHandlers {
  device?: (d: { id: string; view: DeviceView }) => void
  device_removed?: (d: { id: string }) => void
  fleet?: (s: FleetSummary) => void
  event?: (e: AppEvent) => void
  network?: (n: NetworkState) => void
  alerts?: (a: { active: ActiveAlert[] }) => void
  discovery?: (j: DiscoveryJob) => void
  block_found?: (b: BlockFoundEvent) => void
  new_block?: (b: { height: number; hash: string }) => void
}
