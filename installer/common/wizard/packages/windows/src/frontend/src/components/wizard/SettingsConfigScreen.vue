<template>
  <div class="settings-screen">
    <div class="settings-content">
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h1 class="text-h4 mb-4">Settings Configuration</h1>
            <p class="text-subtitle-1 mb-6">
              Configure your application settings based on your preferences.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12">
            <v-form ref="settingsForm">
              <!-- UI Settings -->
              <v-card variant="outlined" class="mb-6">
                <v-card-title>
                  <v-icon start color="primary">mdi-monitor-dashboard</v-icon>
                  User Interface
                </v-card-title>
                <v-card-text>
                  <v-row>


                    <v-col cols="12" md="6">
                      <v-select
                        v-model="settings.default_view"
                        :items="defaultViewOptions"
                        label="Default View"
                        variant="outlined"
                        hint="The screen to show when you start the application"
                        persistent-hint
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      ></v-select>
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col cols="12" md="6">
                      <v-switch
                        v-model="settings.simple_mode"
                        label="Simple Mode"
                        hint="Enable simplified user interface for easier navigation"
                        persistent-hint
                      ></v-switch>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-select
                        v-model="settings.refresh_interval"
                        :items="refreshIntervalOptions"
                        label="Dashboard Refresh Interval"
                        variant="outlined"
                        hint="How often the dashboard should refresh"
                        persistent-hint
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      ></v-select>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>

              <!-- Miner Settings -->
              <v-card variant="outlined" class="mb-6">
                <v-card-title>
                  <v-icon start color="primary">mdi-pickaxe</v-icon>
                  Miner Monitoring
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-select
                        v-model="settings.polling_interval"
                        :items="pollingIntervalOptions"
                        label="Miner Polling Interval"
                        variant="outlined"
                        hint="How often to check miners for updates"
                        persistent-hint
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      ></v-select>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-select
                        v-model="settings.temperature_unit"
                        :items="temperatureUnitOptions"
                        label="Temperature Unit"
                        variant="outlined"
                        hint="Unit for displaying temperature values"
                        persistent-hint
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      ></v-select>
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col cols="12" md="6">
                      <v-select
                        v-model="settings.chart_retention_days"
                        :items="retentionOptions"
                        label="Data Retention Period"
                        variant="outlined"
                        hint="How long to keep historical data"
                        persistent-hint
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      ></v-select>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>

              <!-- Alert Settings -->
              <v-card variant="outlined">
                <v-card-title>
                  <v-icon start color="primary">mdi-bell-ring</v-icon>
                  Alert Configuration
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-switch
                        v-model="alertSettings.enabled"
                        label="Enable Alerts"
                        hint="Turn on/off all alerts"
                        persistent-hint
                      ></v-switch>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-select
                        v-model="alertSettings.notification_method"
                        :items="notificationMethodOptions"
                        label="Notification Method"
                        variant="outlined"
                        hint="How to receive alert notifications"
                        persistent-hint
                        :disabled="!alertSettings.enabled"
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      ></v-select>
                    </v-col>
                  </v-row>

                  <v-row v-if="alertSettings.enabled">
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model.number="alertSettings.temperature_threshold"
                        label="Temperature Threshold (°C)"
                        hint="Alert when temperature exceeds this value"
                        persistent-hint
                        type="number"
                        variant="outlined"
                      ></v-text-field>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model.number="alertSettings.hashrate_drop_percent"
                        label="Hashrate Drop Threshold (%)"
                        hint="Alert when hashrate drops by this percentage"
                        persistent-hint
                        type="number"
                        variant="outlined"
                      ></v-text-field>
                    </v-col>
                  </v-row>

                  <v-row v-if="alertSettings.enabled">
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model.number="alertSettings.offline_duration"
                        label="Offline Duration (minutes)"
                        hint="Alert when miner is offline for this duration"
                        persistent-hint
                        type="number"
                        variant="outlined"
                      ></v-text-field>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model.number="alertSettings.rejected_shares_percent"
                        label="Rejected Shares Threshold (%)"
                        hint="Alert when rejected shares exceed this percentage"
                        persistent-hint
                        type="number"
                        variant="outlined"
                      ></v-text-field>
                    </v-col>
                  </v-row>

                  <!-- Email notification settings -->
                  <v-row
                    v-if="
                      alertSettings.enabled &&
                      alertSettings.notification_method === 'email'
                    "
                  >
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="alertSettings.email_address"
                        label="Email Address"
                        hint="Email address to receive notifications"
                        persistent-hint
                        variant="outlined"
                      ></v-text-field>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-select
                        v-model="alertSettings.email_frequency"
                        :items="emailFrequencyOptions"
                        label="Email Frequency"
                        hint="How often to send email notifications"
                        persistent-hint
                        variant="outlined"
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      ></v-select>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-form>
          </v-col>
        </v-row>

        <v-row v-if="experienceLevel === 'beginner'" class="mt-6">
          <v-col cols="12">
            <v-alert type="info" variant="outlined">
              <h3 class="text-h6">Settings Recommendation</h3>
              <p class="mb-0">
                We've pre-configured these settings based on your experience
                level. You can always change them later in the Settings page.
              </p>
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </div>


  </div>
