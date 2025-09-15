<template>
  <div class="wizard-fullscreen">
    <v-card class="wizard-card">
      <div class="wizard-container">
        <!-- Progress Header -->
        <v-card-text class="pb-0 progress-header">
          <v-row>
            <v-col cols="12">
              <!-- Header with Bitcoin logo -->
              <div class="wizard-header mb-4">
                <div class="wizard-header__logo">
                  <BitcoinLogo 
                    size="lg" 
                    variant="glow" 
                    :animated="true"
                    aria-label="Bitcoin Solo Miner Monitor Logo"
                  />
                </div>
                <div class="wizard-header__text">
                  <h2 class="wizard-header__title">
                    Bitcoin Solo Miner Monitor
                  </h2>
                  <p class="wizard-header__subtitle">Setup Wizard</p>
                </div>
              </div>

              <div class="step-progress">
                <div
                  class="step-item"
                  :class="{
                    active: currentStep >= 1,
                    completed: currentStep > 1,
                  }"
                >
                  <v-avatar
                    :color="getStepColor(1)"
                    size="32"
                    class="step-avatar"
                  >
                    <v-icon v-if="currentStep > 1" size="18" color="white"
                      >mdi-check</v-icon
                    >
                    <span v-else class="text-white">1</span>
                  </v-avatar>
                  <span class="step-label">Welcome</span>
                </div>

                <v-icon
                  :color="currentStep >= 2 ? 'primary' : 'grey'"
                  class="step-separator"
                  >mdi-chevron-right</v-icon
                >

                <div
                  class="step-item"
                  :class="{
                    active: currentStep >= 2,
                    completed: currentStep > 2,
                  }"
                >
                  <v-avatar
                    :color="getStepColor(2)"
                    size="32"
                    class="step-avatar"
                  >
                    <v-icon v-if="currentStep > 2" size="18" color="white"
                      >mdi-check</v-icon
                    >
                    <span v-else class="text-white">2</span>
                  </v-avatar>
                  <span class="step-label">Discovery</span>
                </div>

                <v-icon
                  :color="currentStep >= 3 ? 'primary' : 'grey'"
                  class="step-separator"
                  >mdi-chevron-right</v-icon
                >

                <div
                  class="step-item"
                  :class="{
                    active: currentStep >= 3,
                    completed: currentStep > 3,
                  }"
                >
                  <v-avatar
                    :color="getStepColor(3)"
                    size="32"
                    class="step-avatar"
                  >
                    <v-icon v-if="currentStep > 3" size="18" color="white"
                      >mdi-check</v-icon
                    >
                    <span v-else class="text-white">3</span>
                  </v-avatar>
                  <span class="step-label">Settings</span>
                </div>

                <v-icon
                  :color="currentStep >= 4 ? 'primary' : 'grey'"
                  class="step-separator"
                  >mdi-chevron-right</v-icon
                >

                <div
                  class="step-item"
                  :class="{
                    active: currentStep >= 4,
                    completed: currentStep > 4,
                  }"
                >
                  <v-avatar
                    :color="getStepColor(4)"
                    size="32"
                    class="step-avatar"
                  >
                    <v-icon v-if="currentStep > 4" size="18" color="white"
                      >mdi-check</v-icon
                    >
                    <span v-else class="text-white">4</span>
                  </v-avatar>
                  <span class="step-label">Preferences</span>
                </div>

                <v-icon
                  :color="currentStep >= 5 ? 'primary' : 'grey'"
                  class="step-separator"
                  >mdi-chevron-right</v-icon
                >

                <div
                  class="step-item"
                  :class="{
                    active: currentStep >= 5,
                    completed: currentStep > 5,
                  }"
                >
                  <v-avatar
                    :color="getStepColor(5)"
                    size="32"
                    class="step-avatar"
                  >
                    <v-icon v-if="currentStep > 5" size="18" color="white"
                      >mdi-check</v-icon
                    >
                    <span v-else class="text-white">5</span>
                  </v-avatar>
                  <span class="step-label">Complete</span>
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <v-divider></v-divider>

        <!-- Step Content -->
        <div class="step-content">
          <welcome-screen
            v-if="currentStep === 1"
            @set-experience="setExperienceLevel"
            @next="nextStep"
          ></welcome-screen>

          <network-discovery-screen
            v-if="currentStep === 2"
            ref="discoveryScreen"
            :experience-level="experienceLevel"
            @next="nextStep"
            @back="goBack"
            @miners-found="updateFoundMiners"
          ></network-discovery-screen>

          <settings-config-screen
            v-if="currentStep === 3"
            ref="settingsScreen"
            :experience-level="experienceLevel"
            @next="nextStep"
            @back="goBack"
            @settings-updated="updateSettings"
          ></settings-config-screen>

          <user-preferences-screen
            v-if="currentStep === 4"
            ref="preferencesScreen"
            :experience-level="experienceLevel"
            @next="nextStep"
            @back="goBack"
            @preferences-updated="updatePreferences"
          ></user-preferences-screen>

          <completion-screen
            v-if="currentStep === 5"
            :experience-level="experienceLevel"
            :found-miners="foundMiners"
            :settings="settings"
            :preferences="preferences"
            @finish="completeSetup"
            @back="goBack"
          ></completion-screen>
        </div>

        <!-- Centralized Navigation -->
        <div class="wizard-navigation">
          <v-divider class="mb-4"></v-divider>
          <div class="d-flex justify-space-between align-center">
            <v-btn
              v-if="currentStep > 1"
              variant="text"
              @click="goBack"
              class="nav-btn nav-btn--back"
            >
              <v-icon start>mdi-arrow-left</v-icon>
              Back
            </v-btn>
            <div v-else></div>

            <div class="d-flex gap-2">
              <v-btn
                v-if="showSkipButton"
                variant="text"
                @click="handleSkip"
                class="nav-btn nav-btn--skip"
              >
                Skip for now
              </v-btn>
              <v-btn
                :color="currentStep === 5 ? 'success' : 'primary'"
                @click="handleContinue"
                :disabled="!canContinue"
                class="nav-btn nav-btn--continue"
                :class="{ 'nav-btn--launch': currentStep === 5 }"
                variant="elevated"
              >
                {{ continueButtonText }}
                <v-icon end>{{ continueButtonIcon }}</v-icon>
              </v-btn>
            </div>
          </div>
        </div>
      </div>

      <!-- Progress indicator and navigation -->
      <div class="wizard-footer">
        <v-progress-linear
          :value="progressPercentage"
          height="8"
          color="#ff9800"
          bg-color="rgba(255, 152, 0, 0.2)"
          class="mb-0 progress-bar-custom"
          :style="{ 
            '--v-theme-primary': '#ff9800',
            'background-color': 'rgba(255, 152, 0, 0.2) !important'
          }"
          :aria-label="`Setup progress: ${progressPercentage}% complete`"
          role="progressbar"
          :aria-valuenow="progressPercentage"
          aria-valuemin="0"
          aria-valuemax="100"
        ></v-progress-linear>
        <div class="progress-text">
          Step {{ currentStep }} of 5 ({{ Math.round(progressPercentage) }}%
          complete)
        </div>
      </div>
    </v-card>
  </div>
