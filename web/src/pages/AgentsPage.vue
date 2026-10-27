<script setup lang="ts">
import { Bot, ExternalLink, KeyRound, ShieldCheck, Sparkles, Terminal, Webhook } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import CopyButton from '@/components/ui/CopyButton.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useSession } from '@/stores/session'

const session = useSession()
const origin = location.origin
const tab = ref('mcp')
const tools = ref<string[]>([])

onMounted(async () => {
  try {
    const g = await fetch('/api/v1/agent/guide', { credentials: 'same-origin' })
    if (g.ok) tools.value = ((await g.json()) as { mcp?: { tools?: string[] } }).mcp?.tools ?? []
  } catch {
    /* the list is a nicety */
  }
})

const needsToken = computed(() => session.meta?.auth.mode === 'password')
const prompt = computed(() => `Read ${origin}/llms.txt and set up Solo Miner Monitor for me. Find my miners on the network, connect my node or pool if you can find it, and ask me before you change anything on a miner.`)

const mcpHttp = computed(() => JSON.stringify({ mcpServers: { 'solo-miner-monitor': { url: `${origin}/mcp`, ...(needsToken.value ? { headers: { Authorization: 'Bearer YOUR_TOKEN' } } : {}) } } }, null, 2))
const mcpStdio = computed(() => JSON.stringify({ mcpServers: { 'solo-miner-monitor': { command: 'bsmm', args: ['mcp', '--url', origin, ...(needsToken.value ? ['--token', 'YOUR_TOKEN'] : [])] } } }, null, 2))
const curl = computed(() => `# who am I and how far is setup?\ncurl ${origin}/api/v1/meta\n\n# everything the dashboard shows, in one call\ncurl ${needsToken.value ? '-H "Authorization: Bearer YOUR_TOKEN" ' : ''}${origin}/api/v1/overview\n\n# find miners on the network\ncurl -X POST ${needsToken.value ? '-H "Authorization: Bearer YOUR_TOKEN" ' : ''}-H "Content-Type: application/json" -d '{}' ${origin}/api/v1/discovery`)
const cli = `bsmm agent-guide      # the full instructions, as text\nbsmm status --json    # fleet summary for scripts\nbsmm doctor           # checks that explain themselves\nbsmm token create --name agent --scope read`
</script>

