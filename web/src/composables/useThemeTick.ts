import { onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * A counter that increments whenever the theme, accent or density changes, so canvas charts (which cannot
 * use CSS variables) know to recompute their colours.
 */
export function useThemeTick() {
  const tick = ref(0)
  let obs: MutationObserver | null = null
  onMounted(() => {
    obs = new MutationObserver(() => tick.value++)
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'style', 'data-density'] })
  })
  onBeforeUnmount(() => obs?.disconnect())
  return tick
}