</template>

<script>
import BitcoinLogo from "./BitcoinLogo.vue";
import WelcomeScreen from "./wizard/WelcomeScreen.vue";
import NetworkDiscoveryScreen from "./wizard/NetworkDiscoveryScreen.vue";
import SettingsConfigScreen from "./wizard/SettingsConfigScreen.vue";
import UserPreferencesScreen from "./wizard/UserPreferencesScreen.vue";
import CompletionScreen from "./wizard/CompletionScreen.vue";
export default {
  name: "FirstRunWizard",

  components: {
    BitcoinLogo,
    WelcomeScreen,
    NetworkDiscoveryScreen,
    SettingsConfigScreen,
    UserPreferencesScreen,
    CompletionScreen,
  },

  props: {
    value: {
      type: Boolean,
      default: false,
    },

    allowClose: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      currentStep: this.loadWizardProgress(),
      experienceLevel: this.loadExperienceLevel(),
      foundMiners: this.loadFoundMiners(),
      settings: this.loadSettings(),
      preferences: this.loadPreferences(),
      skipDiscovery: false,
    };
  },

  computed: {
    show: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit("input", value);
      },
    },

    progressPercentage() {
      const percentage = (this.currentStep / 5) * 100;
      console.log(`Progress: Step ${this.currentStep}/5 = ${percentage}%`);
      return percentage;
    },

    showSkipButton() {
      // Show skip button on discovery step if no miners found
      return this.currentStep === 2 && this.foundMiners.length === 0;
    },

    canContinue() {
      switch (this.currentStep) {
        case 1:
          return !!this.experienceLevel;
        case 2:
          return this.foundMiners.length > 0 || this.skipDiscovery;
        case 3:
          return true; // Always allow progression from settings step
        case 4:
          return true; // Always allow progression from preferences step
        case 5:
          return true;
        default:
          return false;
      }
    },

    continueButtonText() {
      switch (this.currentStep) {
        case 5:
          return 'Launch Dashboard';
        default:
          return 'Continue';
      }
    },

    continueButtonIcon() {
      switch (this.currentStep) {
        case 5:
          return 'mdi-rocket-launch';
        default:
          return 'mdi-arrow-right';
      }
    },
  },

  watch: {
    currentStep: {
      immediate: true,
      handler(_newStep) {
        // Ensure progress bar updates immediately when step changes
        this.$nextTick(() => {
          const progressBar = this.$el?.querySelector(".v-progress-linear");
          if (progressBar) {
            // Force a repaint to ensure visual update
            progressBar.style.transform = "translateZ(0)";
          }
          
          // Fix progress bar width issue by directly setting the determinate width
          const determinate = this.$el?.querySelector(".progress-bar-custom .v-progress-linear__determinate");
          if (determinate) {
            const percentage = this.progressPercentage;
            determinate.style.width = `${percentage}%`;
            determinate.style.backgroundColor = '#ff9800';
            determinate.style.display = 'block';
          }
        });
      },
    },
    
    progressPercentage: {
      immediate: true,
      handler(newPercentage) {
        // Also watch for changes to progressPercentage directly
        this.$nextTick(() => {
          const determinate = this.$el?.querySelector(".progress-bar-custom .v-progress-linear__determinate");
          if (determinate) {
            determinate.style.width = `${newPercentage}%`;
            determinate.style.backgroundColor = '#ff9800';
            determinate.style.display = 'block';
          }
        });
      },
    },
  },

  methods: {
    loadWizardProgress() {
      const saved = localStorage.getItem("wizard-progress");
      return saved ? parseInt(saved) : 1;
    },

    loadExperienceLevel() {
      return localStorage.getItem("wizard-experience-level") || "beginner";
    },

    loadFoundMiners() {
      const saved = localStorage.getItem("wizard-found-miners");
      return saved ? JSON.parse(saved) : [];
    },

    loadSettings() {
      const saved = localStorage.getItem("wizard-settings");
      return saved ? JSON.parse(saved) : {};
    },

    loadPreferences() {
      const saved = localStorage.getItem("wizard-preferences");
      return saved ? JSON.parse(saved) : {};
    },

    saveWizardProgress() {
      try {
        // Save simple values first
        localStorage.setItem("wizard-progress", this.currentStep.toString());
        localStorage.setItem("wizard-experience-level", this.experienceLevel);

        // Simple JSON serialization without complex circular reference detection
        // This should be safe for wizard data which is simple objects
        try {
          localStorage.setItem(
            "wizard-found-miners",
            JSON.stringify(this.foundMiners || []),
          );
        } catch (error) {
          console.warn("Failed to save found miners:", error);
          localStorage.setItem("wizard-found-miners", "[]");
        }

        try {
          localStorage.setItem(
            "wizard-settings",
            JSON.stringify(this.settings || {}),
          );
        } catch (error) {
          console.warn("Failed to save settings:", error);
          localStorage.setItem("wizard-settings", "{}");
        }

        try {
          localStorage.setItem(
            "wizard-preferences",
            JSON.stringify(this.preferences || {}),
          );
        } catch (error) {
          console.warn("Failed to save preferences:", error);
          localStorage.setItem("wizard-preferences", "{}");
        }
      } catch (error) {
        console.warn(
          "FirstRunWizard: Failed to save progress to localStorage:",
          error,
        );
        // Don't throw - continue execution even if localStorage fails
      }
    },

    clearWizardProgress() {
      localStorage.removeItem("wizard-progress");
      localStorage.removeItem("wizard-experience-level");
      localStorage.removeItem("wizard-found-miners");
      localStorage.removeItem("wizard-settings");
      localStorage.removeItem("wizard-preferences");
    },

    nextStep() {
      if (this.currentStep < 5) {
        this.currentStep++;
        this.saveWizardProgress();
        // Force immediate progress bar update
        this.$nextTick(() => {
          this.$forceUpdate();
        });
      }
    },

    goBack() {
      if (this.currentStep > 1) {
        this.currentStep--;
        this.saveWizardProgress();
        // Force immediate progress bar update
        this.$nextTick(() => {
          this.$forceUpdate();
        });
      }
    },

    getStepColor(stepNumber) {
      if (this.currentStep > stepNumber) {
        return "success"; // Completed steps
      } else if (this.currentStep === stepNumber) {
        return "primary"; // Current step
      } else {
        return "surface-variant"; // Future steps
      }
    },

    setExperienceLevel(level) {
      this.experienceLevel = level;
      this.saveWizardProgress();
    },

    updateFoundMiners(miners) {
      this.foundMiners = miners;
      this.saveWizardProgress();
    },

    updateSettings(settings) {
      console.log("FirstRunWizard: Updating settings:", settings);

      // Log the type and structure of settings to identify potential issues
      if (settings && typeof settings === "object") {
        console.log("Settings keys:", Object.keys(settings));
        console.log("Settings structure check:");

        for (const [key, value] of Object.entries(settings)) {
          console.log(
            `  ${key}:`,
            typeof value,
            Array.isArray(value) ? `Array(${value.length})` : "",
          );

          // Check for potential circular references
          if (value && typeof value === "object" && !Array.isArray(value)) {
            try {
              JSON.stringify(value);
              console.log(`    ${key} - JSON serializable ✓`);
            } catch (error) {
              console.warn(
                `    ${key} - JSON serialization failed:`,
                error.message,
              );
            }
          }
        }
      }

      this.settings = settings;
      this.saveWizardProgress();
    },

    updatePreferences(preferences) {
      console.log("FirstRunWizard: Updating preferences:", preferences);

      // Log the type and structure of preferences to identify potential issues
      if (preferences && typeof preferences === "object") {
        console.log("Preferences keys:", Object.keys(preferences));
        console.log("Preferences structure check:");

        for (const [key, value] of Object.entries(preferences)) {
          console.log(
            `  ${key}:`,
            typeof value,
            Array.isArray(value) ? `Array(${value.length})` : "",
          );

          // Check for potential circular references
          if (value && typeof value === "object" && !Array.isArray(value)) {
            try {
              JSON.stringify(value);
              console.log(`    ${key} - JSON serializable ✓`);
            } catch (error) {
              console.warn(
                `    ${key} - JSON serialization failed:`,
                error.message,
              );
            }
          }
        }
      }

      this.preferences = preferences;
      this.saveWizardProgress();
    },

    completeSetup() {
      console.log("FirstRunWizard: completeSetup called");
      
      // Enhanced debugging for validation
      console.log("FirstRunWizard: Validation check - experienceLevel:", this.experienceLevel);
      console.log("FirstRunWizard: Validation check - settings:", this.settings);
      console.log("FirstRunWizard: Validation check - preferences:", this.preferences);
      console.log("FirstRunWizard: Settings keys:", this.settings ? Object.keys(this.settings) : 'null/undefined');
      console.log("FirstRunWizard: Preferences keys:", this.preferences ? Object.keys(this.preferences) : 'null/undefined');

      // Validate that we have all required data
      if (!this.experienceLevel) {
        console.error("FirstRunWizard: Missing experience level");
        alert("Please complete all setup steps before continuing.");
        return;
      }

      if (!this.settings || Object.keys(this.settings).length === 0) {
        console.error("FirstRunWizard: Missing settings data");
        console.log("FirstRunWizard: Settings validation failed - settings:", this.settings);
        alert("Please complete the settings configuration step.");
        return;
      }

      if (!this.preferences || Object.keys(this.preferences).length === 0) {
        console.error("FirstRunWizard: Missing preferences data");
        console.log("FirstRunWizard: Preferences validation failed - preferences:", this.preferences);
        alert("Please complete your preferences in step 4.");
        return;
      }

      const setupData = {
        experienceLevel: this.experienceLevel,
        foundMiners: this.foundMiners || [],
        settings: this.settings,
        preferences: this.preferences,
      };

      // Emitting setup-complete with data

      // Save all settings and preferences
      this.$emit("setup-complete", setupData);

      // Clear wizard progress since setup is complete
      this.clearWizardProgress();

      // Note: Don't close the wizard here - let the parent handle navigation first
      // The parent will handle closing after successful navigation
      // Setup completion process initiated
    },

    attemptClose() {
      if (this.allowClose) {
        this.$emit("close-requested");
      }
    },

    handleSkip() {
      if (this.currentStep === 2) {
        this.skipDiscovery = true;
        this.nextStep();
      }
    },

    handleContinue() {
      switch (this.currentStep) {
        case 2:
          // Emit miners found from discovery screen
          this.$refs.discoveryScreen?.emitMinersFound();
          this.nextStep();
          break;
        case 3:
          // For settings screen, always emit settings and proceed
          // The settings screen has default values, so validation should always pass
          this.$refs.settingsScreen?.emitSettings();
          this.nextStep();
          break;
        case 4:
          // For preferences screen, emit preferences and proceed
          this.$refs.preferencesScreen?.proceed();
          // Note: nextStep() will be called by the preferences screen's proceed method
          break;
        case 5:
          this.completeSetup();
          break;
        default:
          this.nextStep();
          break;
      }
    },
  },
};
</script>

