/** Build a CSV (RFC 4180 quoting) from a time axis and named series. Timestamps are ISO-8601 UTC. */
export function csvEscape(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return ''
  const s = String(v)
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/**
 * Header cells hold user-chosen text (miner names). A spreadsheet treats a cell starting with = + - @
 * (after any leading whitespace or control character), or with a tab or carriage return, as a formula,
 * and quoting does not stop that. Such headers get a leading apostrophe so they open as literal text.
 * Only headers go through this: sample values are numbers and stay numeric (a negative is not a formula).
 */
const FORMULA_START = /^[\s\u0000-\u001f]*[=+\-@]|^[\t\r]/

export function csvHeader(name: string): string {
  return csvEscape(FORMULA_START.test(name) ? `'${name}` : name)
}

export function toCsv(t: number[], columns: { name: string; data: (number | null)[] }[]): string {
  const lines = [['time', ...columns.map((c) => c.name)].map(csvHeader).join(',')]
  t.forEach((ts, i) => {
    lines.push([new Date(ts * 1000).toISOString(), ...columns.map((c) => c.data[i] ?? null)].map(csvEscape).join(','))
  })
  return lines.join('\r\n') + '\r\n'
}

export function downloadText(filename: string, text: string, mime = 'text/csv;charset=utf-8'): void {
  const url = URL.createObjectURL(new Blob([text], { type: mime }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
