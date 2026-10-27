import * as f from '@/lib/format'
import { useSettings } from '@/stores/settings'

/**
 * Formatters pre-wired to the user's unit preferences (°C/°F, TH/s vs auto, currency).
 * Because they read the settings store, templates re-render when the user changes a unit.
 */
export function useFmt() {
  const settings = useSettings()
  return {
    ...f,
    hashrate: (hs: number | null | undefined, digits = 3) => f.formatHashrate(hs, settings.hashUnit, digits),
    splitHash: (hs: number | null | undefined, digits = 3) => f.splitHashrate(hs, settings.hashUnit, digits),
    temp: (c: number | null | undefined, digits = 0) => f.formatTemp(c, settings.tempUnit, digits),
    tempValue: (c: number | null | undefined, digits = 0) => {
      const v = f.toDisplayTemp(c, settings.tempUnit)
      return v === null ? '–' : v.toFixed(digits)
    },
    tempSymbol: () => (settings.tempUnit === 'f' ? '°F' : '°C'),
    money: (n: number | null | undefined, digits?: number) => f.formatMoney(n, settings.currency, digits),
  }
}

export type Fmt = ReturnType<typeof useFmt>
