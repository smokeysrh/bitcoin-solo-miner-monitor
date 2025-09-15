<template>
  <div class="d-flex flex-column h-100">
    <div class="flex-grow-1 overflow-y-auto">
      <v-container class="fill-height d-flex align-center">
        <v-row
          class="justify-center align-center w-100"
          style="min-height: 100%"
        >
          <v-col cols="12" md="10" lg="8" xl="6">
            <!-- Welcome Header -->
            <div class="text-center mb-8 welcome-header">
              <div class="mb-6 bitcoin-hero">
                <div class="bitcoin-logo-hero">
                  <BitcoinLogo 
                    size="hero" 
                    variant="glow" 
                    :animated="true"
                    alt-text="Bitcoin Solo Miner Monitor Logo"
                    aria-label="Bitcoin Logo - Welcome to Solo Mining"
                    @logo-loaded="onLogoLoaded"
                    @logo-error="onLogoError"
                  />
                </div>
              </div>
              <h1 class="text-h3 mb-4 welcome-title">
                Welcome to <span class="text-primary">Bitcoin</span> Solo Miner
                Monitoring
              </h1>
              <p class="text-subtitle-1 mb-6 welcome-subtitle">
                This wizard will help you set up your mining monitoring
                environment. Let's get started on your Bitcoin journey!
              </p>
            </div>

            <!-- Experience Level Section -->
            <div class="mb-8">
              <h2 class="text-h5 mb-4">Tell us about your mining experience</h2>
              <p class="mb-6">
                We'll customize your experience based on your familiarity with
                Bitcoin mining.
              </p>

              <div class="d-flex justify-center mb-6">
                <v-btn-toggle
                  v-model="experienceLevel"
                  mandatory
                  color="primary"
                  variant="outlined"
                  divided
                  class="experience-toggle"
                >
                  <v-btn value="beginner" class="experience-btn">
                    <v-icon start>mdi-school</v-icon>
                    Beginner
                  </v-btn>
                  <v-btn value="intermediate" class="experience-btn">
                    <v-icon start>mdi-account</v-icon>
                    Intermediate
                  </v-btn>
                  <v-btn value="advanced" class="experience-btn">
                    <v-icon start>mdi-account-star</v-icon>
                    Advanced
                  </v-btn>
                </v-btn-toggle>
              </div>

              <v-alert
                v-if="experienceLevel === 'beginner'"
                type="info"
                variant="outlined"
                class="mb-6 experience-description"
              >
                <div class="experience-header">
                  <v-icon start color="info">mdi-school</v-icon>
                  <strong>Perfect for newcomers!</strong>
                </div>
                <div class="experience-details mt-3">
                  <p><strong>What you'll get:</strong></p>
                  <ul class="experience-list">
                    <li>
                      <strong>Simple Mode:</strong> Streamlined interface with
                      essential features
                    </li>
                    <li>
                      <strong>Conservative Settings:</strong> Safe temperature
                      alerts (70°C)
                    </li>
                    <li>
                      <strong>Core Widgets:</strong> Miner status, hashrate,
                      temperature, and earnings
                    </li>
                    <li>
                      <strong>Extra Guidance:</strong> Helpful tips and
                      explanations throughout
                    </li>
                    <li>
                      <strong>Grid Layout:</strong> Spacious, easy-to-read
                      dashboard
                    </li>
                  </ul>
                </div>
              </v-alert>

              <v-alert
                v-if="experienceLevel === 'intermediate'"
                type="info"
                variant="outlined"
                class="mb-6 experience-description"
              >
                <div class="experience-header">
                  <v-icon start color="info">mdi-account</v-icon>
                  <strong>Great choice for growing expertise!</strong>
                </div>
                <div class="experience-details mt-3">
                  <p><strong>What you'll get:</strong></p>
                  <ul class="experience-list">
                    <li>
                      <strong>Full Interface:</strong> Access to all main
                      features
                    </li>
                    <li>
                      <strong>Balanced Settings:</strong> Standard refresh rates
                      and alerts (75°C)
                    </li>
                    <li>
                      <strong>Enhanced Widgets:</strong> Core widgets plus
                      network difficulty tracking
                    </li>
                    <li>
                      <strong>Dashboard Layout:</strong> Optimized for
                      monitoring multiple metrics
                    </li>
                    <li>
                      <strong>Compact Tables:</strong> More data density for
                      better overview
                    </li>
                  </ul>
                </div>
              </v-alert>

              <v-alert
                v-if="experienceLevel === 'advanced'"
                type="info"
                variant="outlined"
                class="mb-6 experience-description"
              >
                <div class="experience-header">
                  <v-icon start color="info">mdi-account-star</v-icon>
                  <strong>Welcome, expert!</strong>
                </div>
                <div class="experience-details mt-3">
                  <p><strong>What you'll get:</strong></p>
                  <ul class="experience-list">
                    <li>
                      <strong>Maximum Performance:</strong> Fastest refresh (5s)
                      and polling (10s)
                    </li>
                    <li>
                      <strong>Aggressive Monitoring:</strong> Maximum safe
                      temperature threshold (80°C)
                    </li>
                    <li>
                      <strong>All Widgets:</strong> Complete dashboard with
                      power consumption tracking
                    </li>
                    <li>
                      <strong>Advanced Features:</strong> Full access to all
                      configuration options
                    </li>
                    <li>
                      <strong>Data Dense:</strong> Maximum information density
                      for power users
                    </li>
                  </ul>
                </div>
              </v-alert>
            </div>

            <!-- Personalization Section -->
            <div>
              <h2 class="text-h5 mb-4">Personalize your experience</h2>
              <v-text-field
                v-model="userName"
                label="Your Name (Optional)"
                hint="We'll use this to personalize your dashboard"
                persistent-hint
                variant="outlined"
                class="mb-4 name-input"
                prepend-inner-icon="mdi-account-circle"
                color="primary"
              ></v-text-field>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </div>


  </div>
