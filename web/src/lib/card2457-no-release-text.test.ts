// @vitest-environment node
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

// Card #2457: the update check keeps a version, a release link and the time. Release text is not stored, returned or
// typed anywhere in the interface. The files are read from disk, so this checks what is shipped.
const SRC_DIR = fileURLToPath(new URL('..', import.meta.url))
const source = (relative: string): string => readFileSync(`${SRC_DIR}${relative}`, 'utf8')

/** The body of `export interface <name> { ... }` (these interfaces have no nested braces). */
function interfaceBody(text: string, name: string): string {
  const match = new RegExp(`export interface ${name} \\{([^}]*)\\}`).exec(text)
  if (!match) throw new Error(`interface ${name} not found`)
  return match[1]
}

describe('no release text in the update status', () => {
  it('the UpdateStatus type has version, link, time and state only', () => {
    const fields = [...interfaceBody(source('lib/types.ts'), 'UpdateStatus').matchAll(/^\s*(\w+)\??:/gm)].map((m) => m[1])
    expect(fields.sort()).toEqual(['checked_at', 'current', 'disabled', 'error', 'latest', 'update_available', 'url'])
  })

  it('the About page does not read or show release text', () => {
    expect(source('pages/settings/AboutSettings.vue')).not.toMatch(/\.notes\b/)
  })

  it('the settings type carries the automatic check switch', () => {
    expect(source('lib/types.ts')).toMatch(/check_for_updates: boolean/)
  })
})
