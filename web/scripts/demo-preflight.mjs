// Shared gate for browser tooling: no app reads, writes, or pictures before this succeeds.
export async function requireDemo(base) {
  try {
    const response = await fetch(new URL('/api/v1/meta', base), {
      redirect: 'error', signal: AbortSignal.timeout(5000),
    })
    if (!response.ok || (await response.json())?.demo !== true) throw new Error('not demo')
  } catch {
    throw new Error('Refusing browser tooling: the selected BASE must report meta.demo === true. Start bsmm serve --demo --offline and match BASE / BSMM_DEV_API.')
  }
}

export default async function demoPreflight(config) {
  const bases = new Set(config.projects.map(project => project.use.baseURL))
  for (const base of bases) await requireDemo(base)
}
