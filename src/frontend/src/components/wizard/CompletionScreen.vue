<template>
  <div class="completion-screen">
    <div class="completion-content">
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center completion-header">
            <BitcoinSuccessMessage
              title="Setup Complete!"
              message="Your Bitcoin Solo Miner Monitoring application is now configured and ready to help you monitor your mining operations."
              size="lg"
              :animated="true"
              :show-actions="false"
              centered
              class="completion-success"
            />
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12">
            <v-card variant="outlined" class="mb-6">
              <v-card-title>
                <v-icon start color="primary">mdi-information-outline</v-icon>
                Setup Summary
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <h3 class="text-subtitle-1">Experience Level</h3>
                    <v-chip
                      :color="getExperienceLevelColor"
                      theme="dark"
                      class="mt-2"
                    >
                      {{
                        experienceLevel.charAt(0).toUpperCase() +
                        experienceLevel.slice(1)
                      }}
                    </v-chip>
                  </v-col>

                  <v-col cols="12" md="6">
                    <h3 class="text-subtitle-1">Miners Discovered</h3>
                    <v-chip
                      :color="foundMiners.length > 0 ? 'success' : 'grey'"
                      theme="dark"
                      class="mt-2"
                    >
                      {{ foundMiners.length }} miners
                    </v-chip>
                  </v-col>
                </v-row>

                <v-divider class="my-4"></v-divider>

                <v-row>
                  <v-col cols="12" md="6">
                    <h3 class="text-subtitle-1">UI Mode</h3>
                    <p>
                      {{
                        settings.simple_mode ? "Simple Mode" : "Advanced Mode"
                      }}
                    </p>
                  </v-col>

                  <v-col cols="12" md="6">
                    <h3 class="text-subtitle-1">Default View</h3>
                    <p>{{ getDefaultViewName }}</p>
                  </v-col>
                </v-row>

                <v-row>
                  <v-col cols="12" md="6">
                    <h3 class="text-subtitle-1">Alerts</h3>
                    <p>
                      {{ settings.alerts.enabled ? "Enabled" : "Disabled" }}
                    </p>
                  </v-col>

                  <v-col cols="12" md="6">
                    <h3 class="text-subtitle-1">Dashboard Layout</h3>
                    <p>{{ getLayoutName }}</p>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>

            <v-card variant="outlined" class="mb-6">
              <v-card-title>
                <v-icon start color="primary">mdi-lightbulb-on</v-icon>
                Quick Start Guide
              </v-card-title>
              <v-card-text>
                <v-timeline dense>
                  <v-timeline-item color="primary" small>
                    <div class="font-weight-bold">Dashboard Overview</div>
                    <div class="text-caption">
                      Start by exploring your dashboard to see your miners'
                      status and performance.
                    </div>
                  </v-timeline-item>

                  <v-timeline-item color="primary" small>
                    <div class="font-weight-bold">Miner Management</div>
                    <div class="text-caption">
                      Go to the Miners page to add, edit, or remove miners from
                      your monitoring system.
                    </div>
                  </v-timeline-item>

                  <v-timeline-item color="primary" small>
                    <div class="font-weight-bold">Analytics</div>
                    <div class="text-caption">
                      Check the Analytics page for detailed performance charts
                      and statistics.
                    </div>
                  </v-timeline-item>

                  <v-timeline-item color="primary" small>
                    <div class="font-weight-bold">Settings</div>
                    <div class="text-caption">
                      Visit the Settings page to further customize your
                      experience or change any configurations.
                    </div>
                  </v-timeline-item>
                </v-timeline>
              </v-card-text>
            </v-card>

            <v-card variant="outlined">
              <v-card-title>
                <v-icon start color="primary">mdi-help-circle</v-icon>
                Need Help?
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6" class="text-center">
                    <v-btn
                      color="primary"
                      variant="outlined"
                      block
                      class="mb-2"
                      href="https://github.com/smokeysrh/bitcoin-solo-miner-monitor/tree/main/docs"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <v-icon start>mdi-book-open-variant</v-icon>
                      Documentation
                    </v-btn>
                  </v-col>

                  <v-col cols="12" md="6" class="text-center">
                    <v-btn
                      color="primary"
                      variant="outlined"
                      block
                      class="mb-2"
                      href="https://discord.gg/GzNsNnh4yT"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <v-icon start>mdi-forum</v-icon>
                      Community Forum
                    </v-btn>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </div>
  </div>
</template>

