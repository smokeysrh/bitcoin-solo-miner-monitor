// Every user-visible word of the automatic update check setting on Settings > About, in one place (card #2457).
//
// The wording below is the final copy; nothing else in the code base spells these sentences out. Do not copy these
// strings anywhere else.

export const updateCheckText = {
  /** title of the switch */
  label: 'Check for updates automatically',
  /** line under the title */
  description: 'HashHurdr looks for a newer version once a day. Switch this off and it only checks when you press the button.',
  /** what one check sends and gets back */
  note: 'Each check is one anonymous request to GitHub, which sees your IP address and the app name and version. What comes back is the newest version number and a release link. Nothing installs by itself.',
  /** status line while the switch is off */
  off: 'Automatic checks are off. The Check for updates button still works.',
} as const
