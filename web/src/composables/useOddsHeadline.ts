import { computed } from 'vue'
import { DEFAULT_KIOSK, oddsHeadlineChoice, type OddsHeadlineChoice } from '@/lib/oddsHeadline'
import type { OddsHeadline } from '@/lib/types'
import { useSettings } from '@/stores/settings'

/**
 * The wall display's odds headline, shared by the Odds panel and Settings → Appearance. Both read and write the same
 * saved `ui.kiosk.odds_headline`, so a choice made in one place shows in the other straight away.
 */
export function useOddsHeadline() {
  const settings = useSettings()
  const current = computed<OddsHeadlineChoice>(() => oddsHeadlineChoice(settings.data?.ui.kiosk?.odds_headline))

  /** `ui.kiosk` is saved whole, so keep the other wall display options and change only the headline. Rejects when the save fails. */
  async function choose(value: OddsHeadline): Promise<void> {
    const saved = settings.data?.ui.kiosk ?? DEFAULT_KIOSK
    await settings.patch({ ui: { kiosk: { ...saved, panels: [...saved.panels], odds_headline: value } } })
  }

  return { current, choose }
}
