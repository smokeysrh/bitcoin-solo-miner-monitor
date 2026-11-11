<script setup lang="ts">
import { computed } from 'vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import { useFmt } from '@/composables/useFmt'
import type { EpochInfo, HalvingInfo, NetworkState } from '@/lib/types'

// The wall display's Bitcoin network panel, read from across a room: the next halving leads, the next difficulty
// change follows, and height, difficulty and price are the smaller row underneath. A value that is missing or out of
// date says "Unavailable" and never a zero. Sizes follow the screen (see the style block) and never drop below the
// floors there.
const props = defineProps<{ net: NetworkState | null }>()
const fmt = useFmt()

const UNAVAILABLE = 'Unavailable'

/** Out-of-date network data is not shown as if it were current. */
const fresh = computed(() => (props.net && !props.net.stale ? props.net : null))
const halving = computed(() => fresh.value?.halving ?? null)
const epoch = computed(() => fresh.value?.epoch ?? null)
const height = computed(() => fresh.value?.height ?? null)
const difficulty = computed(() => fresh.value?.difficulty ?? null)
const price = computed(() => props.net?.btc_price || null)

/** Only the app's own estimate, and only when it supplied one. */
function estimate(info: HalvingInfo | EpochInfo | null): string | null {
  if (!info?.estimated_date) return null
  const date = fmt.formatDate(info.estimated_date)
  if (date === '–') return null
  const inAbout = Number.isFinite(info.seconds_remaining) ? ` (in about ${fmt.formatDuration(info.seconds_remaining)})` : ''
  return `Estimated ${date}${inAbout}`
}
const halvingEstimate = computed(() => estimate(halving.value))
const epochEstimate = computed(() => estimate(epoch.value))
</script>

<template>
  <div class="k-net mx-auto w-full text-center" data-testid="kiosk-network">
    <div>
      <p class="k-label font-semibold text-muted" data-testid="kiosk-halving-label">Next halving</p>
      <div class="flex flex-wrap items-baseline justify-center gap-x-[0.3em]">
        <p class="k-halving tnum leading-none font-bold" :class="halving ? 'text-accent-text' : 'k-off text-muted'" data-testid="kiosk-halving-value">{{ halving ? fmt.formatNumber(halving.blocks_remaining) : UNAVAILABLE }}</p>
        <p v-if="halving" class="k-label font-medium text-muted">blocks to go</p>
      </div>
      <p v-if="halvingEstimate" class="k-note text-muted" data-testid="kiosk-halving-estimate">{{ halvingEstimate }}</p>
      <ProgressBar v-if="halving" class="k-bar" :value="halving.progress" tone="violet" :height="12" label="Progress to the next halving" />
    </div>

    <div class="k-gap">
      <p class="k-label font-semibold text-muted" data-testid="kiosk-epoch-label">Next difficulty change</p>
      <div class="flex flex-wrap items-baseline justify-center gap-x-[0.3em]">
        <p class="k-epoch tnum leading-none font-bold" :class="epoch ? 'text-accent-text' : 'k-off text-muted'" data-testid="kiosk-epoch-value">{{ epoch ? fmt.formatNumber(epoch.blocks_remaining) : UNAVAILABLE }}</p>
        <p v-if="epoch" class="k-label font-medium text-muted">blocks to go</p>
      </div>
      <p v-if="epochEstimate" class="k-note text-muted" data-testid="kiosk-epoch-estimate">{{ epochEstimate }}</p>
      <ProgressBar v-if="epoch" class="k-bar" :value="epoch.progress" tone="info" :height="12" label="Progress to the next adjustment" />
    </div>

    <dl class="k-gap grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-3">
      <div>
        <dt class="k-label-small text-muted" data-testid="kiosk-height-label">Block height</dt>
        <dd class="k-small tnum leading-none font-bold" :class="height === null ? 'k-off text-muted' : 'text-fg'" data-testid="kiosk-height-value">{{ height === null ? UNAVAILABLE : fmt.formatNumber(height) }}</dd>
      </div>
      <div>
        <dt class="k-label-small text-muted" data-testid="kiosk-difficulty-label">Difficulty</dt>
        <dd class="k-small tnum leading-none font-bold" :class="difficulty === null ? 'k-off text-muted' : 'text-fg'" data-testid="kiosk-difficulty-value">{{ difficulty === null ? UNAVAILABLE : fmt.formatDifficulty(difficulty) }}</dd>
      </div>
      <div>
        <dt class="k-label-small text-muted" data-testid="kiosk-price-label">Bitcoin price</dt>
        <dd class="k-small tnum leading-none font-bold" :class="price === null ? 'k-off text-muted' : 'text-fg'" data-testid="kiosk-price-value">{{ price === null ? UNAVAILABLE : fmt.money(price, 0) }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
/* Type follows the smaller side of the screen (vh on landscape, vw on portrait), so the panel fills a wall display
   without clipping. The rem floors keep every size at or above the old panel (3rem values, 11px labels). */
.k-net {
  --k-halving: max(4.5rem, min(16vh, 19.5vw));
  --k-epoch: max(3.5rem, min(8.8vh, 12vw));
  --k-small: max(3rem, min(6.7vh, 5vw));
  --k-label: max(1rem, min(2.9vh, 2.9vw));
  --k-label-small: max(0.875rem, min(2.25vh, 2.25vw));
  --k-note: max(1rem, min(2.6vh, 2.6vw));
}
.k-halving {
  --k-size: var(--k-halving);
  font-size: var(--k-size);
}
.k-epoch {
  --k-size: var(--k-epoch);
  font-size: var(--k-size);
}
.k-small {
  --k-size: var(--k-small);
  font-size: var(--k-size);
  margin-top: 0.25rem;
}
.k-label {
  font-size: var(--k-label);
  line-height: 1.3;
}
.k-label-small {
  font-size: var(--k-label-small);
  line-height: 1.3;
}
.k-note {
  font-size: var(--k-note);
  line-height: 1.3;
  margin-top: 0.5rem;
}
/* "Unavailable" is a word, not a number: half size so it fits the same space. Declared after the sizes to win. */
.k-off {
  font-size: calc(var(--k-size) * 0.5);
}
.k-gap {
  margin-top: max(1.5rem, 3.5vh);
}
.k-bar {
  margin-top: 0.75rem;
  height: max(12px, 1.6vh) !important; /* ProgressBar sets its height inline */
}
</style>
