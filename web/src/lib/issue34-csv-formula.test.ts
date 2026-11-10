import { describe, expect, it } from 'vitest'
import { csvEscape, toCsv } from './csv'

// Issue #34: a miner name becomes a CSV column header. A spreadsheet reads a cell that starts with
// = + - @ (after any leading whitespace or control character) as a formula, and quoting does not stop that.
function headerOf(name: string): string {
  return toCsv([0], [{ name, data: [1] }]).split('\r\n')[0]!
}

describe('issue 34: CSV headers stay literal text in a spreadsheet', () => {
  it.each(['=SUM(A1:A9)', '+1+1', '-2+3', '@SUM(A1)'])('prefixes a header starting with %s', (name) => {
    expect(headerOf(name)).toBe(`time,'${name}`)
  })

  it('prefixes a header that starts with a tab or after leading whitespace', () => {
    expect(headerOf('\t=1+1')).toBe("time,'\t=1+1")
    expect(headerOf(' =1+1')).toBe("time,' =1+1")
    expect(headerOf('\t\t @cmd')).toBe("time,'\t\t @cmd")
  })

  it('prefixes a header that starts with a newline or carriage return, and still quotes it', () => {
    expect(headerOf('\n=1+1')).toBe('time,"\'\n=1+1"')
    expect(headerOf('\r+1')).toBe('time,"\'\r+1"')
  })

  it('prefixes and quotes a dangerous header that contains commas or quotes', () => {
    expect(headerOf('=HYPERLINK("http://x","y")')).toBe('time,"\'=HYPERLINK(""http://x"",""y"")"')
    expect(headerOf('=A1,B1')).toBe('time,"\'=A1,B1"')
  })

  it('leaves ordinary names unchanged', () => {
    expect(headerOf('Garage Gamma')).toBe('time,Garage Gamma')
    expect(headerOf('Hashrate, TH/s')).toBe('time,"Hashrate, TH/s"')
    expect(headerOf('rig-2')).toBe('time,rig-2')
    expect(headerOf('a=b')).toBe('time,a=b')
    expect(headerOf('x+y@z')).toBe('time,x+y@z')
  })

  it('keeps numeric samples numeric, including negatives', () => {
    const out = toCsv([0, 60, 120], [{ name: 'Temp', data: [-1.5, 0, null] }])
    expect(out).toBe(
      'time,Temp\r\n1970-01-01T00:00:00.000Z,-1.5\r\n1970-01-01T00:01:00.000Z,0\r\n1970-01-01T00:02:00.000Z,\r\n',
    )
    expect(csvEscape(-3)).toBe('-3')
  })
})