<template>
  <div class="space-y-5">
    <header class="max-w-3xl">
      <h2 class="text-2xl font-semibold tracking-tight text-fg">Agents &amp; API</h2>
      <p class="mt-1 text-sm leading-relaxed text-muted">Everything you can do in this app, an AI agent or a script can do too. Hand your agent one link and it can find your miners, connect your node and set up alerts.</p>
    </header>

    <section class="card relative overflow-hidden p-[var(--pad-card)]" data-testid="agent-prompt">
      <div class="pointer-events-none absolute -top-24 -right-10 size-72 rounded-full bg-accent/10 blur-3xl" aria-hidden="true" />
      <div class="relative">
        <p class="eyebrow flex items-center gap-2"><Sparkles class="size-3.5" aria-hidden="true" /> Quickest way</p>
        <h3 class="mt-2 text-lg font-semibold text-fg">Paste this to your AI agent</h3>
        <p class="mt-1 text-sm text-muted">Works with Claude, ChatGPT, Hermes and anything that can open a web link.</p>
        <CodeBlock class="mt-4" :code="prompt" />
        <div class="mt-4 flex flex-wrap gap-2">
          <CopyButton :text="prompt" label="Copy the prompt" variant="soft" size="sm" what="Prompt copied" />
          <Button size="sm" variant="ghost" href="/llms.txt" target="_blank" rel="noopener noreferrer"><template #icon><ExternalLink class="size-4" /></template>Read what the agent reads</Button>
        </div>
      </div>
    </section>

    <div v-if="needsToken" class="flex gap-3 rounded-2xl border border-warn/30 bg-warn-soft p-4">
      <KeyRound class="mt-0.5 size-5 shrink-0 text-warn" aria-hidden="true" />
      <div class="text-sm">
        <p class="font-medium text-fg">This dashboard is password protected, so your agent needs a token.</p>
        <p class="mt-1 text-muted">Create one with just the power it needs. “Read” is enough to look around; “Control” also lets it restart miners.</p>
        <Button to="/settings/security" size="sm" variant="secondary" class="mt-3">Create a token</Button>
      </div>
    </div>

    <MetricCard title="Connect it" :icon="Bot">
      <Tabs v-model="tab" label="Ways to connect" :tabs="[{ value: 'mcp', label: 'MCP (Claude, Cursor, Hermes)', icon: Bot }, { value: 'rest', label: 'REST API', icon: Webhook }, { value: 'cli', label: 'Command line', icon: Terminal }]">
        <template #mcp>
          <div class="space-y-4">
            <p class="max-w-3xl text-sm leading-relaxed text-muted">MCP lets an AI app use this monitor as a set of tools. Add one of these to your agent’s MCP settings. The first connects over the network; the second runs a small helper on the same computer as the agent.</p>
            <CodeBlock :code="mcpHttp" label="Over HTTP" />
            <CodeBlock :code="mcpStdio" label="Helper program (stdio)" />
          </div>
        </template>
        <template #rest>
          <div class="space-y-4">
            <p class="max-w-3xl text-sm leading-relaxed text-muted">A normal JSON API with predictable errors that say what to do next. Every endpoint is described in the OpenAPI document.</p>
            <CodeBlock :code="curl" label="Try it" />
            <div class="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" href="/docs" target="_blank" rel="noopener noreferrer"><template #icon><ExternalLink class="size-4" /></template>Interactive docs</Button>
              <Button size="sm" variant="secondary" href="/openapi.json" target="_blank" rel="noopener noreferrer">OpenAPI</Button>
              <Button size="sm" variant="secondary" href="/api/v1/agent/guide" target="_blank" rel="noopener noreferrer">Guide as JSON</Button>
              <Button size="sm" variant="secondary" href="/metrics" target="_blank" rel="noopener noreferrer">Prometheus metrics</Button>
            </div>
          </div>
        </template>
        <template #cli>
          <div class="space-y-4">
            <p class="max-w-3xl text-sm leading-relaxed text-muted">The same program that runs this dashboard also works as a tool on the command line, with <code class="rounded bg-surface-3 px-1">--json</code> output for scripts.</p>
            <CodeBlock :code="cli" label="Handy commands" />
          </div>
        </template>
      </Tabs>
    </MetricCard>

    <div class="grid gap-[var(--gap-grid)] lg:grid-cols-2">
      <MetricCard title="What an agent can do" :icon="Sparkles">
        <ul v-if="tools.length" class="flex flex-wrap gap-1.5" data-testid="tool-list"><li v-for="t in tools" :key="t"><Badge class="font-mono text-[11px]">{{ t }}</Badge></li></ul>
        <p v-else class="text-sm text-muted">Look at miners, odds and the network; scan and add miners; restart and pause; change pools; connect a node; set up notifications.</p>
      </MetricCard>
      <MetricCard title="Guard rails" :icon="ShieldCheck">
        <ul class="space-y-2.5 text-sm leading-relaxed text-muted">
          <li class="flex gap-2.5"><span class="mt-2 size-1.5 shrink-0 rounded-full bg-ok" aria-hidden="true" />A token only does what its power allows: read, control or admin.</li>
          <li class="flex gap-2.5"><span class="mt-2 size-1.5 shrink-0 rounded-full bg-ok" aria-hidden="true" />Speed and voltage changes are off unless you allow them in <RouterLink to="/settings/safety" class="text-accent-text underline underline-offset-2 hover:no-underline">Safety</RouterLink>, and only miner-approved values are accepted.</li>
          <li class="flex gap-2.5"><span class="mt-2 size-1.5 shrink-0 rounded-full bg-ok" aria-hidden="true" />Every change an agent makes is logged on the miner’s Activity tab.</li>
          <li class="flex gap-2.5"><span class="mt-2 size-1.5 shrink-0 rounded-full bg-ok" aria-hidden="true" />Anything can be previewed first with a dry run, so nothing has to be a surprise.</li>
        </ul>
      </MetricCard>
    </div>
  </div>
</template>
