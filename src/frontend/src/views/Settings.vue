<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Settings</h1>
      </v-col>
    </v-row>

    <!-- General Settings -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            General Settings
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              :loading="saving"
              :disabled="!settingsChanged"
              @click="saveSettings"
            >
              <v-icon left>mdi-content-save</v-icon>
              Save Changes
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-form ref="settingsForm" v-model="formValid">
              <v-row>


                <v-col cols="12" md="6">
                  <v-select
                    v-model="settings.refresh_interval"
                    :items="refreshIntervalOptions"
                    label="Dashboard Refresh Interval"
                    hint="How often the dashboard should refresh (in seconds)"
                    persistent-hint
                    type="number"
                  ></v-select>
                </v-col>

                <v-col cols="12" md="6">
                  <v-switch
                    v-model="settings.simple_mode"
                    label="Simple Mode"
                    hint="Enable simplified user interface for easier navigation"
                    persistent-hint
                    @change="handleModeChange"
                  ></v-switch>
                </v-col>
              </v-row>

              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="settings.chart_retention_days"
                    :items="retentionOptions"
                    label="Data Retention Period"
                    hint="How long to keep historical data (in days)"
                    persistent-hint
                    type="number"
                  ></v-select>
                </v-col>

                <v-col cols="12" md="6">
                  <v-select
                    v-model="settings.temperature_unit"
                    :items="temperatureUnitOptions"
                    label="Temperature Unit"
                    hint="Unit for displaying temperature values"
                    persistent-hint
                  ></v-select>
                </v-col>
              </v-row>

              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="settings.default_view"
                    :items="defaultViewOptions"
                    label="Default View"
                    hint="The view to show when the application starts"
                    persistent-hint
                  ></v-select>
                </v-col>

                <v-col cols="12" md="6">
                  <v-select
                    v-model="settings.polling_interval"
                    :items="pollingIntervalOptions"
                    label="Miner Polling Interval"
                    hint="How often to poll miners for data (in seconds)"
                    persistent-hint
                    type="number"
                  ></v-select>
                </v-col>
              </v-row>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Alert Settings -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Alert Settings
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              :loading="savingAlerts"
              :disabled="!alertsChanged"
              @click="saveAlertSettings"
            >
              <v-icon left>mdi-content-save</v-icon>
              Save Alerts
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-form ref="alertsForm" v-model="alertsFormValid">
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
                    hint="How to receive alert notifications"
                    persistent-hint
                    :disabled="!alertSettings.enabled"
                  ></v-select>
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>
              <h3 class="text-h6 mb-4">Alert Thresholds</h3>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="alertSettings.temperature_threshold"
                    label="Temperature Threshold (°C)"
                    hint="Alert when temperature exceeds this value"
                    persistent-hint
                    type="number"
                    :rules="[(v) => v >= 0 || 'Temperature must be positive']"
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>

                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="alertSettings.hashrate_drop_percent"
                    label="Hashrate Drop Threshold (%)"
                    hint="Alert when hashrate drops by this percentage"
                    persistent-hint
                    type="number"
                    :rules="[
                      (v) =>
                        (v >= 0 && v <= 100) ||
                        'Percentage must be between 0 and 100',
                    ]"
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="alertSettings.offline_duration"
                    label="Offline Duration (minutes)"
                    hint="Alert when miner is offline for this duration"
                    persistent-hint
                    type="number"
                    :rules="[(v) => v >= 0 || 'Duration must be positive']"
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>

                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="alertSettings.rejected_shares_percent"
                    label="Rejected Shares Threshold (%)"
                    hint="Alert when rejected shares exceed this percentage"
                    persistent-hint
                    type="number"
                    :rules="[
                      (v) =>
                        (v >= 0 && v <= 100) ||
                        'Percentage must be between 0 and 100',
                    ]"
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>
              <h3 class="text-h6 mb-4">Notification Settings</h3>

              <v-row v-if="alertSettings.notification_method === 'email'">
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="alertSettings.email_address"
                    label="Email Address"
                    hint="Email address to receive notifications"
                    persistent-hint
                    :rules="[
                      (v) => /.+@.+\..+/.test(v) || 'Email must be valid',
                    ]"
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>

                <v-col cols="12" md="6">
                  <v-select
                    v-model="alertSettings.email_frequency"
                    :items="emailFrequencyOptions"
                    label="Email Frequency"
                    hint="How often to send email notifications"
                    persistent-hint
                    :disabled="!alertSettings.enabled"
                  ></v-select>
                </v-col>
              </v-row>

              <v-row v-if="alertSettings.notification_method === 'webhook'">
                <v-col cols="12">
                  <v-text-field
                    v-model="alertSettings.webhook_url"
                    label="Webhook URL"
                    hint="URL to send webhook notifications"
                    persistent-hint
                    :rules="[
                      (v) => /^https?:\/\/.+/.test(v) || 'URL must be valid',
                    ]"
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-row v-if="alertSettings.notification_method === 'telegram'">
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="alertSettings.telegram_bot_token"
                    label="Telegram Bot Token"
                    hint="Token for your Telegram bot (optional for local notifications)"
                    persistent-hint
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>

                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="alertSettings.telegram_chat_id"
                    label="Telegram Chat ID"
                    hint="Chat ID to receive notifications"
                    persistent-hint
                    :disabled="!alertSettings.enabled"
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Database Settings -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Database Settings</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <v-card outlined>
                  <v-card-title>
                    <v-icon left>mdi-database</v-icon>
                    Configuration Database
                  </v-card-title>
                  <v-card-text>
                    <p>
                      SQLite database for storing application configuration and
                      miner settings.
                    </p>
                    <v-list-item>
                      <v-list-item-icon>
                        <v-icon>mdi-file-document</v-icon>
                      </v-list-item-icon>
                      <v-list-item-content>
                        <v-list-item-title>Database File</v-list-item-title>
                        <v-list-item-subtitle>{{
                          dbInfo.sqlite_path
                        }}</v-list-item-subtitle>
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-icon>
                        <v-icon>mdi-database-check</v-icon>
                      </v-list-item-icon>
                      <v-list-item-content>
                        <v-list-item-title>Status</v-list-item-title>
                        <v-list-item-subtitle>
                          <v-chip
                            small
                            :color="
                              dbInfo.sqlite_status === 'connected'
                                ? 'success'
                                : 'error'
                            "
                            text-color="white"
                          >
                            {{ dbInfo.sqlite_status }}
                          </v-chip>
                        </v-list-item-subtitle>
                      </v-list-item-content>
                    </v-list-item>
                  </v-card-text>
                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn
                      color="primary"
                      @click="backupConfigDb"
                      :loading="backingUpConfig"
                    >
                      <v-icon left>mdi-backup-restore</v-icon>
                      Backup
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>

              <v-col cols="12" md="6">
                <v-card outlined>
                  <v-card-title>
                    <v-icon left>mdi-chart-timeline</v-icon>
                    Time-Series Database
                  </v-card-title>
                  <v-card-text>
                    <p>
                      InfluxDB for storing historical metrics and performance
                      data.
                    </p>
                    <v-list-item>
                      <v-list-item-icon>
                        <v-icon>mdi-server</v-icon>
                      </v-list-item-icon>
                      <v-list-item-content>
                        <v-list-item-title>Connection</v-list-item-title>
                        <v-list-item-subtitle>{{
                          dbInfo.influx_url
                        }}</v-list-item-subtitle>
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-icon>
                        <v-icon>mdi-database-check</v-icon>
                      </v-list-item-icon>
                      <v-list-item-content>
                        <v-list-item-title>Status</v-list-item-title>
                        <v-list-item-subtitle>
                          <v-chip
                            small
                            :color="
                              dbInfo.influx_status === 'connected'
                                ? 'success'
                                : 'error'
                            "
                            text-color="white"
                          >
                            {{ dbInfo.influx_status }}
                          </v-chip>
                        </v-list-item-subtitle>
                      </v-list-item-content>
                    </v-list-item>
                  </v-card-text>
                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="error" @click="showPurgeDialog = true">
                      <v-icon left>mdi-delete</v-icon>
                      Purge Old Data
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Advanced Settings -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Advanced Settings</v-card-title>
          <v-card-text>
            <v-alert type="warning" prominent border="left" class="mb-4">
              These settings are for advanced users only. Incorrect
              configuration may cause the application to malfunction.
            </v-alert>

            <v-expansion-panels>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-api</v-icon>
                  API Settings
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-form ref="apiForm">
                    <v-row>
                      <v-col cols="12" md="6">
                        <v-switch
                          v-model="advancedSettings.api_enabled"
                          label="Enable External API Access"
                          hint="Allow access to the API from external sources"
                          persistent-hint
                        ></v-switch>
                      </v-col>

                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model="advancedSettings.api_port"
                          label="API Port"
                          hint="Port for the API server"
                          persistent-hint
                          type="number"
                          :rules="[
                            (v) =>
                              (v >= 1024 && v <= 65535) ||
                              'Port must be between 1024 and 65535',
                          ]"
                          :disabled="!advancedSettings.api_enabled"
                        ></v-text-field>
                      </v-col>
                    </v-row>

                    <!-- Authentication settings removed - no longer required for local network access -->

                    <v-row>
                      <v-col cols="12" class="text-right">
                        <v-btn
                          color="primary"
                          @click="saveAdvancedSettings('api')"
                          :loading="savingAdvanced"
                          :disabled="!apiSettingsChanged"
                        >
                          Save API Settings
                        </v-btn>
                      </v-col>
                    </v-row>
                  </v-form>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-tune</v-icon>
                  Performance Settings
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-form ref="perfForm">
                    <v-row>
                      <v-col cols="12" md="6">
                        <v-select
                          v-model="advancedSettings.log_level"
                          :items="logLevelOptions"
                          label="Log Level"
                          hint="Verbosity of application logs"
                          persistent-hint
                        ></v-select>
                      </v-col>

                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model.number="
                            advancedSettings.max_concurrent_requests
                          "
                          label="Max Concurrent Requests"
                          hint="Maximum number of concurrent requests to miners"
                          persistent-hint
                          type="number"
                          :rules="[(v) => v >= 1 || 'Value must be at least 1']"
                        ></v-text-field>
                      </v-col>
                    </v-row>

                    <v-row>
                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model.number="advancedSettings.request_timeout"
                          label="Request Timeout (seconds)"
                          hint="Timeout for requests to miners"
                          persistent-hint
                          type="number"
                          :rules="[(v) => v >= 1 || 'Value must be at least 1']"
                        ></v-text-field>
                      </v-col>

                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model.number="
                            advancedSettings.websocket_update_interval
                          "
                          label="WebSocket Update Interval (seconds)"
                          hint="How often to send updates via WebSocket"
                          persistent-hint
                          type="number"
                          :rules="[
                            (v) => v >= 0.1 || 'Value must be at least 0.1',
                          ]"
                        ></v-text-field>
                      </v-col>
                    </v-row>

                    <v-row>
                      <v-col cols="12" class="text-right">
                        <v-btn
                          color="primary"
                          @click="saveAdvancedSettings('performance')"
                          :loading="savingAdvanced"
                          :disabled="!perfSettingsChanged"
                        >
                          Save Performance Settings
                        </v-btn>
                      </v-col>
                    </v-row>
                  </v-form>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-backup-restore</v-icon>
                  Backup & Restore
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-card outlined>
                        <v-card-title>Backup Configuration</v-card-title>
                        <v-card-text>
                          <p>
                            Create a backup of all application settings and
                            miner configurations.
                          </p>
                        </v-card-text>
                        <v-card-actions>
                          <v-spacer></v-spacer>
                          <v-btn
                            color="primary"
                            @click="createFullBackup"
                            :loading="creatingBackup"
                          >
                            <v-icon left>mdi-download</v-icon>
                            Download Backup
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-card outlined>
                        <v-card-title>Restore Configuration</v-card-title>
                        <v-card-text>
                          <p>
                            Restore application settings and miner
                            configurations from a backup file.
                          </p>
                          <v-file-input
                            v-model="backupFile"
                            label="Backup File"
                            accept=".json"
                            show-size
                            truncate-length="25"
                          ></v-file-input>
                        </v-card-text>
                        <v-card-actions>
                          <v-spacer></v-spacer>
                          <v-btn
                            color="warning"
                            @click="restoreFromBackup"
                            :disabled="!backupFile"
                            :loading="restoring"
                          >
                            <v-icon left>mdi-upload</v-icon>
                            Restore
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>
                  </v-row>

                  <v-row class="mt-4">
                    <v-col cols="12">
                      <v-card outlined>
                        <v-card-title class="red--text">
                          <v-icon left color="red">mdi-restart</v-icon>
                          Reset Application
                        </v-card-title>
                        <v-card-text>
                          <v-alert type="warning" prominent border="left">
                            <strong>Warning:</strong> Resetting the application
                            will clear all settings and return to the first-run
                            setup wizard. This action cannot be undone.
                          </v-alert>
                        </v-card-text>
                        <v-card-actions>
                          <v-spacer></v-spacer>
                          <v-btn
                            color="error"
                            @click="showResetConfirmation = true"
                          >
                            <v-icon left>mdi-restart</v-icon>
                            Reset Application
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Purge Data Dialog -->
    <v-dialog v-model="showPurgeDialog" max-width="500px">
      <v-card>
        <v-card-title>Purge Historical Data</v-card-title>
        <v-card-text>
          <p>Select the age of data to purge from the time-series database:</p>
          <v-select
            v-model="purgeAge"
            :items="purgeOptions"
            label="Purge Data Older Than"
          ></v-select>
          <v-alert type="warning" prominent border="left">
            This action cannot be undone. All data older than the selected age
            will be permanently deleted.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="showPurgeDialog = false">
            Cancel
          </v-btn>
          <v-btn color="error" @click="purgeData" :loading="purging">
            Purge Data
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Reset Application Dialog -->
    <v-dialog v-model="showResetConfirmation" max-width="500px">
      <v-card>
        <v-card-title class="red--text">Reset Application</v-card-title>
        <v-card-text>
          <v-alert type="error" prominent border="left">
            <strong>Warning:</strong> This will reset the application to its
            initial state. All settings, preferences, and configurations will be
            lost.
          </v-alert>
          <p class="mt-4">
            To confirm, please type "RESET" in the field below:
          </p>
          <v-text-field
            v-model="resetConfirmation"
            label="Type RESET to confirm"
            outlined
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="showResetConfirmation = false">
            Cancel
          </v-btn>
          <v-btn
            color="error"
            @click="resetApplication"
            :disabled="resetConfirmation !== 'RESET'"
            :loading="resetting"
          >
            Reset Application
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="showSnackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
      <template v-slot:action="{ attrs }">
        <v-btn text v-bind="attrs" @click="showSnackbar = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useSettingsStore } from "../stores/settings";