<style scoped>
/* Fullscreen wizard styling */
.wizard-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: var(--z-modal);
  background: var(--color-background);
}

/* Comprehensive dropdown overlay fixes for Vuetify 3.x */
:deep(.v-overlay) {
  z-index: 10001 !important;
  position: fixed !important;
}

:deep(.v-overlay__content) {
  z-index: 10001 !important;
  position: fixed !important;
}

:deep(.v-overlay__scrim) {
  z-index: 10000 !important;
  position: fixed !important;
}

:deep(.v-menu) {
  z-index: 10001 !important;
}

:deep(.v-menu > .v-overlay__content) {
  z-index: 10001 !important;
  position: fixed !important;
}

:deep(.v-select__content) {
  z-index: 10001 !important;
}

:deep(.v-list) {
  z-index: 10002 !important;
  background: var(--color-surface) !important;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
  max-height: 300px !important;
  overflow-y: auto !important;
}

:deep(.v-list-item) {
  color: var(--color-text-primary) !important;
  transition: all 0.2s ease;
  padding: 12px 16px !important;
  min-height: 48px !important;
}

:deep(.v-list-item:hover) {
  background: var(--color-primary-alpha-10) !important;
  color: var(--color-primary) !important;
}

:deep(.v-list-item--active) {
  background: var(--color-primary-alpha-20) !important;
  color: var(--color-primary) !important;
}

