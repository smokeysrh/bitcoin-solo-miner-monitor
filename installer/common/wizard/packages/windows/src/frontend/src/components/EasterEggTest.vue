<!--
  Easter Egg Test Component
  
  For testing the secret Bitcoin logo rain animation.
  "↑↑↓↓ is just the beginning" - Classic patterns hold power
-->

<template>
  <v-container class="easter-egg-test">
    <v-row justify="center">
      <v-col cols="12" md="8">
        <v-card class="pa-6">
          <v-card-title class="text-h4 mb-4 d-flex align-center">
            <BitcoinLogo size="md" class="mr-3" />
            Easter Egg Test
          </v-card-title>

          <v-card-text>
            <p class="text-body-1 mb-4">
              This component is for testing the secret animation feature. The
              animation respects accessibility preferences and includes
              cryptographic security.
            </p>

            <v-alert type="info" variant="tonal" class="mb-4">
              <template v-slot:prepend>
                <v-icon>mdi-information</v-icon>
              </template>
              <div>
                <strong>Animation Status:</strong>
                {{
                  easterEgg.animationsEnabled
                    ? "Enabled"
                    : "Disabled (respecting reduced motion preference)"
                }}
              </div>
              <div>
                <strong>Easter Egg Active:</strong>
                {{ easterEgg.isActive ? "Yes" : "No" }}
              </div>
            </v-alert>

            <div class="mb-4">
              <h3 class="text-h6 mb-2">Cryptic Hints:</h3>
              <ul class="text-body-2">
                <li>Look for patterns from gaming's golden age</li>
                <li>The year 1986 holds significance</li>
                <li>Some sequences are universal in gaming culture</li>
                <li>Console messages may contain clues</li>
                <li>Mobile users: try tapping Bitcoin logos rapidly</li>
              </ul>
            </div>

            <div class="mb-4">
              <h3 class="text-h6 mb-2">Technical Details:</h3>
              <ul class="text-body-2">
                <li>Uses cryptographic hash verification for security</li>
                <li>Respects prefers-reduced-motion accessibility setting</li>
                <li>Hardware-accelerated animations for smooth performance</li>
                <li>Automatic cleanup after 5 seconds</li>
                <li>25 Bitcoin logos with realistic physics</li>
              </ul>
            </div>

            <!-- Development only debug button -->
            <v-btn
              v-if="isDevelopment"
              color="primary"
              variant="outlined"
              @click="triggerDebugAnimation"
              class="mb-4"
            >
              <v-icon start>mdi-play</v-icon>
              Debug Trigger (Dev Only)
            </v-btn>

            <v-divider class="my-4"></v-divider>

            <div class="text-caption text-medium-emphasis">
              <v-icon size="small" class="mr-1">mdi-gamepad-variant</v-icon>
              "1986... some things never change" - Look for the classic pattern
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { computed } from "vue";
import { useEasterEgg } from "../composables/useEasterEgg";
import BitcoinLogo from "./BitcoinLogo.vue";

export default {
  name: "EasterEggTest",
  
  components: {
    BitcoinLogo,
  },

  setup() {
    // Initialize easter egg composable
    const easterEgg = useEasterEgg();

    // Check if we're in development mode
    const isDevelopment = computed(() => {
      return process.env.NODE_ENV === "development";
    });

    // Debug trigger for development
    const triggerDebugAnimation = () => {
      if (isDevelopment.value && easterEgg._debugTrigger) {
        easterEgg._debugTrigger();
      }
    };

    return {
      easterEgg,
      isDevelopment,
      triggerDebugAnimation,
    };
  },
};
</script>

<style scoped>
.easter-egg-test {
  min-height: 100vh;
  padding: 2rem 0;
}

/* Subtle hint styling */
.text-caption {
  opacity: 0.8;
}

.text-caption:hover {
  opacity: 1;
  color: rgb(var(--v-theme-primary));
}
</style>
