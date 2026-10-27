<script setup lang="ts">
import { Calculator, Coins, Dices, RotateCcw, Sparkles } from 'lucide-vue-next'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { api, describeError } from '@/lib/api'
import type { HorizonKey, Odds, OddsAvailable } from '@/lib/types'
import { useLive } from '@/stores/live'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Field from '@/components/ui/Field.vue'
import Input from '@/components/ui/Input.vue'
import KeyValue from '@/components/ui/KeyValue.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import Term from '@/components/ui/Term.vue'

const live = useLive()
const fmt = useFmt()

// null = "use my live value"; anything typed becomes a what-if
const whatIf = reactive<{ ths: number | null; difficulty: number | null; power: number | null; growth: number | null }>({ ths: null, difficulty: null, power: null, growth: null })
const result = ref<Odds | null>(null)
const error = ref<string | null>(null)
let timer: ReturnType<typeof setTimeout> | null = null
let ctrl: AbortController | null = null

const active = computed(() => whatIf.ths !== null || whatIf.difficulty !== null || whatIf.power !== null || whatIf.growth !== null)
const shown = computed<Odds | null>(() => (active.value ? result.value : live.odds))
const o = computed<OddsAvailable | null>(() => (shown.value?.available ? shown.value : null))

async function run(): Promise<void> {
  ctrl?.abort()
  ctrl = new AbortController()
  try {
    result.value = await api.odds(
      {
        hashrate_ths: whatIf.ths ?? undefined,
        difficulty: whatIf.difficulty ?? undefined,
        power_w: whatIf.power ?? undefined,
        growth: whatIf.growth !== null ? whatIf.growth / 100 : undefined,
      },
      ctrl.signal,
    )
    error.value = null
  } catch (e) {
    if (!ctrl?.signal.aborted) error.value = describeError(e)
  }
}
watch(whatIf, () => {
  if (timer) clearTimeout(timer)
  if (active.value) timer = setTimeout(run, 250)
})
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
  ctrl?.abort()
})

const liveThs = computed(() => (live.summary?.hashrate_hs ?? 0) / 1e12)
function scaleHash(f: number): void {
  whatIf.ths = Math.round(Math.max(liveThs.value, 0.01) * f * 100) / 100
}
function bumpDifficulty(f: number): void {
  const d = live.network?.difficulty
  if (d) whatIf.difficulty = Math.round(d * f)
}
function reset(): void {
  Object.assign(whatIf, { ths: null, difficulty: null, power: null, growth: null })
  result.value = null
}

