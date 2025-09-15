<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <h1 class="text-h5">Alert Management</h1>
            <v-spacer></v-spacer>
            <v-btn color="primary" @click="openAlertWizard">
              <v-icon left>mdi-plus</v-icon>
              Create Alert
            </v-btn>
          </v-card-title>

          <v-card-text>
            <v-tabs v-model="activeTab">
              <v-tab>Active Alerts</v-tab>
              <v-tab>Alert History</v-tab>
              <v-tab>Templates</v-tab>
            </v-tabs>

            <v-tabs-items v-model="activeTab">
              <!-- Active Alerts Tab -->
              <v-tab-item>
                <v-card flat>
                  <v-card-text>
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-select
                          v-model="filterType"
                          :items="alertTypeOptions"
                          label="Filter by Type"
                          outlined
                          dense
                          clearable
                        ></v-select>
                      </v-col>

                      <v-col cols="12" md="4">
                        <v-select
                          v-model="filterSeverity"
                          :items="severityOptions"
                          label="Filter by Severity"
                          outlined
                          dense
                          clearable
                        ></v-select>
                      </v-col>

                      <v-col cols="12" md="4">
                        <v-text-field
                          v-model="searchQuery"
                          label="Search Alerts"
                          outlined
                          dense
                          clearable
                          append-icon="mdi-magnify"
                        ></v-text-field>
                      </v-col>
                    </v-row>

                    <v-data-table
                      :headers="alertHeaders"
                      :items="filteredAlerts"
                      :loading="loading"
                      :no-data-text="
                        loading ? 'Loading alerts...' : 'No alerts found'
                      "
                      :items-per-page="10"
                      :footer-props="{
                        'items-per-page-options': [5, 10, 15, 20, -1],
                      }"
                      class="elevation-1"
                    >
                      <!-- Name Column -->
                      <template v-slot:item.name="{ item }">
                        <div class="font-weight-medium">{{ item.name }}</div>
                      </template>

                      <!-- Type Column -->
                      <template v-slot:item.type="{ item }">
                        <v-chip small>{{ getAlertTypeName(item.type) }}</v-chip>
                      </template>

                      <!-- Condition Column -->
                      <template v-slot:item.condition="{ item }">
                        {{ getMetricName(item.conditions.metric) }}
                        {{ item.conditions.operator }}
                        {{ item.conditions.threshold
                        }}{{ getMetricUnit(item.conditions.metric) }}
                      </template>

                      <!-- Severity Column -->
                      <template v-slot:item.severity="{ item }">
                        <v-chip
                          small
                          :color="getSeverityColor(item.conditions.severity)"
                          text-color="white"
                        >
                          {{ getSeverityName(item.conditions.severity) }}
                        </v-chip>
                      </template>

                      <!-- Status Column -->
                      <template v-slot:item.enabled="{ item }">
                        <v-switch
                          v-model="item.enabled"
                          @change="toggleAlert(item)"
                          dense
                          hide-details
                          inset
                        ></v-switch>
                      </template>

                      <!-- Actions Column -->
                      <template v-slot:item.actions="{ item }">
                        <v-btn icon small @click="editAlert(item)" class="mr-2">
                          <v-icon small>mdi-pencil</v-icon>
                        </v-btn>

                        <v-btn
                          icon
                          small
                          @click="confirmDeleteAlert(item)"
                          color="error"
                        >
                          <v-icon small>mdi-delete</v-icon>
                        </v-btn>
                      </template>
                    </v-data-table>
                  </v-card-text>
                </v-card>
              </v-tab-item>

              <!-- Alert History Tab -->
              <v-tab-item>
                <v-card flat>
                  <v-card-text>
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-select
                          v-model="historyFilterType"
                          :items="alertTypeOptions"
                          label="Filter by Type"
                          outlined
                          dense
                          clearable
                        ></v-select>
                      </v-col>

                      <v-col cols="12" md="4">
                        <v-select
                          v-model="historyFilterSeverity"
                          :items="severityOptions"
                          label="Filter by Severity"
                          outlined
                          dense
                          clearable
                        ></v-select>
                      </v-col>

                      <v-col cols="12" md="4">
                        <v-menu
                          v-model="dateMenu"
                          :close-on-content-click="false"
                          transition="scale-transition"
                          offset-y
                          max-width="290px"
                          min-width="290px"
                        >
                          <template v-slot:activator="{ on, attrs }">
                            <v-text-field
                              v-model="dateRangeText"
                              label="Date Range"
                              readonly
                              outlined
                              dense
                              v-bind="attrs"
                              v-on="on"
                              clearable
                              @click:clear="clearDateRange"
                              append-icon="mdi-calendar"
                            ></v-text-field>
                          </template>
                          <v-date-picker
                            v-model="dateRange"
                            range
                            no-title
                            scrollable
                          >
                            <v-spacer></v-spacer>
                            <v-btn
                              text
                              color="primary"
                              @click="dateMenu = false"
                            >
                              OK
                            </v-btn>
                          </v-date-picker>
                        </v-menu>
                      </v-col>
                    </v-row>

                    <v-data-table
                      :headers="historyHeaders"
                      :items="alertHistory"
                      :loading="loading"
                      :no-data-text="
                        loading
                          ? 'Loading alert history...'
                          : 'No alert history found'
                      "
                      :items-per-page="10"
                      :footer-props="{
                        'items-per-page-options': [5, 10, 15, 20, -1],
                      }"
                      class="elevation-1"
                    >
                      <!-- Alert Name Column -->
                      <template v-slot:item.alert_name="{ item }">
                        <div class="font-weight-medium">
                          {{ item.alert_name }}
                        </div>
                      </template>

                      <!-- Timestamp Column -->
                      <template v-slot:item.timestamp="{ item }">
                        {{ formatDate(item.timestamp) }}
                      </template>

                      <!-- Severity Column -->
                      <template v-slot:item.severity="{ item }">
                        <v-chip
                          small
                          :color="getSeverityColor(item.severity)"
                          text-color="white"
                        >
                          {{ getSeverityName(item.severity) }}
                        </v-chip>
                      </template>

                      <!-- Status Column -->
                      <template v-slot:item.status="{ item }">
                        <v-chip
                          small
                          :color="
                            item.status === 'triggered' ? 'error' : 'success'
                          "
                          text-color="white"
                        >
                          {{
                            item.status === "triggered"
                              ? "Triggered"
                              : "Resolved"
                          }}
                        </v-chip>
                      </template>

                      <!-- Actions Column -->
                      <template v-slot:item.actions="{ item }">
                        <v-btn icon small @click="viewAlertDetails(item)">
                          <v-icon small>mdi-information</v-icon>
                        </v-btn>
                      </template>
                    </v-data-table>
                  </v-card-text>
                </v-card>
              </v-tab-item>

              <!-- Templates Tab -->
              <v-tab-item>
                <v-card flat>
                  <v-card-text>
                    <v-data-table
                      :headers="templateHeaders"
                      :items="alertTemplates"
                      :loading="loading"
                      :no-data-text="
                        loading ? 'Loading templates...' : 'No templates found'
                      "
                      :items-per-page="10"
                      :footer-props="{
                        'items-per-page-options': [5, 10, 15, 20, -1],
                      }"
                      class="elevation-1"
                    >
                      <!-- Name Column -->
                      <template v-slot:item.name="{ item }">
                        <div class="font-weight-medium">{{ item.name }}</div>
                      </template>

                      <!-- Type Column -->
                      <template v-slot:item.type="{ item }">
                        <v-chip small>{{ getAlertTypeName(item.type) }}</v-chip>
                      </template>

                      <!-- Condition Column -->
                      <template v-slot:item.condition="{ item }">
                        {{ getMetricName(item.conditions.metric) }}
                        {{ item.conditions.operator }}
                        {{ item.conditions.threshold
                        }}{{ getMetricUnit(item.conditions.metric) }}
                      </template>

                      <!-- Actions Column -->
                      <template v-slot:item.actions="{ item }">
                        <v-btn
                          icon
                          small
                          @click="useTemplate(item)"
                          class="mr-2"
                          color="primary"
                        >
                          <v-icon small>mdi-plus-circle</v-icon>
                        </v-btn>

                        <v-btn
                          icon
                          small
                          @click="confirmDeleteTemplate(item)"
                          color="error"
                        >
                          <v-icon small>mdi-delete</v-icon>
                        </v-btn>
                      </template>
                    </v-data-table>
                  </v-card-text>
                </v-card>
              </v-tab-item>
            </v-tabs-items>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Alert Config Wizard Dialog -->
    <alert-config-wizard
      v-model="showAlertWizard"
      :edit-alert="editAlertData"
      @config-complete="onAlertConfigComplete"
      @save-template="saveAlertTemplate"
    ></alert-config-wizard>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title class="headline">Confirm Deletion</v-card-title>
        <v-card-text>
          Are you sure you want to delete this {{ deleteType }}?
          <div v-if="deleteType === 'alert'" class="font-weight-medium mt-2">
            {{ deleteItem?.name }}
          </div>
          <div v-else class="font-weight-medium mt-2">
            {{ deleteItem?.name }}
          </div>
          <div class="red--text mt-2">This action cannot be undone.</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showDeleteDialog = false"> Cancel </v-btn>
          <v-btn color="error" @click="confirmDelete"> Delete </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Alert Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="600">
      <v-card v-if="selectedAlertHistory">
        <v-card-title
          :class="
            selectedAlertHistory.status === 'triggered'
              ? 'error white--text'
              : 'success white--text'
          "
        >
          {{
            selectedAlertHistory.status === "triggered"
              ? "Alert Triggered"
              : "Alert Resolved"
          }}
        </v-card-title>
        <v-card-text class="pt-4">
          <v-row>
            <v-col cols="12" md="6">
              <div class="text-subtitle-2">Alert Name</div>
              <div>{{ selectedAlertHistory.alert_name }}</div>
            </v-col>
            <v-col cols="12" md="6">
              <div class="text-subtitle-2">Timestamp</div>
              <div>{{ formatDate(selectedAlertHistory.timestamp) }}</div>
            </v-col>
          </v-row>

          <v-row class="mt-2">
            <v-col cols="12" md="6">
              <div class="text-subtitle-2">Severity</div>
              <v-chip
                small
                :color="getSeverityColor(selectedAlertHistory.severity)"
                text-color="white"
              >
                {{ getSeverityName(selectedAlertHistory.severity) }}
              </v-chip>
            </v-col>
            <v-col cols="12" md="6">
              <div class="text-subtitle-2">Status</div>
              <v-chip
                small
                :color="
                  selectedAlertHistory.status === 'triggered'
                    ? 'error'
                    : 'success'
                "
                text-color="white"
              >
                {{
                  selectedAlertHistory.status === "triggered"
                    ? "Triggered"
                    : "Resolved"
                }}
              </v-chip>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <div class="text-subtitle-2">Condition</div>
          <div>
            {{ selectedAlertHistory.metric_name }}
            {{ selectedAlertHistory.operator }}
            {{ selectedAlertHistory.threshold }}{{ selectedAlertHistory.unit }}
          </div>

          <div class="text-subtitle-2 mt-4">Actual Value</div>
          <div>
            {{ selectedAlertHistory.actual_value
            }}{{ selectedAlertHistory.unit }}
          </div>

          <div v-if="selectedAlertHistory.message" class="mt-4">
            <div class="text-subtitle-2">Message</div>
            <div>{{ selectedAlertHistory.message }}</div>
          </div>

          <div v-if="selectedAlertHistory.miner_name" class="mt-4">
            <div class="text-subtitle-2">Miner</div>
            <div>{{ selectedAlertHistory.miner_name }}</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showDetailsDialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useAlertsStore } from "../../stores/alerts";
