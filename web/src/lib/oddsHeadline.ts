import { formatOdds } from './format'
import type { KioskConfig, OddsHeadline } from './types'

export interface OddsHeadlineChoice {
  key: OddsHeadline
  /** Short name, used in the Settings list and in the small list below the headline. */
  label: string
  /** Plain-words line under the big number on the wall display. */
  sentence: string
}

/** The six horizons that can be the big number, in the order they are listed. */
export const ODDS_HEADLINES: readonly OddsHeadlineChoice[] = [
  { key: 'ten_minutes', label: 'Next 10 minutes', sentence: 'Chance of a block in the next 10 minutes' },
  { key: 'day', label: 'Today', sentence: 'Chance of a block today' },
  { key: 'month', label: 'This month', sentence: 'Chance of a block this month' },
  { key: 'year', label: 'This year', sentence: 'Chance of a block this year' },
  { key: 'five_years', label: '5 years', sentence: 'Chance of a block in the next 5 years' },
  { key: 'ten_years', label: '10 years', sentence: 'Chance of a block in the next 10 years' },
]

/** What an older saved wall display (no `odds_headline`) has always shown. */
export const DEFAULT_ODDS_HEADLINE: OddsHeadline = 'year'

/** The wall display's settings before anything was saved. Keep in step with the fallback in KioskPage.vue. */
export const DEFAULT_KIOSK: KioskConfig = {
  rotate_s: 15,
  panels: ['overview', 'miners', 'odds', 'network', 'chart'],
  show_clock: true,
}

/** A saved value that is missing or not one of the six choices falls back to the yearly headline. */
export function oddsHeadlineChoice(saved: unknown): OddsHeadlineChoice {
  const found = ODDS_HEADLINES.find((choice) => choice.key === saved)
  return found ?? ODDS_HEADLINES.find((choice) => choice.key === DEFAULT_ODDS_HEADLINE)!
}

/** Zero stays "0%" and a missing value says "Unavailable"; formatOdds alone would show both as a dash. */
export function formatHorizonChance(probability: number | null | undefined): string {
  if (typeof probability !== 'number' || !Number.isFinite(probability)) return 'Unavailable'
  return probability === 0 ? '0%' : formatOdds(probability)
}
