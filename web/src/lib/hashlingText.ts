/**
 * Every word Hashling says, in one place. The text is Becky's, copied verbatim: do not edit, trim or add wording here
 * (and do not write Hashling text anywhere else). A moment that needs a line she has not written is listed for her
 * instead of being improvised.
 *
 * Placeholders: {miner} one miner's name, {count} a number, {miners} up to two names then a "{count} more" tail
 * (see `listMiners`), {source} the name of a node or pool.
 */

export type MomentId =
  | 'M01'
  | 'M02'
  | 'M02N'
  | 'M03'
  | 'M04'
  | 'M05'
  | 'M06'
  | 'M07'
  | 'M08'
  | 'M09'
  | 'M10'
  | 'M11'
  | 'M1XN'
  | 'M12'
  | 'M13'
  | 'M14'
  | 'M15'
  | 'M15N'
  | 'M16'
  | 'M16N'
  | 'M17'
  | 'M18'
  | 'M19'
  | 'M20'
  | 'M21'
  | 'M22'
  | 'M23'
  | 'M24'
  | 'M25'

export interface MomentText {
  readonly title?: string
  readonly line: string
}

export const HASHLING_MOMENTS: Record<MomentId, MomentText> = {
  M01: { title: 'Pool or payout settings changed', line: '{miner} has new pool or payout settings. Check them on its page.' },
  M02: { title: 'Miner offline', line: '{miner} went quiet. Power or Wi-Fi is a good first look.' },
  M02N: { title: 'Several miners offline', line: '{count} miners went quiet: {miners}. Check shared power or Wi-Fi.' },
  M03: { title: 'Fan stopped', line: 'The fan on {miner} stopped. Check the fan and airflow on that miner.' },
  M04: { title: 'Miner running hot', line: '{miner} is running hot. Check its fan, airflow and room temperature.' },
  M05: { title: 'Hashrate dropped', line: '{miner} is hashing far below its usual rate. Check its page for what changed.' },
  M06: { title: 'Total hashrate dropped', line: 'The hurd is hashing a lot less in total. Check which miners slowed down.' },
  M07: { title: 'Many rejected shares', line: '{miner} is getting many rejected shares. Check its pool and connection.' },
  M08: { title: 'Fallback pool in use', line: '{miner} switched to its fallback pool. Check the main pool setting and connection.' },
  M09: { title: 'Node or pool not answering', line: '{source} stopped answering. Check that it is running and reachable.' },
  M10: { title: 'Node behind the network', line: '{source} is behind the network. Check its sync status and connection.' },
  M11: { title: 'Miner needs attention', line: '{miner} needs a look. Open its page to see what it reports.' },
  M1XN: { title: 'Several things need a look', line: '{count} things need a look. Check the dashboard to see which miners.' },
  M12: { title: 'Miner not hashing', line: '{miner} is on but not hashing. Its pool settings are a good first look.' },
  M13: { title: 'We found a block', line: 'The pool confirmed a real block. Somebody hold my hard hat!' },
  M14: { title: 'New best share', line: '{miner} just set a new best share. This one goes on the fridge.' },
  M15: { title: 'Miner added', line: '{miner} is on the board. The hurd just got bigger.' },
  M15N: { title: 'Miners added', line: '{count} new miners joined the hurd. Bigger hurd, same one screen.' },
  M16: { title: 'Miner is back', line: '{miner} is back. Welcome home, little space heater.' },
  M16N: { title: 'Miners are back', line: '{count} quiet miners are back on the board. Welcome home, space heaters.' },
  M17: { title: 'Every miner is hashing', line: 'The outage is over. I checked twice. Then once more, for fun.' },
  M18: { title: 'Welcome to HashHurdr', line: "I'm Hashling. Let's get your whole hurd onto one screen." },
  M19: { title: 'You are set', line: "Setup is done. I'll keep an eye on the hurd from here." },
  M20: { line: "Nothing here yet. Add a miner and I'll keep an eye on it." },
  M21: { title: 'Checklist complete', line: 'Every checklist step is done. Tidy work, pleb.' },
  M22: { title: 'Notifications are on', line: "Go enjoy your beauty rest. I've got the night shift." },
  M23: { title: 'Test notification sent', line: 'The test went through. Alerts will arrive the same way.' },
  M24: { title: 'Pool change accepted', line: 'Noted. {miner} is using the pool settings you chose.' },
  M25: { line: "Every hash is a fresh ticket. I'm a very busy optimist." },
}

/** Alt text for the poses (U01a to U01g), the pop-up controls (U02 to U05). */
export const HASHLING_UI = {
  U01a: 'Hashling the miner mascot on alert',
  U01b: 'Hashling the miner mascot asleep',
  U01c: 'Hashling the miner mascot celebrating a found block',
  U01d: 'Hashling the miner mascot celebrating',
  U01e: 'Hashling the miner mascot giving a thumbs-up',
  U01f: 'Hashling the miner mascot tinkering with his desk rig',
  U01g: 'Hashling the miner mascot holding a lottery ticket',
  U02: 'Hashling pop-ups',
  U03: 'Show Hashling on the dashboard and wall display when something happens, good or bad.',
  U04: 'Dismiss',
  U05: '{count} more',
} as const

export interface Vars {
  miner?: string
  count?: number
  miners?: string
  source?: string
}

/** Put the values into a line. A placeholder with no value is left visible rather than printed as "undefined". */
export function fill(template: string, vars: Vars): string {
  return template.replace(/\{(miner|count|miners|source)\}/g, (whole, name: keyof Vars) => {
    const value = vars[name]
    return value === undefined ? whole : String(value)
  })
}

/** How many names are spelled out before the rest are counted. */
const NAMED_MINERS = 2

/** Up to two names joined with ", ", then the rest as Becky's "{count} more" (U05): "A, B, 3 more". */
export function listMiners(names: readonly string[]): string {
  const shown = names.slice(0, NAMED_MINERS)
  const rest = names.length - shown.length
  return rest > 0 ? [...shown, fill(HASHLING_UI.U05, { count: rest })].join(', ') : shown.join(', ')
}
