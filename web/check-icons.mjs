// Verifies every icon imported from lucide-vue-next in src/ actually exists (a missing one is a blank at runtime, not a build error).
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import * as lucide from 'lucide-vue-next'

const names = new Map()
function walk(dir) {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f)
    if (statSync(p).isDirectory()) walk(p)
    else if (/\.(vue|ts)$/.test(f)) {
      const src = readFileSync(p, 'utf8')
      for (const m of src.matchAll(/import\s*\{([^}]+)\}\s*from\s*'lucide-vue-next'/g)) {
        for (const raw of m[1].split(',')) {
          const n = raw.trim().split(/\s+as\s+/)[0]
          if (n) names.set(n, [...(names.get(n) ?? []), p])
        }
      }
    }
  }
}
walk('src')
const missing = [...names.keys()].filter((n) => !(n in lucide))
console.log(`${names.size} icons used, ${missing.length} missing`)
for (const m of missing) console.log(`  ${m}  (used in ${names.get(m).join(', ')})`)
process.exit(missing.length ? 1 : 0)