import AlertConfigWizard from "./AlertConfigWizard.vue";

export default {
  name: "AlertsManagement",

  components: {
    AlertConfigWizard,
  },

  setup() {
    const alertsStore = useAlertsStore();

    // State
    const activeTab = ref(0);
    const filterType = ref(null);
    const filterSeverity = ref(null);
    const searchQuery = ref("");
    const historyFilterType = ref(null);
    const historyFilterSeverity = ref(null);
    const dateRange = ref([]);
    const dateMenu = ref(false);
    const showAlertWizard = ref(false);
    const editAlertData = ref(null);
    const showDeleteDialog = ref(false);
    const deleteType = ref("");
    const deleteItem = ref(null);
    const showDetailsDialog = ref(false);
    const selectedAlertHistory = ref(null);

    // Mock alert history data (would come from API in real app)
    const alertHistory = ref([
      {
        id: 1,
        alert_id: "alert-1",
        alert_name: "High Temperature Alert",
        timestamp: "2025-08-26T12:30:45Z",
        severity: "high",
        status: "triggered",
        metric_name: "Temperature",
        operator: ">",
        threshold: 80,
        actual_value: 85,
        unit: "°C",
        message: "Temperature exceeded threshold",
        miner_name: "Bitaxe-01",
      },
      {
        id: 2,
        alert_id: "alert-1",
        alert_name: "High Temperature Alert",
        timestamp: "2025-08-26T13:15:22Z",
        severity: "high",
        status: "resolved",
        metric_name: "Temperature",
        operator: ">",
        threshold: 80,
        actual_value: 75,
        unit: "°C",
        message: "Temperature returned to normal",
        miner_name: "Bitaxe-01",
      },
      {
        id: 3,
        alert_id: "alert-2",
        alert_name: "Low Hashrate Alert",
        timestamp: "2025-08-25T18:45:12Z",
        severity: "medium",
        status: "triggered",
        metric_name: "Hashrate",
        operator: "<",
        threshold: 10,
        actual_value: 8.5,
        unit: " TH/s",
        message: "Hashrate dropped below threshold",
        miner_name: "Avalon-02",
      },
    ]);

    // Headers for data tables
    const alertHeaders = [
      { text: "Name", value: "name" },
      { text: "Type", value: "type" },
      { text: "Condition", value: "condition" },
      { text: "Severity", value: "severity" },
      { text: "Enabled", value: "enabled" },
      { text: "Actions", value: "actions", sortable: false },
    ];

    const historyHeaders = [
      { text: "Alert Name", value: "alert_name" },
      { text: "Timestamp", value: "timestamp" },
      { text: "Severity", value: "severity" },
      { text: "Status", value: "status" },
      { text: "Miner", value: "miner_name" },
      { text: "Actions", value: "actions", sortable: false },
    ];

    const templateHeaders = [
      { text: "Name", value: "name" },
      { text: "Type", value: "type" },
      { text: "Condition", value: "condition" },
      { text: "Actions", value: "actions", sortable: false },
    ];

    // Options for filters
    const alertTypeOptions = [
      { text: "Performance", value: "performance" },
      { text: "Connectivity", value: "connectivity" },
      { text: "Temperature", value: "temperature" },
      { text: "Profitability", value: "profitability" },
      { text: "System", value: "system" },
    ];

    const severityOptions = [
      { text: "Low", value: "low" },
      { text: "Medium", value: "medium" },
      { text: "High", value: "high" },
      { text: "Critical", value: "critical" },
    ];

    // Computed properties
    const loading = computed(() => alertsStore.loading);

    const filteredAlerts = computed(() => {
      let result = [...alertsStore.alerts];

      // Apply type filter
      if (filterType.value) {
        result = result.filter((alert) => alert.type === filterType.value);
      }

      // Apply severity filter
      if (filterSeverity.value) {
        result = result.filter(
          (alert) => alert.conditions.severity === filterSeverity.value,
        );
      }

      // Apply search query
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase();
        result = result.filter(
          (alert) =>
            alert.name.toLowerCase().includes(query) ||
            getMetricName(alert.conditions.metric)
              .toLowerCase()
              .includes(query),
        );
      }

      return result;
    });

    const alertTemplates = computed(() => alertsStore.alertTemplates);

    const dateRangeText = computed(() => {
      if (dateRange.value.length === 2) {
        return `${dateRange.value[0]} to ${dateRange.value[1]}`;
      }
      return "";
    });

    // Methods
    const getAlertTypeName = (type) => {
      switch (type) {
        case "performance":
          return "Performance";
        case "connectivity":
          return "Connectivity";
        case "temperature":
          return "Temperature";
        case "profitability":
          return "Profitability";
        case "system":
          return "System";
        default:
          return type;
      }
    };

    const getMetricName = (metric) => {
      if (!metric) return "";

      return metric
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
    };

    const getMetricUnit = (metric) => {
      if (!metric) return "";

      switch (metric) {
        case "hashrate":
          return " TH/s";
        case "temperature":
          return "°C";
        case "fan_speed":
          return "%";
        case "power_consumption":
          return "W";
        case "earnings":
        case "earnings_per_th":
        case "power_cost":
          return " BTC";
        case "profit_margin":
        case "efficiency":
        case "cpu_usage":
        case "memory_usage":
        case "disk_usage":
          return "%";
        case "uptime":
          return " minutes";
        case "response_time":
          return " ms";
        default:
          return "";
      }
    };

    const getSeverityName = (severity) => {
      switch (severity) {
        case "low":
          return "Low";
        case "medium":
          return "Medium";
        case "high":
          return "High";
        case "critical":
          return "Critical";
        default:
          return severity;
      }
    };

    const getSeverityColor = (severity) => {
      switch (severity) {
        case "low":
          return "info";
        case "medium":
          return "warning";
        case "high":
          return "error";
        case "critical":
          return "deep-purple darken-2";
        default:
          return "primary";
      }
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(date);
    };

    const clearDateRange = () => {
      dateRange.value = [];
    };

    const openAlertWizard = () => {
      editAlertData.value = null;
      showAlertWizard.value = true;
    };

    const editAlert = (alert) => {
      editAlertData.value = alert;
      showAlertWizard.value = true;
    };

    const onAlertConfigComplete = () => {
      // Refresh alerts after configuration is complete
      alertsStore.fetchAlerts();
    };

    const toggleAlert = async (alert) => {
      try {
        await alertsStore.toggleAlertStatus(alert.id, alert.enabled);
      } catch (error) {
        console.error("Error toggling alert status:", error);
        // Revert the toggle if there was an error
        alert.enabled = !alert.enabled;
      }
    };

    const confirmDeleteAlert = (alert) => {
      deleteType.value = "alert";
      deleteItem.value = alert;
      showDeleteDialog.value = true;
    };

    const confirmDeleteTemplate = (template) => {
      deleteType.value = "template";
      deleteItem.value = template;
      showDeleteDialog.value = true;
    };

    const confirmDelete = async () => {
      try {
        if (deleteType.value === "alert") {
          await alertsStore.removeAlert(deleteItem.value.id);
        } else if (deleteType.value === "template") {
          await alertsStore.removeAlertTemplate(deleteItem.value.id);
        }
      } catch (error) {
        console.error(`Error deleting ${deleteType.value}:`, error);
      } finally {
        showDeleteDialog.value = false;
        deleteItem.value = null;
      }
    };

    const viewAlertDetails = (alertHistoryItem) => {
      selectedAlertHistory.value = alertHistoryItem;
      showDetailsDialog.value = true;
    };

    const useTemplate = (template) => {
      // Create a new alert from the template
      const newAlert = {
        name: `${template.name} Alert`,
        type: template.type,
        miners: ["all"],
        conditions: { ...template.conditions },
        notifications: {
          methods: ["app"],
          frequency: "once",
          quiet_hours: {
            enabled: false,
            start: "22:00",
            end: "08:00",
          },
        },
        enabled: true,
        use_template: true,
        template_id: template.id,
      };

      // Open the alert wizard with the template data
      editAlertData.value = newAlert;
      showAlertWizard.value = true;
    };

    const saveAlertTemplate = async (template) => {
      try {
        await alertsStore.addAlertTemplate(template);
      } catch (error) {
        console.error("Error saving alert template:", error);
      }
    };

    // Lifecycle hooks
    onMounted(() => {
      // Fetch alerts and templates
      alertsStore.fetchAlerts();
      alertsStore.fetchAlertTemplates();
    });

    return {
      // State
      activeTab,
      filterType,
      filterSeverity,
      searchQuery,
      historyFilterType,
      historyFilterSeverity,
      dateRange,
      dateMenu,
      showAlertWizard,
      editAlertData,
      showDeleteDialog,
      deleteType,
      deleteItem,
      showDetailsDialog,
      selectedAlertHistory,
      alertHistory,

      // Computed
      loading,
      filteredAlerts,
      alertTemplates,
      dateRangeText,

      // Data
      alertHeaders,
      historyHeaders,
      templateHeaders,
      alertTypeOptions,
      severityOptions,

      // Methods
      getAlertTypeName,
      getMetricName,
      getMetricUnit,
      getSeverityName,
      getSeverityColor,
      formatDate,
      clearDateRange,
      openAlertWizard,
      editAlert,
      onAlertConfigComplete,
      toggleAlert,
      confirmDeleteAlert,
      confirmDeleteTemplate,
      confirmDelete,
      viewAlertDetails,
      useTemplate,
      saveAlertTemplate,
    };
  },
};
</script>
