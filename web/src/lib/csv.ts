/** Build a CSV (RFC 4180 quoting) from a time axis and named series. Timestamps are ISO-8601 UTC. */
export function csvEscape(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return ''
  const s = String(v)
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv(t: number[], columns: { name: string; data: (number | null)[] }[]): string {
  const lines = [['time', ...columns.map((c) => c.name)].map(csvEscape).join(',')]
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
