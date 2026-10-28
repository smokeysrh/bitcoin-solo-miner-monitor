<script setup lang="ts">
import { Dices } from 'lucide-vue-next'
import { computed } from 'vue'
import { useFmt } from '@/composables/useFmt'
import { useLive } from '@/stores/live'
import EmptyState from '@/components/ui/EmptyState.vue'
import Term from '@/components/ui/Term.vue'
import WidgetFrame from '../WidgetFrame.vue'

const live = useLive()
const fmt = useFmt()
const odds = computed(() => (live.odds?.available ? live.odds : null))
const year = computed(() => odds.value?.horizons.year)
const rows = computed(() =>
  odds.value
    ? [
        ['Next 10 minutes', odds.value.horizons.ten_minutes],
        ['Today', odds.value.horizons.day],
        ['This month', odds.value.horizons.month],
        ['This year', odds.value.horizons.year],
        ['Next 10 years', odds.value.horizons.ten_years],
      ] as const
    : [],
)
</script>

<template>
  <WidgetFrame title="Your odds" subtitle="Chance of finding a block" to="/odds" link-label="Calculator">
    <div v-if="odds && year" data-testid="widget-odds">
      <p class="tnum text-4xl leading-none font-bold tracking-tight text-fg" data-testid="odds-year">{{ fmt.formatOdds(year.probability) }}</p>
      <p class="mt-1.5 text-sm text-muted">each year, about {{ fmt.formatFraction(year.probability, 3) }}</p>

      <dl class="mt-4 space-y-2 border-t border-line pt-3.5">
        <div v-for="[label, h] in rows" :key="label" class="flex items-baseline justify-between gap-3 text-sm">
          <dt class="text-muted">{{ label }}</dt>
          <dd class="tnum font-medium text-fg">{{ h.probability === 0 ? '0%' : fmt.formatOdds(h.probability) }}</dd>
        </div>
      </dl>

      <p class="mt-4 text-xs leading-relaxed text-subtle">
        On average that is one block every {{ fmt.formatDuration(odds.expected_seconds, 1) }}. Each hash is an
        independent ticket, so <Term k="odds">past luck changes nothing</Term>.
      </p>
    </div>
    <EmptyState v-else compact :icon="Dices" title="Odds need network data" :description="live.odds && !live.odds.available ? live.odds.reason : 'Waiting for the first reading.'" />
  </WidgetFrame>
</template>
