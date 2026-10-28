import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { api, describeError } from '@/lib/api'
import { LiveStream, type StreamStatus } from '@/lib/stream'
import type { ActiveAlert, AppEvent, BlockInfo, DeviceView, FleetSummary, FoundBlock, NetworkState, Odds } from '@/lib/types'
import { useToasts } from './toasts'
import { useUi } from './ui'

const EVENT_CAP = 60
/** Refetch the heavier derived numbers (odds, economics) this often even if nothing pushes. */
const OVERVIEW_EVERY_MS = 30_000

export interface LeaderboardRow {
  device_id: string
  difficulty: number
  ts: number
}

/**
 * Everything the dashboard shows that changes while you watch. Loaded once over REST, then kept fresh by
 * the server-sent event stream; a slow timer refetches the odds because they depend on the live hashrate.
 */
export const useLive = defineStore('live', () => {
  const devicesById = ref<Record<string, DeviceView>>({})
  const summary = shallowRef<FleetSummary | null>(null)
  const network = shallowRef<NetworkState | null>(null)
  const odds = shallowRef<Odds | null>(null)
  const alerts = ref<ActiveAlert[]>([])
  const events = ref<AppEvent[]>([])
  const blocksFound = ref<FoundBlock[]>([])
  const recentBlocks = ref<BlockInfo[]>([])
  const leaderboard = ref<LeaderboardRow[]>([])
  const status = ref<StreamStatus>('idle')
  const loaded = ref(false)
  const loadError = ref<string | null>(null)
  const lastUpdate = ref(0)

  const devices = computed(() => Object.values(devicesById.value).sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })))
  const deviceCount = computed(() => devices.value.length)
  const byId = (id: string | null | undefined): DeviceView | undefined => (id ? devicesById.value[id] : undefined)
  const deviceName = (id: string | null | undefined): string => byId(id)?.name ?? (id ? 'Removed miner' : '')
  const unackedEvents = computed(() => events.value.filter((e) => e.ack_ts === null && e.severity !== 'info').length)

  let stream: LiveStream | null = null
  let timer: ReturnType<typeof setInterval> | null = null
  let soon: ReturnType<typeof setTimeout> | null = null
  let loadSeq = 0
  let epoch = 0
  const toasts = useToasts()

  async function loadAll(): Promise<void> {
    const seq = ++loadSeq
    try {
      const [ov, devs, pool, blocks] = await Promise.all([
        api.overview(),
        api.devices(),
        api.pool().catch(() => ({ pools: [] })),
        api.recentBlocks().catch(() => [] as BlockInfo[]),
      ])
      if (seq !== loadSeq) return // a newer load superseded this one
      const map: Record<string, DeviceView> = {}
      for (const d of devs) map[d.id] = d
      devicesById.value = map
      summary.value = ov.summary
      odds.value = ov.odds
      network.value = { ...ov.network, pools: pool.pools, recent_blocks: blocks }
      recentBlocks.value = blocks
      alerts.value = ov.alerts
      events.value = ov.events
      blocksFound.value = ov.blocks_found
      leaderboard.value = ov.leaderboard
      loaded.value = true
      loadError.value = null
      lastUpdate.value = Date.now()
    } catch (e) {
      if (seq !== loadSeq) return
      loadError.value = describeError(e)
    }
  }

  /** Cheap refresh of the numbers the stream does not push (odds, leaderboard, blocks you found). */
  async function refreshOverview(): Promise<void> {
    const started = epoch
    try {
      const ov = await api.overview()
      if (started !== epoch) return
      odds.value = ov.odds
      leaderboard.value = ov.leaderboard
      blocksFound.value = ov.blocks_found
      alerts.value = ov.alerts
      if (!summary.value || ov.summary.updated_at > summary.value.updated_at) summary.value = ov.summary
      lastUpdate.value = Date.now()
    } catch {
      /* the stream status badge already tells the user the connection is struggling */
    }
  }

  function refreshSoon(delayMs = 1500): void {
    if (soon) clearTimeout(soon)
    soon = setTimeout(() => {
      soon = null
      void refreshOverview()
    }, delayMs)
  }

  async function refreshBlocks(): Promise<void> {
    const started = epoch
    const blocks = await api.recentBlocks().catch(() => recentBlocks.value)
    if (started !== epoch) return
    recentBlocks.value = blocks
    if (network.value) network.value = { ...network.value, recent_blocks: recentBlocks.value }
  }

  function announce(e: AppEvent): void {
    if (!loaded.value || Date.now() / 1000 - e.ts > 60) return
    if (e.severity === 'critical') toasts.push({ kind: 'error', title: e.title, body: e.body ?? undefined, timeout: 10_000 })
    else if (e.severity === 'warning') toasts.push({ kind: 'warning', title: e.title, body: e.body ?? undefined })
    else if (e.type === 'new_best_share') toasts.push({ kind: 'success', title: e.title, body: e.body ?? undefined })
    else if (e.type === 'device_online') toasts.push({ kind: 'success', title: e.title, body: e.body ?? undefined, timeout: 3500 })
  }

  function start(): void {
    if (stream) return
    void loadAll()
    stream = new LiveStream(
      {
        device: ({ id, view }) => {
          devicesById.value = { ...devicesById.value, [id]: view }
        },
        device_removed: ({ id }) => {
          const next = { ...devicesById.value }
          delete next[id]
          devicesById.value = next
        },
        fleet: (s) => {
          summary.value = s
          lastUpdate.value = Date.now()
        },
        event: (e) => {
          events.value = [e, ...events.value.filter((x) => x.id !== e.id)].slice(0, EVENT_CAP)
          announce(e)
        },
        network: (n) => {
          const prevHeight = network.value?.height ?? null
          network.value = { ...n, recent_blocks: network.value?.recent_blocks ?? recentBlocks.value }
          if (prevHeight !== null && n.height !== null && n.height > prevHeight) void refreshBlocks()
        },
        alerts: ({ active }) => {
          alerts.value = active
        },
        block_found: (b) => {
          const ui = useUi()
          ui.celebrate({ height: b.height, hash: b.hash, address: b.address ?? null })
          void refreshOverview()
        },
        new_block: () => refreshSoon(),
      },
      {
        onStatus: (s) => {
          status.value = s
        },
        onResync: () => void loadAll(),
      },
    )
    stream.start()
    timer = setInterval(() => {
      if (document.visibilityState === 'visible') void refreshOverview()
    }, OVERVIEW_EVERY_MS)
  }

  function stop(): void {
    epoch++
    loadSeq++
    stream?.stop()
    stream = null
    if (timer) clearInterval(timer)
    if (soon) clearTimeout(soon)
    timer = soon = null
    status.value = 'idle'
    devicesById.value = {}
    summary.value = network.value = odds.value = null
    alerts.value = []
    events.value = []
    blocksFound.value = []
    recentBlocks.value = []
    leaderboard.value = []
    loaded.value = false
    loadError.value = null
    lastUpdate.value = 0
  }

  /** Apply a freshly returned device view immediately (after a poll or edit) instead of waiting for the stream. */
  function upsertDevice(v: DeviceView): void {
    devicesById.value = { ...devicesById.value, [v.id]: v }
  }

  return {
    devicesById,
    devices,
    deviceCount,
    summary,
    network,
    odds,
    alerts,
    events,
    blocksFound,
    recentBlocks,
    leaderboard,
    status,
    loaded,
    loadError,
    lastUpdate,
    unackedEvents,
    byId,
    deviceName,
    start,
    stop,
    reload: loadAll,
    refreshOverview,
    upsertDevice,
  }
})
