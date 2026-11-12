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