</template>

<script>
import BitcoinLogo from '../BitcoinLogo.vue'

export default {
  name: "WelcomeScreen",
  
  components: {
    BitcoinLogo
  },

  data() {
    return {
      experienceLevel: "beginner",
      userName: "",
    };
  },

  methods: {
    setExperience() {
      // Emit the selected experience level to the parent component
      this.$emit("set-experience", this.experienceLevel);
    },
    
    onLogoLoaded(event) {
      console.log('Bitcoin logo loaded successfully:', event)
    },
    
    onLogoError(event) {
      console.error('Bitcoin logo failed to load:', event)
    }
  },

  watch: {
    experienceLevel: {
      immediate: true,
      handler(newLevel) {
        if (newLevel) {
          this.setExperience();
        }
      },
    },
  },
};
</script>
<style scoped>
/* Import shared wizard styles for standardized info bubbles */
@import "./shared-wizard-styles.css";

/* Welcome screen styling */
.welcome-header {
  padding: var(--spacing-xxl) 0;
  background: linear-gradient(
    135deg,
    var(--color-primary-alpha-10) 0%,
    transparent 100%
  );
  border-radius: var(--radius-xl);
  margin-bottom: var(--spacing-xxxl) !important;
  border: 1px solid var(--color-border-subtle);
}

.bitcoin-hero {
  position: relative;
  display: inline-block;
}

.bitcoin-logo-hero {
  margin: 0 auto;
  filter: drop-shadow(0 4px 12px var(--color-primary-alpha-30));
  transition: all var(--transition-slow);
  animation: bitcoinFloat 3s ease-in-out infinite;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bitcoin-logo-hero:hover {
  transform: scale(1.1) rotate(10deg);
  filter: drop-shadow(0 8px 20px var(--color-primary-alpha-30));
}

@keyframes bitcoinFloat {
  0%,
  100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

.welcome-title {
  font-weight: var(--font-weight-bold);
  background: linear-gradient(
    135deg,
    var(--color-text-primary) 0%,
    var(--color-primary) 100%
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--spacing-lg) !important;
}

.welcome-subtitle {
  color: var(--color-text-secondary);
  font-size: var(--font-size-h4);
  line-height: var(--line-height-relaxed);
  max-width: 600px;
  margin: 0 auto var(--spacing-xxl) auto;
}

/* Experience level toggle styling */
.experience-toggle {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-2);
  border: 1px solid var(--color-border);
}

.experience-btn {
  min-width: 140px;
  height: 56px;
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
  border-radius: 0 !important;
  border: none !important;
}

.experience-btn::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    var(--color-primary-alpha-10),
    transparent
  );
  transition: left var(--transition-slow);
}

.experience-btn:hover::before {
  left: 100%;
}

/* Fix the active button styling to prevent overflow */
:deep(.v-btn-toggle .v-btn--active) {
  background: var(--color-primary) !important;
  color: var(--color-text-on-primary) !important;
  box-shadow: inset 0 0 0 2px var(--color-primary) !important;
  transform: none !important;
  z-index: 1;
}

:deep(.v-btn-toggle .v-btn) {
  border-radius: 0 !important;
  border: none !important;
  margin: 0 !important;
}