:deep(.v-list-item-title) {
  color: inherit !important;
  font-weight: 400;
}

.wizard-card {
  width: 100%;
  height: 100%;
  border-radius: 0 !important;
  box-shadow: none !important;
}

/* Wizard container styling */
.wizard-container {
  height: calc(100vh - 120px); /* Full height minus footer and navigation */
  display: flex;
  flex-direction: column;
  min-height: 500px;
  background: linear-gradient(
    135deg,
    var(--color-background) 0%,
    var(--color-surface) 100%
  );
}

/* Remove header styling since we removed the app bar */

/* Progress header styling */
.progress-header {
  flex-shrink: 0;
  padding: var(--spacing-md) var(--spacing-lg);
  max-height: 200px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-subtle);
}

/* Wizard header styling */
.wizard-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.wizard-header__logo {
  flex-shrink: 0;
}

.wizard-header__text {
  text-align: center;
}

.wizard-header__title {
  color: var(--color-text-primary);
  font-size: var(--font-size-h2);
  font-weight: var(--font-weight-semibold);
  margin: 0;
  line-height: var(--line-height-tight);
}

.wizard-header__subtitle {
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  margin: var(--spacing-xs) 0 0 0;
  opacity: 0.8;
}

/* Step content styling - Fixed for proper scrolling */
.step-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  background: var(--color-background);
  position: relative;
  z-index: 1;
  /* Remove padding from here - let individual screens handle their own padding */
  /* Enable smooth scrolling and touch scrolling for mobile */
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
  /* Set maximum height to ensure proper scrolling calculation */
  max-height: calc(
    100vh - 360px
  ); /* Account for header (~200px), footer (~80px), and navigation (~80px) */

  /* Add scroll styling for better UX */
  scrollbar-width: thin;
  scrollbar-color: rgba(var(--v-theme-primary), 0.3) transparent;
}

