import type { PageLayout } from '@/lib/types'

/** The `ui` setting that holds a page's layout. */
export type PageKey = 'bitcoin_page' | 'odds_page'

export interface PageCard {
  id: string
  title: string
  /** Tailwind classes for the card's cell in the page grid (column span). */
  cell?: string
}

/**
 * Turn whatever was saved on the server into the ordered card ids to show: unknown cards are dropped (a card removed
 * in an upgrade) and duplicates collapse. Nothing saved, or a shape we do not know, means every card in default order.
 */
export function resolvePageLayout(saved: PageLayout | null | undefined, cards: PageCard[]): string[] {
  if (!saved || saved.version !== 1 || !Array.isArray(saved.cards)) return cards.map((c) => c.id)
  const known = new Set(cards.map((c) => c.id))
  const seen = new Set<string>()
  const out: string[] = []
  for (const id of saved.cards) {
    if (typeof id !== 'string' || !known.has(id) || seen.has(id)) continue
    seen.add(id)
    out.push(id)
  }
  return out
}