</template>

<script>
export default {
  name: "SettingsConfigScreen",

  props: {
    experienceLevel: {
      type: String,
      default: "beginner",
    },
  },

  data() {
    return {
      settings: {
        refresh_interval: 10,
        chart_retention_days: 30,
        temperature_unit: "celsius",
        default_view: "dashboard",
        polling_interval: 30,
        simple_mode: true,
      },

      alertSettings: {
        enabled: true,
        notification_method: "browser",
        temperature_threshold: 80,
        hashrate_drop_percent: 20,
        offline_duration: 5,
        rejected_shares_percent: 5,
        email_address: "",
        email_frequency: "immediate",
      },

      // Options - Fixed structure for proper dropdown functionality

      refreshIntervalOptions: [
        { title: "5 seconds", value: 5 },
        { title: "10 seconds", value: 10 },
        { title: "30 seconds", value: 30 },
        { title: "1 minute", value: 60 },
        { title: "5 minutes", value: 300 },
      ],

      retentionOptions: [
        { title: "7 days", value: 7 },
        { title: "14 days", value: 14 },
        { title: "30 days", value: 30 },
        { title: "60 days", value: 60 },
        { title: "90 days", value: 90 },
      ],

      temperatureUnitOptions: [
        { title: "Celsius (°C)", value: "celsius" },
        { title: "Fahrenheit (°F)", value: "fahrenheit" },
      ],

      defaultViewOptions: [
        { title: "Dashboard", value: "dashboard" },
        { title: "Simple Dashboard", value: "dashboard-simple" },
        { title: "Miners", value: "miners" },
        { title: "Analytics", value: "analytics" },
      ],

      pollingIntervalOptions: [
        { title: "10 seconds", value: 10 },
        { title: "30 seconds", value: 30 },
        { title: "1 minute", value: 60 },
        { title: "5 minutes", value: 300 },
        { title: "10 minutes", value: 600 },
      ],

      notificationMethodOptions: [
        { title: "Browser Notifications", value: "browser" },
        { title: "Email", value: "email" },
      ],

      emailFrequencyOptions: [
        { title: "Immediate", value: "immediate" },
        { title: "Hourly Digest", value: "hourly" },
        { title: "Daily Digest", value: "daily" },
      ],
    };
  },





  created() {
    // Set default settings based on experience level
    this.applyExperienceLevelDefaults();
  },

  methods: {
    applyExperienceLevelDefaults() {
      // Apply different default settings based on experience level
      switch (this.experienceLevel) {
        case "beginner":
          this.settings.simple_mode = true;
          this.settings.refresh_interval = 10;
          this.settings.polling_interval = 30;
          this.settings.default_view = "dashboard-simple";
          this.alertSettings.temperature_threshold = 70; // Conservative and safe
          break;

        case "intermediate":
          this.settings.simple_mode = false;
          this.settings.refresh_interval = 10;
          this.settings.polling_interval = 30;
          this.settings.default_view = "dashboard";
          this.alertSettings.temperature_threshold = 75; // Balanced and safe
          break;

        case "advanced":
          this.settings.simple_mode = false;
          this.settings.refresh_interval = 5;
          this.settings.polling_interval = 10;
          this.settings.default_view = "dashboard";
          this.alertSettings.temperature_threshold = 80; // Maximum safe threshold
          break;
      }
    },

    emitSettings() {
      // Validate settings before emitting
      const isValid = this.validateSettings();
      
      if (!isValid) {
        console.warn('SettingsConfigScreen: Settings validation failed, but proceeding with defaults');
      }
      
      // Combine settings and alert settings
      const combinedSettings = {
        ...this.settings,
        alerts: this.alertSettings,
      };

      console.log("SettingsConfigScreen: Emitting settings:", combinedSettings);

      // Emit the settings to the parent component
      this.$emit("settings-updated", combinedSettings);
      return true; // Always return true - validation is optional in wizard
    },
    
    validateSettings() {
      // Basic validation - ensure required numeric values are valid
      const requiredNumericFields = [
        'refresh_interval',
        'polling_interval', 
        'chart_retention_days'
      ];
      
      for (const field of requiredNumericFields) {
        const value = this.settings[field];
        if (!value || isNaN(value) || value <= 0) {
          console.warn(`SettingsConfigScreen: Invalid ${field}: ${value}`);
          return false;
        }
      }
      
      // Validate alert settings if enabled
      if (this.alertSettings.enabled) {
        const alertNumericFields = [
          'temperature_threshold',
          'hashrate_drop_percent',
          'offline_duration',
          'rejected_shares_percent'
        ];
        
        for (const field of alertNumericFields) {
          const value = this.alertSettings[field];
          if (!value || isNaN(value) || value <= 0) {
            console.warn(`SettingsConfigScreen: Invalid alert ${field}: ${value}`);
            return false;
          }
        }
        
        // Validate email if email notifications are enabled
        if (this.alertSettings.notification_method === 'email') {
          if (!this.alertSettings.email_address || !this.alertSettings.email_address.includes('@')) {
            console.warn('SettingsConfigScreen: Invalid email address for email notifications');
            return false;
          }
        }
      }
      
      return true;
    },
  },
};
</script>