/* Custom scrollbar styling for webkit browsers */
.step-content::-webkit-scrollbar {
  width: 8px;
}

.step-content::-webkit-scrollbar-track {
  background: transparent;
}

.step-content::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-primary), 0.3);
  border-radius: 4px;
  transition: background 0.3s ease;
}

.step-content::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-primary), 0.5);
}

/* Step progress styling */
.step-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  padding: var(--spacing-md) 0;
}

.step-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: all var(--transition-normal);
  padding: var(--spacing-sm) var(--spacing-sm);
  border-radius: var(--radius-md);
  position: relative;
}

.step-item.active {
  background: var(--color-primary-alpha-10);
  transform: scale(1.05);
}

.step-item.completed {
  background: rgba(var(--color-success), 0.1);
}

.step-item.active .step-label {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.step-item.completed .step-label {
  color: var(--color-success);
  font-weight: var(--font-weight-medium);
}

.step-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
  white-space: nowrap;
  transition: all var(--transition-normal);
}

.step-avatar {
  font-weight: var(--font-weight-bold);
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-1);
}

.step-item.active .step-avatar {
  box-shadow: 0 4px 12px var(--color-primary-alpha-30);
  transform: scale(1.1);
}

.step-item.completed .step-avatar {
  box-shadow: 0 4px 12px rgba(var(--color-success), 0.4);
}

