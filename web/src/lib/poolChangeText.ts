// Every user-visible word of the pool and payout settings alert in the web app, in one place.
//
// PLACEHOLDER WORDING (card #2442, phase 1): plain functional text. The final copy is drafted separately and replaces the
// values below; nothing else in the code base spells these sentences out. Each entry is listed in STRINGS.md with where it
// appears, its variables and its length limits. Do not copy these strings anywhere else.

export const poolChangeText = {
  /** badge on a miner tile and in the miner table (a few words; it sits next to the status) */
  badge: 'Settings changed',
  badgeTitle: 'This miner reports pool or payout settings that differ from the ones HashHurdr has on record.',

  /** notice at the top of the miner page */
  noticeTitle: 'Pool or payout settings changed',
  noticeIntro: 'HashHurdr has the earlier values on record. Compare them with the values the miner reports now.',
  since: (ago: string): string => `Seen ${ago}`,
  beforeLabel: 'Before',
  nowLabel: 'Now',
  /** shown instead of a value when a pool was not there before or is gone now */
  absent: 'none',
  settingLabels: { pool_address: 'Pool address', pool_port: 'Pool port', payout_address: 'Payout address' } as Record<string, string>,
  slotLabels: { primary: 'Primary pool', fallback: 'Fallback pool' } as Record<string, string>,
  /** a pool that is neither primary nor fallback; the argument is the slot name as reported */
  otherSlot: (slot: string): string => `Pool ${slot}`,

  /** the Accept button and what follows it */
  acceptButton: 'This was me: accept',
  acceptBusy: 'Accepting…',
  confirmTitle: 'Accept this change?',
  confirmMessage: 'HashHurdr will treat the new settings as normal and stop showing this notice. Nothing is changed on the miner.',
  confirmLabel: 'Accept change',
  readOnlyNote: 'Only someone with control access can accept this change.',
  acceptedToast: (miner: string): string => `Accepted the new pool settings for ${miner}`,
  acceptFailedToast: 'Could not accept the change',

  /** the demo banner button that triggers the scenario */
  demoScenarioLabel: "Change a miner's pool",
}

/** "fallback" -> "Fallback pool"; a numbered slot such as "fallback 2" -> "Fallback pool 2". */
export function slotLabel(slot: string): string {
  const [base = slot, ...rest] = slot.split(' ')
  const label = poolChangeText.slotLabels[base] ?? poolChangeText.otherSlot(base)
  return rest.length ? `${label} ${rest.join(' ')}` : label
}
