/**
 * Live updates over Server-Sent Events, with automatic reconnect and a watchdog.
 *
 * EventSource reconnects by itself after a dropped connection, but gives up for good on an HTTP error
 * (for example a 401 after the session expired). This wrapper reconnects in both cases, backs off
 * politely and reports its state so the UI can show a "Live / Reconnecting" badge.
 */
import type { StreamHandlers } from './types'

export type StreamStatus = 'idle' | 'connecting' | 'live' | 'reconnecting' | 'closed'

export const STREAM_TOPICS = [
  'device',
  'device_removed',
  'fleet',
  'event',
  'network',
  'alerts',
  'discovery',
  'block_found',
  'new_block',
] as const satisfies readonly (keyof StreamHandlers)[]

export interface StreamOptions {
  url?: string
  /** Seconds of total silence before the connection is considered dead. The server pushes a fleet update every ~4 s. */
  watchdogS?: number
  onStatus?: (s: StreamStatus) => void
  /** Called on every (re)connect after the first, so stores can refetch what they missed. */
  onResync?: () => void
  eventSourceFactory?: (url: string) => EventSource
}

/** Backoff schedule in ms: 1s, 2s, 4s, 8s, 15s, then 30s forever, each with up to 25% jitter. */
export function backoffMs(attempt: number, rand: () => number = Math.random): number {
  const base = Math.min(30_000, [1000, 2000, 4000, 8000, 15000][attempt] ?? 30_000)
  return Math.round(base * (1 + rand() * 0.25))
}

/** Parse the JSON payload of an SSE message; returns `undefined` for malformed data instead of throwing. */
export function parsePayload<T = unknown>(data: string): T | undefined {
  try {
    return JSON.parse(data) as T
  } catch {
    return undefined
  }
}

export class LiveStream {
  private es: EventSource | null = null
  private attempt = 0
  private timer: ReturnType<typeof setTimeout> | null = null
  private watchdog: ReturnType<typeof setInterval> | null = null
  private lastMessage = 0
  private wantOpen = false
  private everConnected = false
  status: StreamStatus = 'idle'

  constructor(
    private readonly handlers: StreamHandlers,
    private readonly opts: StreamOptions = {},
  ) {}

  start(): void {
    if (this.wantOpen) return
    this.wantOpen = true
    this.connect()
    const limit = (this.opts.watchdogS ?? 25) * 1000
    this.watchdog = setInterval(() => {
      if (this.es && Date.now() - this.lastMessage > limit) {
        // the socket looks open but nothing has arrived for far too long: a half-dead connection
        this.dropAndRetry()
      }
    }, 5000)
  }

  stop(): void {
    this.wantOpen = false
    if (this.timer) clearTimeout(this.timer)
    if (this.watchdog) clearInterval(this.watchdog)
    this.timer = this.watchdog = null
    this.es?.close()
    this.es = null
    this.setStatus('closed')
  }

  private setStatus(s: StreamStatus): void {
    if (this.status === s) return
    this.status = s
    this.opts.onStatus?.(s)
  }

  private connect(): void {
    this.setStatus(this.everConnected ? 'reconnecting' : 'connecting')
    const url = this.opts.url ?? `/api/v1/stream?topics=${STREAM_TOPICS.join(',')}`
    const es = this.opts.eventSourceFactory ? this.opts.eventSourceFactory(url) : new EventSource(url, { withCredentials: true })
    this.es = es
    this.lastMessage = Date.now()

    es.addEventListener('hello', () => {
      this.lastMessage = Date.now()
      this.attempt = 0
      const resync = this.everConnected
      this.everConnected = true
      this.setStatus('live')
      if (resync) this.opts.onResync?.()
    })

    for (const topic of STREAM_TOPICS) {
      es.addEventListener(topic, (ev) => {
        this.lastMessage = Date.now()
        if (this.status !== 'live') this.setStatus('live')
        const payload = parsePayload((ev as MessageEvent<string>).data)
        if (payload === undefined) return
        try {
          // each topic has its own payload type; the handler map is keyed by topic name
          ;(this.handlers[topic] as ((p: unknown) => void) | undefined)?.(payload)
        } catch (e) {
          console.error(`[stream] handler for "${topic}" failed`, e)
        }
      })
    }

    es.onerror = () => {
      // CLOSED = the browser gave up (HTTP error); CONNECTING = it is retrying on its own
      if (es.readyState === 2 /* CLOSED */) this.dropAndRetry()
      else this.setStatus('reconnecting')
    }
  }

  private dropAndRetry(): void {
    this.es?.close()
    this.es = null
    if (!this.wantOpen) return
    this.setStatus('reconnecting')
    const wait = backoffMs(this.attempt++)
    this.timer = setTimeout(() => {
      this.timer = null
      if (this.wantOpen) this.connect()
    }, wait)
  }
}
