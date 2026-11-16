import { api, describeError } from '@/lib/api'
import { poolChangeText } from '@/lib/poolChangeText'
import type { DeviceView } from '@/lib/types'
import { useHashling } from '@/stores/hashling'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import { confirmDialog } from './useConfirm'

/**
 * What you can do with a miner in HashHurdr's own list: read it again now, stop monitoring it, or accept a change of its
 * pool settings. None of these touches the miner itself.
 */
export function useMinerMonitor() {
  const live = useLive()
  const toasts = useToasts()
  const hashling = useHashling()

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

  /** Ask first, then tell HashHurdr that the new settings are intended. Returns true once HashHurdr's record is updated. */
  async function acceptPoolChange(d: DeviceView): Promise<boolean> {
    const change = d.pool_change
    if (!change) return false
    const ok = await confirmDialog({
      title: poolChangeText.confirmTitle,
      message: poolChangeText.confirmMessage,
      confirmLabel: poolChangeText.confirmLabel,
    })
    if (!ok) return false
    try {
      const r = await api.acceptPoolChange(change.event_id)
      live.upsertDevice(r.device)
      if (!hashling.show('M24', { miner: d.name })) toasts.success(poolChangeText.acceptedToast(d.name))
      return true
    } catch (e) {
      toasts.error(poolChangeText.acceptFailedToast, describeError(e))
      return false
    }
  }

  return { remove, pollNow, acceptPoolChange }
}
