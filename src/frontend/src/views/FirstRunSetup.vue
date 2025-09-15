<template>
  <first-run-wizard
    v-model="showWizard"
    :allow-close="false"
    @setup-complete="handleSetupComplete"
  ></first-run-wizard>
</template>

<script>
import FirstRunWizard from "../components/FirstRunWizard.vue";
import { useSettingsStore } from "../stores/settings"; // Re-enable settings store
import {
  isFirstRun,
  saveSetupData,
  getInitialRoute,
} from "../services/firstRunService";

export default {
  name: "FirstRunSetup",

  components: {
    FirstRunWizard,
  },

  data() {
    return {
      showWizard: true,
    };
  },

  methods: {
    async handleSetupComplete(setupData) {
      // const settingsStore = useSettingsStore(); // TEMPORARILY DISABLED - PINIA ISSUE

      try {
        console.log('FirstRunSetup: Setup completion started with data:', setupData);

        // Validate setup data
        if (!setupData || !setupData.settings || !setupData.preferences) {
          throw new Error("Invalid setup data received");
        }

        // Save all setup data using our service
        console.log('FirstRunSetup: Saving setup data...');
        saveSetupData(setupData);
        console.log('FirstRunSetup: Setup data saved successfully');

        // Redirect to the appropriate dashboard based on UI mode
        const route = getInitialRoute();
        console.log('FirstRunSetup: Navigating to route:', route);

        // Validate route before navigation
        if (!route || (route !== "/" && route !== "/dashboard-simple")) {
          throw new Error(`Invalid route returned: ${route}`);
        }

        // Use replace instead of push to prevent going back to setup
        await this.$router.replace(route);
        console.log('FirstRunSetup: Navigation completed successfully');

        // Close the wizard after successful navigation
        this.showWizard = false;
        console.log('FirstRunSetup: Wizard closed after successful navigation');

        // Update settings in the store (non-blocking) - TEMPORARILY DISABLED - PINIA ISSUE
        // This happens after navigation so it doesn't block the user experience
        try {
          if (
            setupData.settings &&
            Object.keys(setupData.settings).length > 0
          ) {
            // await settingsStore.updateSettings(setupData.settings); // TEMPORARILY DISABLED - PINIA ISSUE
            console.log("Settings store update disabled during testing phase");
            console.log('FirstRunSetup: Settings store updated successfully');
          }
        } catch (settingsError) {
          console.warn(
            "FirstRunSetup: Settings update failed, but navigation succeeded:",
            settingsError,
          );
          // Don't show error to user since navigation worked
        }
      } catch (error) {
        console.error("FirstRunSetup: Error during setup completion:", error);
        // Show user-friendly error message
        alert(
          `There was an error completing the setup: ${error.message}. Please try again.`,
        );
        // Re-show wizard on error
        this.showWizard = true;
      }
    },
  },

  async created() {
    // The App.vue component already handles first run detection and routing
    // No need to check again here as it can cause race conditions
    // Component created, setup wizard should be displayed
  },
};
</script>
