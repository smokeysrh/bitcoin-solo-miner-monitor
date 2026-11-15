import { api, describeError } from '@/lib/api'
import type { DeviceView } from '@/lib/types'
import { useLive } from '@/stores/live'
import { useToasts } from '@/stores/toasts'
import { confirmDialog } from './useConfirm'

/**
 * What you can do with a miner in HashHurdr's own list: read it again now, or stop monitoring it.
 * Neither touches the miner itself.
 */
export function useMinerMonitor() {
  const live = useLive()
  const toasts = useToasts()

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

  return { remove, pollNow }
}
