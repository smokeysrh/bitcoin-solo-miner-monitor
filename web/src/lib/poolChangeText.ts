// Every user-visible word of the pool and payout settings alert in the web app, in one place.
//
// The wording below is the final copy (card #2442); nothing else in the code base spells these sentences out. Do not copy
// these strings anywhere else.

export const poolChangeText = {
  /** badge on a miner tile and in the miner table (a few words; it sits next to the status) */
  badge: 'Pool or payout changed',
  badgeTitle: "This miner's pool or payout settings changed, and the notice is still waiting for your answer.",

  /** notice at the top of the miner page */
  noticeTitle: 'Pool or payout settings changed',
  noticeIntro: "Compare Before and Now. If this was not you, fix it in the miner's own settings page.",
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
  confirmMessage: 'HashHurdr will record the settings the miner reports right now as normal and clear this notice. Nothing is changed on the miner.',
  confirmLabel: 'Accept change',
  readOnlyNote: 'Only someone with control access can accept this change.',
  acceptedToast: (miner: string): string => `Accepted the new settings for ${miner}`,
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
