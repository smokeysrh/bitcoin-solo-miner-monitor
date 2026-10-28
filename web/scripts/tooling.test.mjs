import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { mkdtemp, readdir, rm } from 'node:fs/promises'
import { createServer } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'
import { requireDemo } from './demo-preflight.mjs'

test('OPS-11 demo gate requires literal true and fails closed on malformed/unreachable responses', async () => {
  let payload = '{"demo":true}'
  let status = 200
  const server = createServer((req, res) => { res.writeHead(status); res.end(payload) })
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  const base = `http://127.0.0.1:${server.address().port}`
  try {
    await requireDemo(base)
    for (const body of ['{}', '{"demo":false}', '{"demo":"true"}', 'null', 'not-json']) {
      payload = body
      await assert.rejects(requireDemo(base), /Refusing browser tooling/)
    }
    payload = '{"demo":true}'
    status = 403
    await assert.rejects(requireDemo(base), /Refusing browser tooling/)
  } finally {
    server.closeAllConnections()
    await new Promise(resolve => server.close(resolve))
  }
  await assert.rejects(requireDemo(base), /Refusing browser tooling/)
})

async function run(args, env) {
  const child = spawn(process.execPath, args, { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] })
  let output = ''
  child.stdout.on('data', b => { output += b })
  child.stderr.on('data', b => { output += b })
  const timer = setTimeout(() => child.kill(), 15000)
  const [code] = await once(child, 'exit')
  clearTimeout(timer)
  return { code, output }
}

for (const entry of ['screenshots', 'e2e', 'audit']) {
  test(`OPS-11 ${entry} refuses non-demo before reads, writes or screenshots`, async () => {
    const requests = []
    const server = createServer((req, res) => {
      requests.push([req.method, req.url])
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify(req.url === '/api/v1/meta' ? { demo: false } : req.url === '/api/v1/devices' ? [{ id: 'fixture', name: 'NerdQAxe' }] : {}))
    })
    server.listen(0, '127.0.0.1')
    await once(server, 'listening')
    const out = await mkdtemp(join(tmpdir(), 'bsmm-tooling-'))
    try {
      const args = entry === 'screenshots' ? ['scripts/make-screenshots.mjs'] : entry === 'audit' ? ['e2e/audit.mjs', out] :
        ['node_modules/playwright/cli.js', 'test', '--project=desktop', '--grep=dashboard shows live', '--timeout=2000', `--output=${out}`]
      const result = await run(args, { BASE: `http://127.0.0.1:${server.address().port}`, OUT: out, ROUTES: '/', SIZES: 'desktop' })
      assert.notEqual(result.code, 0)
      assert.deepEqual(requests, [['GET', '/api/v1/meta']], result.output)
      assert.match(result.output, /demo/i)
      const files = await readdir(out, { recursive: true })
      assert.ok(!files.some(p => p.endsWith('.png')), 'non-demo screenshots must never be written')
    } finally {
      server.closeAllConnections()
      server.close()
      await rm(out, { recursive: true, force: true })
    }
  })
}

test('OPS-12 package shots enumerates the real generator without a browser', async () => {
  const { readFile } = await import('node:fs/promises')
  const { scripts } = JSON.parse(await readFile('package.json', 'utf8'))
  assert.equal(scripts.shots, 'node scripts/make-screenshots.mjs')
  const result = await run(['scripts/make-screenshots.mjs', '--list'], { BASE: 'http://127.0.0.1:1' })
  assert.equal(result.code, 0, result.output)
  assert.match(result.output, /dashboard/)
  assert.match(result.output, /phone/)
})