import { resetFirstRun } from "../services/firstRunService";
import axios from "axios";
import { cloneDeep } from "lodash";
import { useRouter } from "vue-router";

export default {
  name: "Settings",

  setup() {
    const settingsStore = useSettingsStore();
    const router = useRouter();

    // Forms
    const settingsForm = ref(null);
    const alertsForm = ref(null);
    const apiForm = ref(null);
    const perfForm = ref(null);

    // Form validation
    const formValid = ref(true);
    const alertsFormValid = ref(true);

    // Loading states
    const saving = ref(false);
    const savingAlerts = ref(false);
    const savingAdvanced = ref(false);
    const backingUpConfig = ref(false);
    const creatingBackup = ref(false);
    const restoring = ref(false);
    const purging = ref(false);

    // Settings
    const originalSettings = ref({});
    const settings = reactive({
      refresh_interval: 10,
      chart_retention_days: 30,
      temperature_unit: "celsius",
      default_view: "dashboard",
      polling_interval: 30,
      ui_mode: "advanced",
      simple_mode: (localStorage.getItem('uiMode') || 'advanced') === 'simple',
    });

    // Alert settings
    const originalAlertSettings = ref({});
    const alertSettings = reactive({
      enabled: false,
      notification_method: "browser",
      temperature_threshold: 80,
      hashrate_drop_percent: 20,
      offline_duration: 5,
      rejected_shares_percent: 5,
      email_address: "",
      email_frequency: "immediate",
      webhook_url: "",
      telegram_bot_token: "",
      telegram_chat_id: "",
    });

    // Advanced settings
    const originalAdvancedSettings = ref({});
    const advancedSettings = reactive({
      api_enabled: false,
      api_port: 8000,
      log_level: "info",
      max_concurrent_requests: 5,
      request_timeout: 10,
      websocket_update_interval: 1,
    });

    // Database info
    const dbInfo = reactive({
      sqlite_path: "/workspace/data/config.db",
      sqlite_status: "connected",
      influx_url: "http://localhost:8086",
      influx_status: "connected",
    });

    // Backup
    const backupFile = ref(null);

    // Purge dialog
    const showPurgeDialog = ref(false);
    const purgeAge = ref("30d");

    // Reset application
    const showResetConfirmation = ref(false);
    const resetConfirmation = ref("");
    const resetting = ref(false);

    // Authentication removed - no longer needed for local network access

    // Snackbar
    const showSnackbar = ref(false);
    const snackbarText = ref("");
    const snackbarColor = ref("success");

    // Options

    const uiModeOptions = [
      { text: "Simple Mode", value: "simple" },
      { text: "Advanced Mode", value: "advanced" },
    ];

    const refreshIntervalOptions = [
      { text: "5 seconds", value: 5 },
      { text: "10 seconds", value: 10 },
      { text: "30 seconds", value: 30 },
      { text: "1 minute", value: 60 },
      { text: "5 minutes", value: 300 },
    ];

    const retentionOptions = [
      { text: "7 days", value: 7 },
      { text: "14 days", value: 14 },
      { text: "30 days", value: 30 },
      { text: "60 days", value: 60 },
      { text: "90 days", value: 90 },
      { text: "180 days", value: 180 },
      { text: "365 days", value: 365 },
    ];

    const temperatureUnitOptions = [
      { text: "Celsius (°C)", value: "celsius" },
      { text: "Fahrenheit (°F)", value: "fahrenheit" },
    ];

    const defaultViewOptions = [
      { text: "Dashboard", value: "dashboard" },
      { text: "Miners", value: "miners" },
      { text: "Analytics", value: "analytics" },
      { text: "Network", value: "network" },
    ];

    const pollingIntervalOptions = [
      { text: "10 seconds", value: 10 },
      { text: "30 seconds", value: 30 },
      { text: "1 minute", value: 60 },
      { text: "5 minutes", value: 300 },
      { text: "10 minutes", value: 600 },
    ];

    const notificationMethodOptions = [
      { text: "Browser Notifications", value: "browser" },
      { text: "Email", value: "email" },
      { text: "Webhook", value: "webhook" },
      { text: "Telegram", value: "telegram" },
    ];

    const emailFrequencyOptions = [
      { text: "Immediate", value: "immediate" },
      { text: "Hourly Digest", value: "hourly" },
      { text: "Daily Digest", value: "daily" },
    ];

    const logLevelOptions = [
      { text: "Debug", value: "debug" },
      { text: "Info", value: "info" },
      { text: "Warning", value: "warning" },
      { text: "Error", value: "error" },
    ];

    const purgeOptions = [
      { text: "7 days", value: "7d" },
      { text: "30 days", value: "30d" },
      { text: "90 days", value: "90d" },
      { text: "180 days", value: "180d" },
      { text: "365 days", value: "365d" },
    ];

    // Computed properties
    const settingsChanged = computed(() => {
      return (
        JSON.stringify(settings) !== JSON.stringify(originalSettings.value)
      );
    });

    const alertsChanged = computed(() => {
      return (
        JSON.stringify(alertSettings) !==
        JSON.stringify(originalAlertSettings.value)
      );
    });

    const apiSettingsChanged = computed(() => {
      const originalApi = {
        api_enabled: originalAdvancedSettings.value.api_enabled,
        api_port: originalAdvancedSettings.value.api_port,
      };

      const currentApi = {
        api_enabled: advancedSettings.api_enabled,
        api_port: advancedSettings.api_port,
      };

      return JSON.stringify(currentApi) !== JSON.stringify(originalApi);
    });

    const perfSettingsChanged = computed(() => {
      const originalPerf = {
        log_level: originalAdvancedSettings.value.log_level,
        max_concurrent_requests:
          originalAdvancedSettings.value.max_concurrent_requests,
        request_timeout: originalAdvancedSettings.value.request_timeout,
        websocket_update_interval:
          originalAdvancedSettings.value.websocket_update_interval,
      };

      const currentPerf = {
        log_level: advancedSettings.log_level,
        max_concurrent_requests: advancedSettings.max_concurrent_requests,
        request_timeout: advancedSettings.request_timeout,
        websocket_update_interval: advancedSettings.websocket_update_interval,
      };

      return JSON.stringify(currentPerf) !== JSON.stringify(originalPerf);
    });

    // Handle UI mode change
    // Methods
    const loadSettings = async () => {
      try {
        // Get settings from store
        const storeSettings = settingsStore.settings;

        // Update settings
        Object.assign(settings, storeSettings);
        
        // Sync simple_mode with localStorage (localStorage takes precedence for UI mode)
        const currentUIMode = localStorage.getItem('uiMode') || 'advanced';
        settings.simple_mode = currentUIMode === 'simple';
        settings.ui_mode = currentUIMode;

        // Save original settings for comparison
        originalSettings.value = cloneDeep(settings);
      } catch (error) {
        console.error("Error loading settings:", error);
        showNotification("Error loading settings", "error");
      }
    };

    const loadAlertSettings = async () => {
      try {
        // Fetch alert settings from API
        const response = await axios.get("/api/settings/alerts");

        // Update alert settings
        Object.assign(alertSettings, response.data);

        // Save original settings for comparison
        originalAlertSettings.value = cloneDeep(alertSettings);
      } catch (error) {
        console.error("Error loading alert settings:", error);
        showNotification("Error loading alert settings", "error");
      }
    };

    const loadAdvancedSettings = async () => {
      try {
        // Fetch advanced settings from API
        const response = await axios.get("/api/settings/advanced");

        // Update advanced settings
        Object.assign(advancedSettings, response.data);

        // Save original settings for comparison
        originalAdvancedSettings.value = cloneDeep(advancedSettings);
      } catch (error) {
        console.error("Error loading advanced settings:", error);
        showNotification("Error loading advanced settings", "error");
      }
    };

    const loadDatabaseInfo = async () => {
      try {
        // Fetch database info from API
        const response = await axios.get("/api/system/database");

        // Update database info
        Object.assign(dbInfo, response.data);
      } catch (error) {
        console.error("Error loading database info:", error);
      }
    };



    const saveSettings = async () => {
      if (!formValid.value) {
        showNotification("Please fix the errors in the form", "error");
        return;
      }

      saving.value = true;

      try {
        // Sync ui_mode with simple_mode before saving
        settings.ui_mode = settings.simple_mode ? "simple" : "advanced";
        
        // Update localStorage
        localStorage.setItem("uiMode", settings.ui_mode);

        // Update settings in store
        await settingsStore.updateSettings(settings);

        // Update original settings
        originalSettings.value = cloneDeep(settings);

        showNotification("Settings saved successfully", "success");
      } catch (error) {
        console.error("Error saving settings:", error);
        showNotification("Error saving settings", "error");
      } finally {
        saving.value = false;
      }
    };

    const saveAlertSettings = async () => {
      if (!alertsFormValid.value) {
        showNotification("Please fix the errors in the form", "error");
        return;
      }

      savingAlerts.value = true;

      try {
        // Save alert settings to API
        await axios.put("/api/settings/alerts", alertSettings);

        // Update original settings
        originalAlertSettings.value = cloneDeep(alertSettings);

        showNotification("Alert settings saved successfully", "success");
      } catch (error) {
        console.error("Error saving alert settings:", error);
        showNotification("Error saving alert settings", "error");
      } finally {
        savingAlerts.value = false;
      }
    };

    const saveAdvancedSettings = async (section) => {
      savingAdvanced.value = true;

      try {
        let payload = {};

        if (section === "api") {
          payload = {
            api_enabled: advancedSettings.api_enabled,
            api_port: advancedSettings.api_port,
          };
        } else if (section === "performance") {
          payload = {
            log_level: advancedSettings.log_level,
            max_concurrent_requests: advancedSettings.max_concurrent_requests,
            request_timeout: advancedSettings.request_timeout,
            websocket_update_interval:
              advancedSettings.websocket_update_interval,
          };
        }

        // Save advanced settings to API
        await axios.put("/api/settings/advanced", payload);

        // Update original settings
        originalAdvancedSettings.value = cloneDeep(advancedSettings);

        showNotification("Advanced settings saved successfully", "success");
      } catch (error) {
        console.error("Error saving advanced settings:", error);
        showNotification("Error saving advanced settings", "error");
      } finally {
        savingAdvanced.value = false;
      }
    };

    const backupConfigDb = async () => {
      backingUpConfig.value = true;

      try {
        // Request backup from API
        const response = await axios.get("/api/system/backup/config", {
          responseType: "blob",
        });

        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute(
          "download",
          `config_backup_${new Date().toISOString().split("T")[0]}.db`,
        );
        document.body.appendChild(link);
        link.click();
        link.remove();

        showNotification("Configuration database backup created", "success");
      } catch (error) {
        console.error("Error backing up configuration database:", error);
        showNotification("Error creating backup", "error");
      } finally {
        backingUpConfig.value = false;
      }
    };

    const createFullBackup = async () => {
      creatingBackup.value = true;

      try {
        // Request full backup from API
        const response = await axios.get("/api/system/backup/full", {
          responseType: "blob",
        });

        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute(
          "download",
          `full_backup_${new Date().toISOString().split("T")[0]}.json`,
        );
        document.body.appendChild(link);
        link.click();
        link.remove();

        showNotification("Full backup created", "success");
      } catch (error) {
        console.error("Error creating full backup:", error);
        showNotification("Error creating backup", "error");
      } finally {
        creatingBackup.value = false;
      }
    };

    const restoreFromBackup = async () => {
      if (!backupFile.value) {
        showNotification("Please select a backup file", "error");
        return;
      }

      restoring.value = true;

      try {
        // Create form data
        const formData = new FormData();
        formData.append("backup_file", backupFile.value);

        // Send restore request
        await axios.post("/api/system/restore", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });

        showNotification(
          "Backup restored successfully. The application will restart.",
          "success",
        );

        // Reload the page after a short delay
        setTimeout(() => {
          window.location.reload();
        }, 3000);
      } catch (error) {
        console.error("Error restoring from backup:", error);
        showNotification("Error restoring from backup", "error");
      } finally {
        restoring.value = false;
      }
    };

    const purgeData = async () => {
      purging.value = true;

      try {
        // Send purge request
        await axios.post("/api/system/purge", {
          age: purgeAge.value,
        });

        showNotification(
          `Data older than ${purgeAge.value} purged successfully`,
          "success",
        );
        showPurgeDialog.value = false;
      } catch (error) {
        console.error("Error purging data:", error);
        showNotification("Error purging data", "error");
      } finally {
        purging.value = false;
      }
    };

    const resetApplication = async () => {
      if (resetConfirmation.value !== "RESET") return;

      resetting.value = true;

      try {
        // Reset first run state
        resetFirstRun();

        // Clear all localStorage items
        localStorage.clear();

        // Show notification
        showNotification(
          "Application reset successful. Redirecting to setup wizard...",
          "success",
        );

        // Wait a moment before redirecting
        setTimeout(() => {
          // Get router instance
          const router = useRouter();
          // Redirect to setup wizard
          router.push("/setup");
        }, 2000);
      } catch (error) {
        console.error("Error resetting application:", error);
        showNotification("Error resetting application", "error");
        resetting.value = false;
      }
    };

    const showNotification = (text, color = "success") => {
      snackbarText.value = text;
      snackbarColor.value = color;
      showSnackbar.value = true;
    };



    // Handle UI mode change
    const handleModeChange = () => {
      // Save the mode preference to localStorage for immediate effect
      const newMode = settings.simple_mode ? "simple" : "advanced";
      localStorage.setItem("uiMode", newMode);
      
      // Navigate to the appropriate dashboard based on the selected mode
      const targetRoute = settings.simple_mode ? "/dashboard-simple" : "/";
      
      // Only navigate if we're not already on the target route
      if (router.currentRoute.value.path !== targetRoute) {
        router.push(targetRoute);
      }
      
      // Show feedback to user
      showNotification(
        `Switched to ${settings.simple_mode ? 'Simple' : 'Advanced'} Mode`, 
        'success'
      );
    };

    // Watch for changes in notification method
    watch(
      () => alertSettings.notification_method,
      (newValue) => {
        // Reset specific settings when notification method changes
        if (newValue === "email") {
          alertSettings.webhook_url = "";
          alertSettings.telegram_bot_token = "";
          alertSettings.telegram_chat_id = "";
        } else if (newValue === "webhook") {
          alertSettings.email_address = "";
          alertSettings.email_frequency = "immediate";
          alertSettings.telegram_bot_token = "";
          alertSettings.telegram_chat_id = "";
        } else if (newValue === "telegram") {
          alertSettings.email_address = "";
          alertSettings.email_frequency = "immediate";
          alertSettings.webhook_url = "";
        } else {
          // Browser notifications
          alertSettings.email_address = "";
          alertSettings.email_frequency = "immediate";
          alertSettings.webhook_url = "";
          alertSettings.telegram_bot_token = "";
          alertSettings.telegram_chat_id = "";
        }
      },
    );

    // Lifecycle hooks
    onMounted(async () => {
      await loadSettings();
      await loadAlertSettings();
      await loadAdvancedSettings();
      await loadDatabaseInfo();
    });

    return {
      // Forms
      settingsForm,
      alertsForm,
      apiForm,
      perfForm,
      formValid,
      alertsFormValid,

      // Loading states
      saving,
      savingAlerts,
      savingAdvanced,
      backingUpConfig,
      creatingBackup,
      restoring,
      purging,
      resetting,

      // Settings
      settings,
      alertSettings,
      advancedSettings,
      dbInfo,

      // Backup
      backupFile,

      // Purge dialog
      showPurgeDialog,
      purgeAge,

      // Reset application
      showResetConfirmation,
      resetConfirmation,

      // Authentication removed

      // Snackbar
      showSnackbar,
      snackbarText,
      snackbarColor,

      // Options
      themeOptions,
      uiModeOptions,
      refreshIntervalOptions,
      retentionOptions,
      temperatureUnitOptions,
      defaultViewOptions,
      pollingIntervalOptions,
      notificationMethodOptions,
      emailFrequencyOptions,
      logLevelOptions,
      purgeOptions,

      // Computed
      settingsChanged,
      alertsChanged,
      apiSettingsChanged,
      perfSettingsChanged,

      // Methods
      handleModeChange,
      saveSettings,
      saveAlertSettings,
      saveAdvancedSettings,
      backupConfigDb,
      createFullBackup,
      restoreFromBackup,
      purgeData,
      resetApplication,
    };
  },
};
</script>