/* Name input styling */
.name-input {
  max-width: 400px;
  margin: 0 auto;
}

.name-input :deep(.v-field) {
  background: var(--color-surface-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  transition: all var(--transition-normal);
}

.name-input :deep(.v-field:hover) {
  background: var(--color-surface-elevated);
  transform: translateY(-2px);
  box-shadow: var(--shadow-2);
  border-color: var(--color-primary);
}

.name-input :deep(.v-field--focused) {
  background: var(--color-surface-elevated);
  box-shadow: var(--shadow-focus);
  border-color: var(--color-primary);
}

/* Continue button styling */
.continue-btn {
  min-width: 160px;
  height: 56px;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-h4);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px var(--color-primary-alpha-30);
  transition: all var(--transition-bounce);
  position: relative;
  overflow: hidden;
}

.continue-btn::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.2),
    transparent
  );
  transition: left 0.5s;
}

.continue-btn:hover::before {
  left: 100%;
}

.continue-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px var(--color-primary-alpha-30);
}

.continue-btn:active {
  transform: translateY(-1px);
}

/* Footer styling - Fixed for static positioning */
.welcome-footer {
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(var(--color-surface), 0.8) 100%
  );
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--color-border-subtle);
  position: static; /* Ensure static positioning, not fixed */
  margin-top: auto; /* Push to bottom of content */
}

/* Layout utilities */
.h-100 {
  height: 100%;
}

.v-container.fill-height {
  min-height: 100%;
  height: 100%;
}

.v-container.fill-height .v-row {
  flex: 1;
  margin: 0;
}

.w-100 {
  width: 100%;
}

/* Experience level description styling */
.experience-description {
  text-align: left !important;
  max-width: 600px;
  margin: 0 auto 24px auto;
}

.experience-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1rem;
}

.experience-details p {
  margin-bottom: var(--spacing-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-info);
}

.experience-list {
  margin: 0;
  padding-left: 20px;
  list-style-type: none;
}

.experience-list li {
  margin-bottom: 6px;
  position: relative;
  padding-left: 16px;
  line-height: 1.4;
}

.experience-list li::before {
  content: "•";
  color: var(--color-info);
  font-weight: var(--font-weight-bold);
  position: absolute;
  left: 0;
}

.experience-list li strong {
  color: var(--color-text-primary);
}

/* Responsive design */
@media (max-width: 960px) {
  .welcome-header {
    padding: var(--spacing-lg) var(--spacing-md);
    margin-bottom: var(--spacing-xxl) !important;
  }

  .bitcoin-logo-hero {
    /* Size is now controlled by the BitcoinLogo component size prop */
  }

  .welcome-title {
    font-size: var(--font-size-h3) !important;
  }

  .welcome-subtitle {
    font-size: var(--font-size-body);
  }

  .experience-toggle {
    flex-direction: column;
    width: 100%;
    max-width: 300px;
    margin: 0 auto;
  }

  .experience-btn {
    width: 100%;
    margin-bottom: var(--spacing-sm);
    border-radius: var(--radius-md) !important;
  }

  .continue-btn {
    width: 100%;
    max-width: 300px;
  }
}

@media (max-width: 600px) {
  .welcome-header {
    padding: var(--spacing-lg) var(--spacing-sm);
  }

  .bitcoin-logo-hero {
    /* Size is now controlled by the BitcoinLogo component size prop */
  }

  .welcome-title {
    font-size: var(--font-size-h4) !important;
    margin-bottom: var(--spacing-md) !important;
  }

  .welcome-subtitle {
    font-size: var(--font-size-small);
    margin-bottom: var(--spacing-lg) !important;
  }

  .experience-btn {
    min-width: unset;
    height: var(--button-height-large);
    font-size: var(--font-size-small);
  }

  .continue-btn {
    height: var(--button-height-large);
    font-size: var(--font-size-body);
  }

  .name-input {
    max-width: 100%;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .bitcoin-logo-hero,
  .experience-btn,
  .continue-btn,
  .name-input :deep(.v-field),
  :deep(.v-alert) {
    animation: none;
    transition: none;
  }

  .bitcoin-logo-hero:hover,
  .experience-btn:hover,
  .continue-btn:hover,
  .name-input :deep(.v-field:hover),
  :deep(.v-alert:hover) {
    transform: none;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .welcome-header {
    border: 2px solid var(--color-border);
  }

  .experience-btn {
    border: 2px solid var(--color-border);
  }

  .continue-btn {
    border: 2px solid var(--color-primary);
  }

  .name-input :deep(.v-field) {
    border: 2px solid var(--color-border);
  }
}
</style>
