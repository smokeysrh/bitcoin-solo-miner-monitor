<template>
  <div class="preferences-screen">
    <div class="preferences-content">
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h1 class="text-h4 mb-4">Customize Your Experience</h1>
            <p class="text-subtitle-1 mb-6">
              Set your preferences to personalize your mining monitoring
              experience.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12">
            <v-form ref="preferencesForm" v-model="formValid">
              <!-- Dashboard Layout -->
              <v-card variant="outlined" class="mb-6">
                <v-card-title>
                  <v-icon start color="primary"
                    >mdi-view-dashboard-outline</v-icon
                  >
                  Dashboard Layout
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-select
                        v-model="preferences.dashboard_layout"
                        :items="layoutOptions"
                        label="Dashboard Layout"
                        variant="outlined"
                        hint="Choose how widgets are arranged on your dashboard"
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

              <!-- Notification Preferences -->
              <v-card variant="outlined" class="mb-6">
                <v-card-title>
                  <v-icon start color="primary">mdi-bell-outline</v-icon>
                  Notification Preferences
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-switch
                        v-model="preferences.desktop_notifications"
                        label="Desktop Notifications"
                        hint="Show notifications on your desktop"
                        persistent-hint
                      ></v-switch>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-switch
                        v-model="preferences.sound_alerts"
                        label="Sound Alerts"
                        hint="Play sound when important events occur"
                        persistent-hint
                      ></v-switch>
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col cols="12" md="6">
                      <v-switch
                        v-model="preferences.email_notifications"
                        label="Email Notifications"
                        hint="Receive notifications via email"
                        persistent-hint
                      ></v-switch>
                    </v-col>

                    <v-col
                      cols="12"
                      md="6"
                      v-if="preferences.email_notifications"
                    >
                      <v-text-field
                        v-model="preferences.email_address"
                        label="Email Address"
                        type="email"
                        variant="outlined"
                        hint="Enter your email address for notifications"
                        persistent-hint
                        :rules="emailRules"
                        :disabled="!preferences.email_notifications"
                      ></v-text-field>
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col cols="12">
                      <h3 class="text-subtitle-1 mb-2">Notification Events</h3>
                      <p class="text-caption mb-4">
                        Select which events should trigger notifications
                      </p>

                      <v-checkbox
                        v-model="preferences.notify_miner_offline"
                        label="Miner goes offline"
                        :disabled="
                          !preferences.desktop_notifications &&
                          !preferences.email_notifications
                        "
                      ></v-checkbox>

                      <v-checkbox
                        v-model="preferences.notify_temperature_alert"
                        label="Temperature exceeds threshold"
                        :disabled="
                          !preferences.desktop_notifications &&
                          !preferences.email_notifications
                        "
                      ></v-checkbox>

                      <v-checkbox
                        v-model="preferences.notify_hashrate_drop"
                        label="Hashrate drops significantly"
                        :disabled="
                          !preferences.desktop_notifications &&
                          !preferences.email_notifications
                        "
                      ></v-checkbox>

                      <v-checkbox
                        v-model="preferences.notify_new_miner"
                        label="New miner discovered"
                        :disabled="
                          !preferences.desktop_notifications &&
                          !preferences.email_notifications
                        "
                      ></v-checkbox>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>

              <!-- Appearance -->
              <v-card variant="outlined">
                <v-card-title>
                  <v-icon start color="primary">mdi-palette</v-icon>
                  Appearance
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-select
                        v-model="preferences.accent_color"
                        :items="accentColorOptions"
                        label="Accent Color"
                        variant="outlined"
                        hint="Choose your preferred accent color"
                        persistent-hint
                        item-title="title"
                        item-value="value"
                        attach
                        :menu-props="{
                          closeOnContentClick: true,
                          maxHeight: 300,
                          transition: 'slide-y-transition',
                        }"
                      >
                        <template v-slot:selection="{ item }">
                          <v-chip
                            :color="item.value"
                            theme="dark"
                            size="small"
                            class="mr-2"
                          ></v-chip>
                          {{ item.title }}
                        </template>
                        <template v-slot:item="{ item }">
                          <v-chip
                            :color="item.value"
                            theme="dark"
                            size="small"
                            class="mr-2"
                          ></v-chip>
                          {{ item.title }}
                        </template>
                      </v-select>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-select
                        v-model="preferences.font_size"
                        :items="fontSizeOptions"
                        label="Font Size"
                        variant="outlined"
                        hint="Adjust the text size throughout the application"
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
                        v-model="preferences.compact_tables"
                        label="Compact Tables"
                        hint="Use more compact table layouts to fit more data"
                        persistent-hint
                      ></v-switch>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-switch
                        v-model="preferences.animations"
                        label="UI Animations"
                        hint="Enable or disable UI animations"
                        persistent-hint
                      ></v-switch>
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
              <h3 class="text-h6">Preference Recommendation</h3>
              <p class="mb-0">
                We've selected preferences that work well for beginners. You can
                always change these later in the Settings page.
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
  name: "UserPreferencesScreen",

  props: {
    experienceLevel: {
      type: String,
      default: "beginner",
    },
  },

  data() {
    return {
      formValid: true,

      preferences: {
        dashboard_layout: "grid",
        desktop_notifications: true,
        sound_alerts: true,
        email_notifications: false,
        email_address: "",
        notify_miner_offline: true,
        notify_temperature_alert: true,
        notify_hashrate_drop: true,
        notify_new_miner: true,
        accent_color: "primary",
        font_size: "medium",
        compact_tables: false,
        animations: true,
      },



      layoutOptions: [
        { title: "Grid Layout", value: "grid" },
        { title: "List Layout", value: "list" },
        { title: "Dashboard Layout", value: "dashboard" },
      ],

      chartTypeOptions: [{ title: "Line Chart", value: "line" }],

      accentColorOptions: [
        { title: "Bitcoin Orange", value: "primary" },
        { title: "Success Green", value: "success" },
        { title: "Info Blue", value: "info" },
        { title: "Warning Amber", value: "warning" },
        { title: "Error Red", value: "error" },
        { title: "Secondary Grey", value: "secondary" },
      ],

      fontSizeOptions: [
        { title: "Small", value: "small" },
        { title: "Medium", value: "medium" },
        { title: "Large", value: "large" },
      ],

      emailRules: [
        (v) =>
          !this.preferences.email_notifications ||
          !!v ||
          "Email address is required when email notifications are enabled",
        (v) =>
          !v || /.+@.+\..+/.test(v) || "Please enter a valid email address",
      ],
    };
  },

  created() {
    // Set default preferences based on experience level
    this.applyExperienceLevelDefaults();
  },

  // Removed problematic watcher that was causing infinite loops
  // Widget validation is now handled in methods when needed

  methods: {
    applyExperienceLevelDefaults() {
      // Apply different default preferences based on experience level
      switch (this.experienceLevel) {
        case "beginner":
          this.preferences.dashboard_layout = "grid";
          this.preferences.compact_tables = false;
          break;

        case "intermediate":
          this.preferences.dashboard_layout = "dashboard";
          this.preferences.compact_tables = true;
          break;

        case "advanced":
          this.preferences.dashboard_layout = "dashboard";
          this.preferences.compact_tables = true;
          break;
      }
    },

    proceed() {
      if (!this.$refs.preferencesForm.validate()) return;

      // Additional validation for email notifications
      if (
        this.preferences.email_notifications &&
        !this.preferences.email_address
      ) {
        return;
      }

      console.log("UserPreferencesScreen: Emitting preferences:", this.preferences);
      console.log("UserPreferencesScreen: Preferences keys:", Object.keys(this.preferences));

      // Emit the preferences to the parent component
      this.$emit("preferences-updated", this.preferences);

      // Emit event to move to the next step
      this.$emit("next");
    },
  },
};
</script>