.step-separator {
  margin: 0 var(--spacing-sm);
  transition: all var(--transition-normal);
}

/* Footer styling */
.wizard-footer {
  background: var(--color-surface);
  border-top: 1px solid var(--color-border-subtle);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.2);
  padding: 0;
  height: 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* Centralized Navigation styling */
.wizard-navigation {
  flex-shrink: 0;
  padding: 16px 24px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border-subtle);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  margin-top: auto;
}

.nav-btn {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
  min-width: 120px;
  height: 44px;
}

.nav-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.nav-btn--continue {
  min-width: 140px;
  font-weight: 600;
}

.nav-btn--continue:hover {
  box-shadow: 0 4px 12px var(--color-primary-alpha-30);
}

.nav-btn--launch {
  min-width: 180px;
  font-size: 1.1rem;
  box-shadow: 0 4px 12px rgba(var(--v-theme-success), 0.3);
}

.nav-btn--launch:hover {
  box-shadow: 0 6px 16px rgba(var(--v-theme-success), 0.4);
  transform: translateY(-3px);
}

.nav-btn--back {
  color: var(--color-text-secondary);
}

.nav-btn--back:hover {
  color: var(--color-text-primary);
  background: var(--color-surface-elevated);
}

.nav-btn--skip {
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
}

.nav-btn--skip:hover {
  color: var(--color-text-primary);
  background: var(--color-surface-elevated);
}

.progress-text {
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--color-text-secondary);
  padding: var(--spacing-sm) 0 var(--spacing-xs) 0;
  line-height: 1;
}

/* Remove Bitcoin logo styling since we removed the header */

/* Utility classes */
.w-100 {
  width: 100%;
}