<script>
import BitcoinSuccessMessage from "../BitcoinSuccessMessage.vue";
export default {
  name: "CompletionScreen",

  components: {
    BitcoinSuccessMessage,
  },

  props: {
    experienceLevel: {
      type: String,
      default: "beginner",
    },

    foundMiners: {
      type: Array,
      default: () => [],
    },

    settings: {
      type: Object,
      default: () => ({}),
    },

    preferences: {
      type: Object,
      default: () => ({}),
    },
  },

  computed: {
    getExperienceLevelColor() {
      switch (this.experienceLevel) {
        case "beginner":
          return "info";
        case "intermediate":
          return "primary";
        case "advanced":
          return "purple";
        default:
          return "grey";
      }
    },

    getDefaultViewName() {
      const viewMap = {
        dashboard: "Dashboard",
        "dashboard-simple": "Simple Dashboard",
        miners: "Miners",
        analytics: "Analytics",
        network: "Network",
      };

      return viewMap[this.settings.default_view] || "Dashboard";
    },

    getLayoutName() {
      const layoutMap = {
        grid: "Grid Layout",
        list: "List Layout",
        dashboard: "Dashboard Layout",
      };

      return layoutMap[this.preferences.dashboard_layout] || "Grid Layout";
    },
  },

  methods: {
    launchDashboard() {
      console.log("CompletionScreen: Launch Dashboard button clicked");
      this.$emit("finish");
      console.log("CompletionScreen: Finish event emitted");
    },
  },
};
</script>

<style scoped>
/* Completion screen layout - Fixed for proper scrolling */
.completion-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  /* Ensure the screen takes full height of step-content */
  min-height: 100%;
}

.completion-content {
  flex: 1;
  /* Remove overflow-y: auto to prevent nested scrolling - parent .step-content handles scrolling */
  padding: var(--spacing-lg);
  min-height: 0;
  /* Allow content to expand naturally */
  overflow: visible;
}

/* Ensure proper scrolling and container sizing */
.completion-content :deep(.v-container) {
  padding: 0; /* Remove padding since .completion-content now handles it */
  max-width: none;
  /* Ensure container doesn't constrain height */
  height: auto;
}

/* Completion screen styling */
.completion-header {
  padding: 32px 0;
  margin-bottom: 32px;
}

.completion-success {
  max-width: 600px;
  margin: 0 auto;
}

/* Enhanced card styling */
:deep(.v-card) {
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-outline-variant), 0.5);
}

:deep(.v-card:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

:deep(.v-card-title) {
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
  padding: 20px 24px 16px 24px;
}

:deep(.v-card-text) {
  padding: 16px 24px 24px 24px;
}

/* Chip styling */
:deep(.v-chip) {
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.v-chip:hover) {
  transform: scale(1.05);
}

/* Timeline styling */
:deep(.v-timeline) {
  padding: 16px 0;
}

:deep(.v-timeline-item) {
  margin-bottom: 16px;
}

:deep(.v-timeline-item .v-timeline-item__body) {
  background: rgba(var(--v-theme-surface-variant), 0.5);
  border-radius: 8px;
  padding: 12px 16px;
  margin-left: 16px;
  transition: all 0.3s ease;
}

:deep(.v-timeline-item .v-timeline-item__body:hover) {
  background: rgba(var(--v-theme-surface-variant), 0.8);
  transform: translateX(4px);
}

/* Button styling */
:deep(.v-btn) {
  border-radius: 12px;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.v-btn:hover) {
  transform: translateY(-2px);
}

/* Responsive design */
@media (max-width: 960px) {
  .completion-content {
    padding: var(--spacing-md);
  }

  .completion-header {
    padding: 24px 16px;
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
  .completion-content {
    padding: var(--spacing-sm);
  }

  .completion-header {
    padding: 20px 12px;
  }

  :deep(.v-card-title) {
    padding: 12px 16px 8px 16px;
    font-size: 1rem;
  }

  :deep(.v-card-text) {
    padding: 8px 16px 16px 16px;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  :deep(.v-card),
  :deep(.v-chip),
  :deep(.v-timeline-item .v-timeline-item__body),
  :deep(.v-btn),
  .launch-btn {
    animation: none;
    transition: none;
  }

  :deep(.v-card:hover),
  :deep(.v-chip:hover),
  :deep(.v-timeline-item .v-timeline-item__body:hover),
  :deep(.v-btn:hover),
  .launch-btn:hover {
    transform: none;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .completion-header {
    border: 2px solid rgb(var(--v-theme-outline));
  }

  :deep(.v-card) {
    border: 2px solid rgb(var(--v-theme-outline));
  }

  .launch-btn {
    border: 2px solid rgb(var(--v-theme-success));
  }

  :deep(.v-chip) {
    border: 1px solid rgb(var(--v-theme-outline));
  }
}
</style>