<style scoped>
/* Import shared wizard styles for standardized info bubbles */
@import "./shared-wizard-styles.css";

/* Preferences screen layout - Fixed for proper scrolling */
.preferences-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  /* Ensure the screen takes full height of step-content */
  min-height: 100%;
}

.preferences-content {
  flex: 1;
  /* Remove overflow-y: auto to prevent nested scrolling - parent .step-content handles scrolling */
  padding: var(--spacing-lg);
  min-height: 0;
  /* Allow content to expand naturally */
  overflow: visible;
}

/* Ensure proper scrolling and container sizing */
.preferences-content :deep(.v-container) {
  padding: 0; /* Remove padding since .preferences-content now handles it */
  max-width: none;
  /* Ensure container doesn't constrain height */
  height: auto;
}

/* Card styling improvements */
:deep(.v-card) {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 12px;
  transition: all 0.3s ease;
  margin-bottom: 24px;
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

/* Responsive design */
@media (max-width: 960px) {
  .preferences-content {
    padding: var(--spacing-md);
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
  .preferences-content {
    padding: var(--spacing-sm);
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

/* Ensure select field interaction */
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
  color: rgb(var(--v-theme-on-surface-variant));
}

:deep(.v-select.v-select--active-menu .v-field__append-inner .v-icon) {
  transform: rotate(180deg);
  color: rgb(var(--v-theme-primary));
}

/* Fix overlay positioning */
:deep(.v-overlay) {
  position: fixed !important;
}

:deep(.v-overlay__scrim) {
  position: fixed !important;
  z-index: 9999 !important;
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


</style>
