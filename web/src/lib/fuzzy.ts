/**
 * Tiny fuzzy matcher for the command palette. Returns 0 for "no match", otherwise higher is better:
 * exact word starts beat substrings, substrings beat scattered letters.
 */
export function fuzzyScore(query: string, text: string): number {
  const q = query.trim().toLowerCase()
  if (!q) return 1
  const t = text.toLowerCase()

  // every space-separated term must match somewhere; the total is the sum
  const terms = q.split(/\s+/)
  let total = 0
  for (const term of terms) {
    const s = scoreTerm(term, t)
    if (s === 0) return 0
    total += s
  }
  return total / terms.length
}

function scoreTerm(term: string, t: string): number {
  const idx = t.indexOf(term)
  if (idx !== -1) {
    const atWordStart = idx === 0 || /[\s\-_/.:]/.test(t[idx - 1]!)
    return 100 - Math.min(idx, 40) + (atWordStart ? 40 : 0)
  }
  // subsequence: letters in order, penalise gaps
  let ti = 0
  let gaps = 0
  let last = -1
  for (const ch of term) {
    const found = t.indexOf(ch, ti)
    if (found === -1) return 0
    if (last !== -1 && found > last + 1) gaps += found - last - 1
    last = found
    ti = found + 1
  }
  return Math.max(1, 40 - gaps)
}

export interface Ranked<T> {
  item: T
  score: number
}

export function rank<T>(items: T[], query: string, text: (item: T) => string): Ranked<T>[] {
  return items
    .map((item) => ({ item, score: fuzzyScore(query, text(item)) }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
}