<style scoped>
/* Import shared wizard styles for standardized info bubbles */
@import "./shared-wizard-styles.css";

/* Settings screen layout - Fixed for proper scrolling */
.settings-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  /* Ensure the screen takes full height of step-content */
  min-height: 100%;
}

.settings-content {
  flex: 1;
  /* Remove overflow-y: auto to prevent nested scrolling - parent .step-content handles scrolling */
  padding: var(--spacing-lg);
  min-height: 0;
  /* Allow content to expand naturally */
  overflow: visible;
}

.settings-footer {
  flex-shrink: 0;
  padding: 16px 24px;
  background: rgb(var(--v-theme-surface));
  /* Add border and shadow to make footer more prominent */
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  /* Ensure footer stays at bottom with static positioning */
  margin-top: auto;
  position: static; /* Ensure static positioning, not fixed */
}

/* Header styling */
.text-center h1 {
  color: rgb(var(--v-theme-on-surface));
  font-weight: 600;
  margin-bottom: 16px;
}

.text-center p {
  color: rgb(var(--v-theme-on-surface-variant));
  margin-bottom: 32px;
}

/* Card styling */
:deep(.v-card) {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 12px;
  transition: all 0.3s ease;
}

:deep(.v-card:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

:deep(.v-card-title) {
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
  padding: 20px 24px 16px 24px;
}

:deep(.v-card-text) {
  padding: 16px 24px 24px 24px;
}

/* Form field styling */
:deep(.v-text-field .v-field) {
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.v-text-field .v-field:hover) {
  background: rgb(var(--v-theme-surface-bright));
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

:deep(.v-text-field .v-field--focused) {
  background: rgb(var(--v-theme-surface-bright));
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.3);
}

/* Select field styling */
:deep(.v-select .v-field) {
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.v-select .v-field:hover) {
  background: rgb(var(--v-theme-surface-bright));
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

:deep(.v-select .v-field--focused) {
  background: rgb(var(--v-theme-surface-bright));
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.3);
}

/* Switch styling - Fixed to show proper enabled/disabled states */
:deep(.v-switch) {
  margin-top: 8px;
}

:deep(.v-switch .v-selection-control__wrapper) {
  height: auto;
}

/* Off state - Grey track with white thumb */
:deep(.v-switch .v-switch__track) {
  background-color: #9e9e9e !important;
  opacity: 1 !important;
  transition: background-color 0.3s ease;
}

:deep(.v-switch .v-switch__thumb) {
  background-color: #ffffff !important;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* On state - Orange track with white thumb (multiple selectors for Vuetify 3.x compatibility) */
:deep(.v-switch input:checked ~ .v-switch__track),
:deep(.v-switch[aria-checked="true"] .v-switch__track),
:deep(.v-switch.v-switch--inset .v-switch__track),
:deep(.v-switch .v-selection-control--dirty .v-switch__track) {
  background-color: #ff9800 !important;
  opacity: 1 !important;
}

:deep(.v-switch input:checked ~ .v-switch__thumb),
:deep(.v-switch[aria-checked="true"] .v-switch__thumb),
:deep(.v-switch.v-switch--inset .v-switch__thumb),
:deep(.v-switch .v-selection-control--dirty .v-switch__thumb) {
  background-color: #ffffff !important;
}

/* Hover effects */
:deep(.v-switch:hover .v-switch__thumb) {
  box-shadow: 0 2px 8px rgba(255, 152, 0, 0.4);
  transform: scale(1.05);
}

:deep(.v-switch input:checked:hover ~ .v-switch__thumb),
:deep(.v-switch[aria-checked="true"]:hover .v-switch__thumb),
:deep(.v-switch.v-switch--inset:hover .v-switch__thumb),
:deep(.v-switch .v-selection-control--dirty:hover .v-switch__thumb) {
  box-shadow: 0 2px 8px rgba(255, 152, 0, 0.6);
}

/* Focus states for accessibility */
:deep(.v-switch:focus-within .v-switch__thumb) {
  box-shadow: 0 0 0 2px rgba(255, 152, 0, 0.3);
}

/* Button styling */
.settings-btn {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
  min-width: 120px;
}

.settings-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/* Responsive design */
@media (max-width: 960px) {
  .settings-content {
    padding: var(--spacing-md);
  }

  .settings-footer {
    padding: 12px 16px;
  }

  :deep(.v-card-title) {
    padding: 16px 20px 12px 20px;
    font-size: 1.1rem;
  }

  :deep(.v-card-text) {
    padding: 12px 20px 20px 20px;
  }
}

@media (max-width: 600px) {
  .settings-content {
    padding: var(--spacing-sm);
  }

  .settings-footer {
    padding: 12px;
  }

  .settings-footer .d-flex {
    flex-direction: column;
    gap: 12px;
  }

  .settings-btn {
    width: 100%;
  }

  :deep(.v-card-title) {
    padding: 12px 16px 8px 16px;
    font-size: 1rem;
  }

  :deep(.v-card-text) {
    padding: 8px 16px 16px 16px;
  }
}

/* Comprehensive dropdown overlay fixes for Vuetify 3.x */
:deep(.v-overlay) {
  z-index: 10001 !important;
  position: fixed !important;
}

:deep(.v-overlay__content) {
  z-index: 10002 !important;
  position: fixed !important;
}

:deep(.v-overlay__scrim) {
  z-index: 10000 !important;
  position: fixed !important;
}

:deep(.v-menu) {
  z-index: 10003 !important;
}

:deep(.v-menu > .v-overlay__content) {
  z-index: 10003 !important;
  position: fixed !important;
}

:deep(.v-select__content) {
  z-index: 10003 !important;
}

:deep(.v-list) {
  z-index: 10004 !important;
  background: rgb(var(--v-theme-surface)) !important;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
  max-height: 300px !important;
  overflow-y: auto !important;
}

:deep(.v-list-item) {
  color: rgb(var(--v-theme-on-surface)) !important;
  transition: all 0.2s ease;
  padding: 12px 16px !important;
  min-height: 48px !important;
  position: relative;
  z-index: 1;
}

:deep(.v-list-item:hover) {
  background: rgba(var(--v-theme-primary), 0.1) !important;
  color: rgb(var(--v-theme-primary)) !important;
}

:deep(.v-list-item--active) {
  background: rgba(var(--v-theme-primary), 0.2) !important;
  color: rgb(var(--v-theme-primary)) !important;
}

:deep(.v-list-item-title) {
  color: inherit !important;
  font-weight: 400;
  position: relative;
  z-index: 2;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

/* Additional dropdown title visibility improvements */
:deep(.v-list-item:hover .v-list-item-title) {
  color: rgb(var(--v-theme-primary)) !important;
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

:deep(.v-list-item--active .v-list-item-title) {
  color: rgb(var(--v-theme-primary)) !important;
  font-weight: 500;
}

/* Ensure dropdown menu borders don't interfere with text */
:deep(.v-list-item::before) {
  z-index: 0 !important;
}

:deep(.v-list-item::after) {
  z-index: 0 !important;
}

/* Improve dropdown menu contrast */
:deep(.v-menu .v-overlay__content) {
  backdrop-filter: blur(8px);
}

:deep(.v-list) {
  backdrop-filter: blur(8px);
}

/* Ensure select menus work properly */
:deep(.v-select .v-field__append-inner) {
  color: rgb(var(--v-theme-on-surface-variant));
}

:deep(.v-select.v-select--active-menu .v-field__append-inner .v-icon) {
  transform: rotate(180deg);
  color: rgb(var(--v-theme-primary));
}

/* Fix select field interaction */
:deep(.v-select .v-field__input) {
  cursor: pointer !important;
}

:deep(.v-select .v-field) {
  cursor: pointer !important;
}

/* Ensure dropdown arrow is visible and clickable */
:deep(.v-select .v-field__append-inner) {
  pointer-events: auto !important;
  cursor: pointer !important;
}

/* Fix overlay positioning */
:deep(.v-overlay) {
  position: fixed !important;
}

:deep(.v-overlay__scrim) {
  position: fixed !important;
  z-index: 9999 !important;
}

/* Ensure proper scrolling and container sizing */
.settings-content :deep(.v-container) {
  padding: 0; /* Remove padding since .settings-content now handles it */
  max-width: none;
  /* Ensure container doesn't constrain height */
  height: auto;
}

/* Add scroll indicators for better UX */
.settings-screen {
  /* Add subtle scroll indicator */
  position: relative;
}

.settings-screen::after {
  content: "";
  position: fixed;
  bottom: 80px; /* Above footer */
  right: 20px;
  width: 4px;
  height: 40px;
  background: linear-gradient(
    to bottom,
    transparent,
    rgba(var(--v-theme-primary), 0.3)
  );
  border-radius: 2px;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
  z-index: 10;
}

/* Show scroll indicator when content is scrollable */
.step-content:hover .settings-screen::after {
  opacity: 1;
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  :deep(.v-card),
  :deep(.v-text-field .v-field),
  :deep(.v-select .v-field),
  .settings-btn {
    transition: none;
  }

  :deep(.v-card:hover),
  :deep(.v-text-field .v-field:hover),
  :deep(.v-select .v-field:hover),
  .settings-btn:hover {
    transform: none;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  :deep(.v-card) {
    border: 2px solid rgb(var(--v-theme-outline));
  }

  :deep(.v-text-field .v-field),
  :deep(.v-select .v-field) {
    border: 2px solid rgb(var(--v-theme-outline));
  }

  .settings-btn {
    border: 2px solid rgb(var(--v-theme-primary));
  }
}
</style>
