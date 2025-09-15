<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Verification & Summary</h2>
            <p class="text-body-1 mb-6">
              Review your miner configuration and verify the connection.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12" md="6">
            <v-card outlined class="mb-4">
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-information-outline</v-icon>
                Miner Details
              </v-card-title>
              <v-card-text>
                <v-list dense>
                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Name</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        minerData.name
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Type</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        getMinerTypeName
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >IP Address</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        minerData.ip_address
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Port</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        minerData.port
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>

            <v-card outlined>
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-server-network</v-icon>
                Pool Configuration
              </v-card-title>
              <v-card-text>
                <v-list dense>
                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Pool URL</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        minerData.pool_url
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Pool Port</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        minerData.pool_port
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Worker Username</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        minerData.pool_user
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="6">
            <v-card outlined class="mb-4">
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-tune</v-icon>
                Hardware Settings
              </v-card-title>
              <v-card-text>
                <v-list dense>
                  <v-list-item v-if="minerData.fan_speed !== null">
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Fan Speed</v-list-item-subtitle
                      >
                      <v-list-item-title
                        >{{ minerData.fan_speed }}%</v-list-item-title
                      >
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider
                    v-if="
                      minerData.fan_speed !== null &&
                      (minerData.frequency !== null ||
                        minerData.power_limit !== null)
                    "
                  ></v-divider>

                  <v-list-item v-if="minerData.frequency !== null">
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Frequency</v-list-item-subtitle
                      >
                      <v-list-item-title
                        >{{ minerData.frequency }} MHz</v-list-item-title
                      >
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider
                    v-if="
                      minerData.frequency !== null &&
                      minerData.power_limit !== null
                    "
                  ></v-divider>

                  <v-list-item v-if="minerData.power_limit !== null">
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Power Limit</v-list-item-subtitle
                      >
                      <v-list-item-title
                        >{{ minerData.power_limit }} W</v-list-item-title
                      >
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>

            <v-card outlined :color="connectionStatusColor" dark>
              <v-card-title class="subtitle-1">
                <v-icon left>{{ connectionStatusIcon }}</v-icon>
                Connection Status
              </v-card-title>
              <v-card-text>
                <p class="mb-2">
                  {{ connectionStatus.message || "Connection status unknown" }}
                </p>

                <v-expand-transition>
                  <div v-if="connectionStatus.status === 'error'">
                    <v-divider class="my-2"></v-divider>
                    <h3 class="subtitle-2 mb-2">Troubleshooting Tips</h3>
                    <ul class="mb-0">
                      <li>Verify the IP address and port are correct</li>
                      <li>
                        Check that the miner is powered on and connected to the
                        network
                      </li>
                      <li>Ensure no firewall is blocking the connection</li>
                      <li>Try restarting the miner</li>
                    </ul>
                  </div>
                </v-expand-transition>

                <v-expand-transition>
                  <div
                    v-if="
                      connectionStatus.status === 'success' &&
                      connectionStatus.details
                    "
                  >
                    <v-divider class="my-2"></v-divider>
                    <h3 class="subtitle-2 mb-2">Detected Information</h3>
                    <v-simple-table dense dark>
                      <template v-slot:default>
                        <tbody>
                          <tr
                            v-for="(value, key) in connectionStatus.details"
                            :key="key"
                          >
                            <td>{{ formatKey(key) }}</td>
                            <td>{{ formatValue(value) }}</td>
                          </tr>
                        </tbody>
                      </template>
                    </v-simple-table>
                  </div>
                </v-expand-transition>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row class="mt-4">
          <v-col cols="12" md="6" offset-md="3">
            <v-card outlined>
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-content-save-outline</v-icon>
                Save as Template
              </v-card-title>
              <v-card-text>
                <p class="text-body-2 mb-4">
                  Save these settings as a template for future miners.
                </p>
                <v-text-field
                  v-model="templateName"
                  label="Template Name"
                  hint="Enter a descriptive name for this configuration"
                  persistent-hint
                  outlined
                  dense
                ></v-text-field>
                <v-btn
                  color="primary"
                  block
                  class="mt-4"
                  @click="saveTemplate"
                  :disabled="!templateName"
                >
                  <v-icon left>mdi-content-save</v-icon>
                  Save as Template
                </v-btn>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: "VerificationSummary",

  props: {
    minerData: {
      type: Object,
      required: true,
    },

    connectionStatus: {
      type: Object,
      default: () => ({
        status: "unknown",
        message: "",
        details: {},
      }),
    },

    isEditMode: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      templateName: this.isEditMode
        ? `${this.minerData.name} Template`
        : "My Miner Template",
    };
  },

  computed: {
    getMinerTypeName() {
      switch (this.minerData.type) {
        case "bitaxe":
          return "Bitaxe";
        case "avalon_nano":
          return "Avalon Nano";
        case "magic_miner":
          return "Magic Miner";
        default:
          return "Bitcoin Miner";
      }
    },

    connectionStatusColor() {
      switch (this.connectionStatus.status) {
        case "success":
          return "success";
        case "error":
          return "error";
        case "warning":
          return "warning";
        default:
          return "grey darken-1";
      }
    },

    connectionStatusIcon() {
      switch (this.connectionStatus.status) {
        case "success":
          return "mdi-check-circle";
        case "error":
          return "mdi-alert-circle";
        case "warning":
          return "mdi-alert";
        default:
          return "mdi-help-circle";
      }
    },
  },

  methods: {
    saveTemplate() {
      if (!this.templateName) return;

      // Emit event to parent component to save template
      this.$emit("save-as-template", this.templateName);

      // Show success message
      this.$nextTick(() => {
        this.showSnackbar("Template saved successfully");
      });
    },

    showSnackbar(message) {
      // This would typically use a global snackbar system
      // For now, we'll just log to console
      console.log("Snackbar:", message);
    },

    formatKey(key) {
      // Convert snake_case to Title Case
      return key
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
    },

    formatValue(value) {
      if (value === null || value === undefined) {
        return "N/A";
      }

      if (typeof value === "boolean") {
        return value ? "Yes" : "No";
      }

      if (Array.isArray(value)) {
        return value.join(", ");
      }

      if (typeof value === "object") {
        return JSON.stringify(value);
      }

      return value.toString();
    },
  },
};
</script>

<style scoped>
.v-list-item {
  min-height: 40px;
}
</style>