/* Enhanced transitions for smooth interactions */
.v-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.v-progress-linear {
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.v-progress-linear :deep(.v-progress-linear__determinate) {
  transition: width 0.3s ease !important;
}

/* Progress bar custom styling with orange color fill */
.progress-bar-custom {
  background-color: rgba(255, 152, 0, 0.2) !important;
  transition: all 0.3s ease !important;
  border-radius: 4px !important;
  overflow: hidden !important;
}

/* Target the progress bar elements directly without :deep() for better compatibility */
.wizard-footer .progress-bar-custom {
  background-color: rgba(255, 152, 0, 0.2) !important;
}

/* Use global CSS to target Vuetify's internal elements */
.progress-bar-custom .v-progress-linear__background {
  background-color: rgba(255, 152, 0, 0.2) !important;
  opacity: 1 !important;
}

.progress-bar-custom .v-progress-linear__determinate {
  background-color: #ff9800 !important;
  background: #ff9800 !important;
  transition: width 0.3s ease !important;
}

.progress-bar-custom .v-progress-linear__buffer {
  background-color: rgba(255, 152, 0, 0.1) !important;
}

/* Animation for progress bar stripes */
@keyframes progress-stripes {
  0% {
    background-position: 0 0;
  }
  100% {
    background-position: 20px 0;
  }
}

/* Responsive design */
@media (max-width: 960px) {
  .wizard-container {
    height: calc(100vh - 120px); /* Footer and navigation on mobile */
  }

  .wizard-navigation {
    padding: 12px 16px;
  }

  .nav-btn {
    min-width: 100px;
    height: 40px;
    font-size: var(--font-size-small);
  }

  .nav-btn--continue {
    min-width: 120px;
  }

  .wizard-header {
    flex-direction: column;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) 0;
  }

  .wizard-header__title {
    font-size: var(--font-size-h3);
  }

  .wizard-header__subtitle {
    font-size: var(--font-size-small);
  }

  .step-progress {
    flex-direction: column;
    gap: var(--spacing-md);
    padding: var(--spacing-md) 0;
  }

  .step-separator {
    transform: rotate(90deg);
    margin: var(--spacing-xs) 0;
  }

  .step-content {
    /* Adjust max-height for mobile with larger header */
    max-height: calc(
      100vh - 380px
    ); /* Account for larger mobile header (~260px), footer (~60px), and navigation (~60px) */
  }

  .progress-header {
    padding: var(--spacing-md);
    max-height: 220px;
  }

  .step-item {
    padding: var(--spacing-sm) var(--spacing-md);
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 600px) {
  .wizard-header__title {
    font-size: var(--font-size-h4);
  }

  .wizard-header__subtitle {
    font-size: var(--font-size-caption);
  }

  .step-label {
    font-size: var(--font-size-caption);
  }

  .step-avatar {
    width: 28px !important;
    height: 28px !important;
  }

  .step-item {
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-sm);
  }

  .step-content {
    /* Further adjust max-height for small mobile screens */
    max-height: calc(
      100vh - 360px
    ); /* Account for compact mobile header (~240px), footer (~60px), and navigation (~60px) */
  }

  .progress-header {
    padding: var(--spacing-sm);
    max-height: 200px;
  }

  .progress-text {
    font-size: var(--font-size-overline);
    padding: var(--spacing-xs) 0 var(--spacing-xs) 0;
  }

  .wizard-navigation {
    padding: 8px 12px;
  }

  .wizard-navigation .d-flex {
    flex-direction: column;
    gap: 12px;
  }

  .nav-btn {
    width: 100%;
    min-width: unset;
  }
}

/* Ensure proper layout structure */
.wizard-card {
  display: flex;
  flex-direction: column;
  background: var(--color-background);
}

.wizard-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.wizard-footer {
  flex-shrink: 0;
}

/* Animation for step transitions */
@keyframes stepPulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
  }
}

.step-item.active .step-avatar {
  animation: stepPulse 2s ease-in-out infinite;
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .step-item,
  .step-avatar,
  .step-separator,
  .v-card,
  .v-progress-linear {
    transition: none;
    animation: none;
  }

  .step-item.active .step-avatar {
    animation: none;
  }

  .progress-bar-custom :deep(.v-progress-linear__determinate) {
    animation: none !important;
    background-image: none !important;
  }

  @keyframes progress-stripes {
    0%,
    100% {
      background-position: 0 0;
    }
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .progress-header,
  .wizard-footer {
    border-width: 2px;
  }

  .step-item.active {
    border: 2px solid rgb(var(--v-theme-primary));
  }

  .step-item.completed {
    border: 2px solid rgb(var(--v-theme-success));
  }
}
</style>

<style>
/* Global styles for progress bar - not scoped to work with Vuetify's internal elements */
.progress-bar-custom .v-progress-linear__background {
  background-color: rgba(255, 152, 0, 0.2) !important;
  opacity: 1 !important;
}

.progress-bar-custom .v-progress-linear__determinate {
  background-color: #ff9800 !important;
  background: #ff9800 !important;
  transition: width 0.3s ease !important;
}

.progress-bar-custom .v-progress-linear__buffer {
  background-color: rgba(255, 152, 0, 0.1) !important;
}

/* Hide individual screen footers to prevent button overlap */
.settings-footer,
.discovery-footer,
.welcome-footer,
.preferences-footer,
.completion-footer {
  display: none !important;
}

/* Fix button positioning issues by hiding problematic buttons */
.settings-btn,
.discovery-btn,
.preferences-btn,
.completion-btn,
.launch-btn {
  display: none !important;
}

/* Hide any navigation buttons that might still exist in individual screens */
.step-content .v-btn[variant="text"]:first-child,
.step-content .v-btn[color="primary"]:last-child,
.step-content .v-btn[color="success"] {
  display: none !important;
}
</style>
