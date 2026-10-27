// Runs before first paint so the page never flashes the wrong theme or accent colour.
// Kept as a separate file because the server sends `script-src 'self'` (no inline scripts).
(function () {
  try {
    var root = document.documentElement
    var theme = localStorage.getItem('bsmm.theme') || 'dark'
    if (theme === 'system') {
      theme = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
    }
    root.setAttribute('data-theme', theme)
    var accent = localStorage.getItem('bsmm.accent')
    if (accent && /^#[0-9a-fA-F]{6}$/.test(accent)) root.style.setProperty('--accent-base', accent)
    var density = localStorage.getItem('bsmm.density')
    if (density === 'compact') root.setAttribute('data-density', 'compact')
    if (localStorage.getItem('bsmm.reduceMotion') === '1') root.setAttribute('data-reduce-motion', '1')
  } catch (e) {
    /* storage can be blocked; the defaults are fine */
  }
})()
