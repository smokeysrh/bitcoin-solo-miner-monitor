/**
 * Does this person want stillness? True for the device setting (prefers-reduced-motion) and for the in-app
 * "Reduce motion" switch, which `applyLook` mirrors onto the document as `data-reduce-motion`. Read when it is needed,
 * so a change takes effect at the next pop-up or blink.
 */
export function prefersReducedMotion(): boolean {
  if (typeof document === 'undefined') return false
  if (document.documentElement.getAttribute('data-reduce-motion') === '1') return true
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
