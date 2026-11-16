import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

// Card #2445: the "Mark offline after" count also decides how many polls in a row a changed pool or payout setting
// must be seen before an alert is raised, so its hint says both. The Field text is read from the component source.
const SOURCE = readFileSync(fileURLToPath(new URL('./GeneralSettings.vue', import.meta.url)), 'utf8')
const NEW_HINT = 'Checks in a row before a miner counts as offline, or before a changed pool or payout setting raises an alert.'
const OLD_HINT = 'Failed checks in a row before a miner counts as offline.'

describe('card 2445: the offline count hint names the pool alert', () => {
  it('shows the new hint on the "Mark offline after" field', () => {
    expect(SOURCE).toContain(`<Field label="Mark offline after" hint="${NEW_HINT}">`)
  })

  it('no longer shows the old hint', () => {
    expect(SOURCE).not.toContain(OLD_HINT)
  })
})
