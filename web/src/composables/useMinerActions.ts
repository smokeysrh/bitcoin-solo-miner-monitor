import { api, describeError } from '@/lib/api'
import type { ActionResult, Capability, DeviceView } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useSession } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { useToasts } from '@/stores/toasts'
import { confirmDialog } from './useConfirm'

/**
 * Everything you can do to a miner from the UI, with the safety rails in one place:
 * who may do it, whether the miner supports it, a confirmation for the disruptive ones, and a toast with the outcome.
 */
export function useMinerActions() {
  const live = useLive()
  const session = useSession()
  const settings = useSettings()
  const toasts = useToasts()

  /** Control is allowed for this session, switched on globally and for this miner, and the driver supports it. */
  function can(d: DeviceView, cap: Capability): boolean {
    return session.canControl && d.allow_control && (settings.data?.safety.allow_control ?? true) && d.capabilities.includes(cap)
  }

  async function refresh(d: DeviceView): Promise<void> {
    try {
      live.upsertDevice(await api.pollDevice(d.id))
    } catch {
      /* the stream will bring the next reading anyway */
    }
  }

  async function run(d: DeviceView, action: string, params: Record<string, unknown>, success: string): Promise<ActionResult | null> {
    try {
      const res = await api.action(d.id, action, params)
      if (res.ok === false) {
        toasts.error(`${d.name}: that did not work`, res.message ?? res.error)
        return res
      }
      toasts.success(success, res.message)
      void refresh(d)
      return res
    } catch (e) {
      toasts.error(`${d.name}: could not do that`, describeError(e))
      return null
    }
  }

  async function restart(d: DeviceView): Promise<void> {
    const ok = await confirmDialog({
      title: `Restart ${d.name}?`,
      message: 'It stops hashing while it reboots, usually for under a minute, then reconnects by itself.',
      confirmLabel: 'Restart',
    })
    if (ok) await run(d, 'restart', {}, `${d.name} is restarting`)
  }

  const identify = (d: DeviceView) => run(d, 'identify', {}, `${d.name} is flashing so you can find it`)

  async function pause(d: DeviceView): Promise<void> {
    const ok = await confirmDialog({
      title: `Pause ${d.name}?`,
      message: 'It stops hashing until you resume it. Nothing is lost.',
      confirmLabel: 'Pause mining',
    })
    if (ok) await run(d, 'pause', {}, `${d.name} is paused`)
  }

  const resume = (d: DeviceView) => run(d, 'resume', {}, `${d.name} is hashing again`)

  async function remove(d: DeviceView): Promise<boolean> {
    const ok = await confirmDialog({
      title: `Stop monitoring ${d.name}?`,
      message: 'The miner itself is not touched. Its history is deleted from this app and cannot be recovered.',
      confirmLabel: 'Remove miner',
      tone: 'danger',
    })
    if (!ok) return false
    try {
      await api.removeDevice(d.id)
      toasts.success(`${d.name} removed`)
      void live.reload()
      return true
    } catch (e) {
      toasts.error('Could not remove it', describeError(e))
      return false
    }
  }

  async function pollNow(d: DeviceView): Promise<void> {
    try {
      live.upsertDevice(await api.pollDevice(d.id))
      toasts.info(`${d.name} refreshed`)
    } catch (e) {
      toasts.error(`Could not reach ${d.name}`, describeError(e))
    }
  }

  return { can, restart, identify, pause, resume, remove, pollNow, run }
}