const HORIZONS: [HorizonKey, string][] = [
  ['hour', 'In the next hour'],
  ['day', 'Today'],
  ['week', 'This week'],
  ['month', 'This month'],
  ['year', 'This year'],
  ['five_years', 'In 5 years'],
  ['ten_years', 'In 10 years'],
]
// width on a log scale so "1 in 12 million" and "1 in 148" are both visible
const barWidth = (p: number): number => Math.max(2, Math.min(100, ((Math.log10(p) + 8) / 8) * 100))
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 class="text-2xl font-semibold tracking-tight text-fg">Odds &amp; costs</h2>
        <p class="mt-1 max-w-2xl text-sm text-muted">The honest numbers: how likely a block is, what the electricity costs, and what changes if you add hardware.</p>
      </div>
      <Button v-if="active" variant="ghost" size="sm" @click="reset"><template #icon><RotateCcw class="size-4" /></template>Back to my real numbers</Button>
    </header>

    <div class="grid gap-[var(--gap-grid)] xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="space-y-[var(--gap-grid)]">
        <section v-if="o" class="card relative overflow-hidden p-[var(--pad-card)]" data-testid="odds-hero">
          <div class="pointer-events-none absolute -top-24 -right-10 size-72 rounded-full bg-accent/10 blur-3xl" aria-hidden="true" />
          <div class="relative">
            <p class="eyebrow flex items-center gap-2"><Dices class="size-3.5" aria-hidden="true" /> {{ active ? 'What if…' : 'Your chance of finding a block' }}</p>
            <p class="mt-3 flex flex-wrap items-baseline gap-x-3">
              <span class="text-gradient-accent tnum text-5xl font-bold tracking-tight sm:text-6xl">{{ fmt.formatOdds(o.horizons.year.probability) }}</span>
              <span class="text-lg text-muted">per year</span>
            </p>
            <p class="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
              At {{ fmt.hashrate(o.hashrate) }} you hold about {{ fmt.formatFraction(o.share_of_network, 7) }} of the network. On average you would wait
              <b class="text-fg">{{ fmt.formatDuration(o.expected_seconds) }}</b> for a block, but luck is not scheduled: the next hash is just as likely to win as any other.
            </p>
          </div>
        </section>
        <EmptyState v-else-if="shown && !shown.available" :icon="Dices" title="Odds need network data" :description="shown.reason">
          <Button to="/settings/sources" variant="soft">Connect a data source</Button>
        </EmptyState>

        <MetricCard v-if="o" title="Chance over time" :icon="Dices">
          <ul class="space-y-3.5" data-testid="odds-horizons">
            <li v-for="[k, label] in HORIZONS" :key="k" class="grid grid-cols-[8.5rem_1fr_auto] items-center gap-3 text-sm sm:grid-cols-[10rem_1fr_9rem]">
              <span class="text-muted">{{ label }}</span>
              <span class="h-2 overflow-hidden rounded-full bg-surface-3" aria-hidden="true">
                <span class="block h-full rounded-full bg-gradient-to-r from-accent/40 to-accent" :style="{ width: `${barWidth(o.horizons[k].probability)}%` }" />
              </span>
              <span class="tnum text-right font-medium text-fg">{{ fmt.formatOdds(o.horizons[k].probability) }}</span>
            </li>
          </ul>
          <p class="mt-4 text-xs text-subtle">Bars use a log scale so very small chances stay visible.</p>
        </MetricCard>

        <div v-if="o" class="grid gap-[var(--gap-grid)] md:grid-cols-2">
          <MetricCard title="Electricity vs. payout" :icon="Coins">
            <KeyValue :rows="[
              { label: 'Power drawn', value: fmt.formatPower(o.economics.power_w) },
              { label: `Cost per day`, value: fmt.money(o.economics.cost_per_day) },
              { label: 'Cost per month', value: fmt.money(o.economics.cost_per_month) },
              { label: 'Cost per year', value: fmt.money(o.economics.cost_per_year) },
              { label: 'Expected payout per year', value: o.economics.expected_value_per_year != null ? fmt.money(o.economics.expected_value_per_year) : '–' },
              { label: 'Payout vs. cost', value: o.economics.ev_to_cost_ratio != null ? `${(o.economics.ev_to_cost_ratio * 100).toFixed(0)}%` : '–', tone: (o.economics.ev_to_cost_ratio ?? 0) >= 1 ? 'ok' : 'warn' },
              { label: 'Break-even Bitcoin price', value: o.economics.break_even_btc_price ? fmt.money(o.economics.break_even_btc_price, 0) : '–' },
            ]" />
            <p class="mt-4 text-xs leading-relaxed text-subtle">
              “Expected payout” is an average over many lifetimes: you will almost certainly receive nothing, and very rarely a whole block ({{ o.economics.block_reward_btc }} BTC) at once.
              Electricity price: {{ fmt.money(o.economics.price_per_kwh, 3) }}/kWh. <RouterLink to="/settings/energy" class="text-accent-text underline underline-offset-2 hover:no-underline">Change</RouterLink>
            </p>
          </MetricCard>
          <MetricCard title="Work done so far" :icon="Sparkles">
            <KeyValue :rows="[
              { label: 'Hashes tried', value: fmt.formatSI(o.work.total_hashes, 'H') },
              { label: 'Blocks of work', value: o.work.expected_blocks_of_work.toExponential(2) },
              { label: 'Chance you would have won by now', value: fmt.formatFraction(o.work.chance_found_by_now, 4) },
              { label: 'Blocks found', value: String(o.work.blocks_found), tone: o.work.blocks_found ? 'ok' : undefined },
              { label: 'Best share', value: fmt.formatDifficulty(o.best_share.difficulty) },
              { label: 'Closest you came', value: o.best_share.progress_to_block != null ? fmt.formatFraction(o.best_share.progress_to_block, 4) + ' of a block' : '–' },
            ]" />
            <p class="mt-4 text-xs leading-relaxed text-subtle"><Term k="bestshare">Best share</Term> shows the luckiest single hash. It is a fun measure of luck, not a sign you are getting closer.</p>
          </MetricCard>
        </div>

        <MetricCard v-if="o?.plain_english?.length" title="In plain English">
          <ul class="space-y-2.5 text-sm leading-relaxed text-muted">
            <li v-for="line in o.plain_english" :key="line" class="flex gap-2.5"><span class="mt-2 size-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />{{ line }}</li>
          </ul>
        </MetricCard>
      </div>

      <aside class="xl:sticky xl:top-24 xl:self-start">
        <MetricCard title="What-if calculator" :icon="Calculator">
          <p class="mb-4 text-sm text-muted">Leave a box empty to use your real value. Type to see what changes.</p>
          <div class="space-y-4">
            <Field :label="`Hashrate (your fleet: ${fmt.hashrate(live.summary?.hashrate_hs)})`">
              <template #default="{ id }"><Input :id="id" v-model="whatIf.ths" type="number" :min="0" :step="0.1" suffix="TH/s" :placeholder="liveThs.toFixed(2)" data-testid="whatif-ths" /></template>
            </Field>
            <div class="flex flex-wrap gap-1.5">
              <Button v-for="f in [2, 5, 10, 100]" :key="f" size="xs" variant="secondary" @click="scaleHash(f)">×{{ f }}</Button>
            </div>
            <Field :label="`Difficulty (now: ${fmt.formatDifficulty(live.network?.difficulty)})`">
              <template #default="{ id }"><Input :id="id" v-model="whatIf.difficulty" type="number" :min="0" :placeholder="live.network?.difficulty ? String(Math.round(live.network.difficulty)) : ''" /></template>
            </Field>
            <div class="flex flex-wrap gap-1.5">
              <Button size="xs" variant="secondary" @click="bumpDifficulty(1.1)">+10%</Button>
              <Button size="xs" variant="secondary" @click="bumpDifficulty(1.5)">+50%</Button>
              <Button size="xs" variant="secondary" @click="bumpDifficulty(2)">×2</Button>
            </div>
            <Field label="Power drawn">
              <template #default="{ id }"><Input :id="id" v-model="whatIf.power" type="number" :min="0" suffix="W" :placeholder="String(Math.round(live.summary?.power_wall_w ?? live.summary?.power_w ?? 0))" /></template>
            </Field>
            <Field label="Network growth per year" hint="If the whole network keeps getting faster, odds shrink over time. 30 means +30% a year.">
              <template #default="{ id, describedBy }"><Input :id="id" v-model="whatIf.growth" type="number" suffix="%" :described-by="describedBy" placeholder="0" /></template>
            </Field>
          </div>
          <p v-if="error" class="mt-4 text-sm text-bad" role="alert">{{ error }}</p>
        </MetricCard>
      </aside>
    </div>
  </div>
</template>
