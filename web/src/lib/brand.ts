// URLs of the supplied HashHurdr brand files in web/public/brand (copied unchanged from the brand kit).
// Components bind these with `:src` on purpose. A static absolute `src="/brand/..."` is rewritten by the Vue
// template compiler into a module import when a Vite dev server is running (vitest, `npm run dev`), and Vite
// then inlines any file under 4 KiB as a data: URI. The symbol is 2.6 KB, so it was inlined; the lockups are
// 7 KB, so they were not. A bound string is never rewritten: every build and every test sees the same URL.
export const BRAND_ASSETS = {
  symbol: '/brand/hashhurdr-symbol.svg',
  lockupHorizontalDark: '/brand/hashhurdr-lockup-horizontal-dark.svg',
  lockupHorizontalLight: '/brand/hashhurdr-lockup-horizontal-light.svg',
} as const

// Hashling's poses, copied unchanged from the brand kit's `mascot/poses/` into web/public/brand/hashling. Every pose and
// the blink frame share one 52 x 44 pixel grid, so scale them by whole numbers only (see HashlingArt.vue). Bound strings
// for the same reason as above.
export const HASHLING_POSES = ['alert', 'sleeping', 'found-block', 'celebrate', 'thumbs-up', 'tinkering', 'lottery-ticket'] as const
export type HashlingPose = (typeof HASHLING_POSES)[number]

export const HASHLING_ART: Record<HashlingPose, string> = {
  alert: '/brand/hashling/hashling-alert.svg',
  sleeping: '/brand/hashling/hashling-sleeping.svg',
  'found-block': '/brand/hashling/hashling-found-block.svg',
  celebrate: '/brand/hashling/hashling-celebrate.svg',
  'thumbs-up': '/brand/hashling/hashling-thumbs-up.svg',
  tinkering: '/brand/hashling/hashling-tinkering.svg',
  'lottery-ticket': '/brand/hashling/hashling-lottery-ticket.svg',
}

/** The idle pose with its eyes closed: the one frame the logo mark blinks with. */
export const HASHLING_BLINK = '/brand/hashling/hashling-blink.svg'

/** The pixel grid every pose is drawn on. */
export const HASHLING_GRID = { width: 52, height: 44 } as const
