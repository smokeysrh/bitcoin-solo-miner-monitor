// @vitest-environment node
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { api } from '@/lib/api'

// HashHurdr only reads from miners. The interface has no way to restart, flash, pause, resume, retune or
// re-point a miner, and the client has no call that could. The files are read from disk, so this checks what is shipped.
const SRC_DIR = fileURLToPath(new URL('.', import.meta.url))
const sourceFile = (relative: string): string => readFileSync(`${SRC_DIR}${relative}`, 'utf8')

/** Every .vue and .ts file under web/src that is not a test. */
function shippedSources(): { path: string; text: string }[] {
  return (readdirSync(SRC_DIR, { recursive: true }) as string[])
    .filter((p) => /\.(vue|ts)$/.test(p) && !/\.test\.ts$/.test(p))
    .map((p) => ({ path: p, text: sourceFile(p) }))
}

describe('monitor-only interface', () => {
  it('the api client has no miner action, bulk action or tuning call', () => {
    const forbidden = Object.keys(api).filter((name) => /action|tuning|restart|identify|pause|resume/i.test(name))
    expect(forbidden).toEqual([])
  })

  it('no source file calls a miner action or tuning endpoint', () => {
    const hits = shippedSources()
      .filter(({ text }) => /\/actions\b|\/tuning\b/.test(text))
      .map(({ path }) => path)
    expect(hits).toEqual([])
  })

  it('no source file sends or reads the per-miner or global control switches', () => {
    const hits = shippedSources()
      .filter(({ text }) => /allow_control|allow_tuning|useMinerActions/.test(text))
      .map(({ path }) => path)
    expect(hits).toEqual([])
  })

  it('the control-only components and the Safety page are gone', () => {
    for (const gone of ['pages/settings/SafetySettings.vue', 'components/miners/detail/DetailTuning.vue', 'components/miners/BulkActionDialog.vue', 'composables/useMinerActions.ts']) {
      expect(existsSync(`${SRC_DIR}${gone}`), gone).toBe(false)
    }
  })

  it('the router and settings navigation have no Safety page', () => {
    for (const file of ['router.ts', 'pages/settings/SettingsLayout.vue', 'components/layout/CommandPalette.vue']) {
      expect(sourceFile(file), file).not.toMatch(/settings\/safety|SafetySettings/)
    }
  })

  it('the miner detail page has no Tuning tab', () => {
    const page = sourceFile('pages/MinerDetailPage.vue')
    expect(page).not.toMatch(/DetailTuning|value: 'tuning'|#tuning/)
  })
})
