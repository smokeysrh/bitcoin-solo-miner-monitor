<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Set Alert Conditions</h2>
            <p class="text-body-1 mb-6">
              Define when this alert should be triggered.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="primary">mdi-tune</v-icon>
                Alert Conditions
              </v-card-title>
              <v-card-text>
                <v-form ref="conditionsForm" v-model="isFormValid">
                  <v-row>
                    <v-col cols="12" md="4">
                      <v-select
                        v-model="conditions.metric"
                        :items="availableMetrics"
                        label="Metric"
                        outlined
                        :rules="[(v) => !!v || 'Metric is required']"
                      ></v-select>
                    </v-col>

                    <v-col cols="12" md="4">
                      <v-select
                        v-model="conditions.operator"
                        :items="operators"
                        item-text="text"
                        item-value="value"
                        label="Operator"
                        outlined
                        :rules="[(v) => !!v || 'Operator is required']"
                      ></v-select>
                    </v-col>

                    <v-col cols="12" md="4">
                      <v-text-field
                        v-model="conditions.threshold"
                        :label="`Threshold ${getMetricUnit}`"
                        type="number"
                        outlined
                        :rules="[
                          (v) =>
                            (v !== null && v !== '') || 'Threshold is required',
                        ]"
                      ></v-text-field>
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col cols="12" md="6">
                      <v-select
                        v-model="conditions.duration"
                        :items="durations"
                        item-text="text"
                        item-value="value"
                        label="Duration"
                        outlined
                        hint="How long the condition must persist before triggering"
                        persistent-hint
                      ></v-select>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-select
                        v-model="conditions.severity"
                        :items="severities"
                        item-text="text"
                        item-value="value"
                        label="Severity"
                        outlined
                        hint="How important this alert is"
                        persistent-hint
                      >
                        <template v-slot:selection="{ item }">
                          <v-chip
                            :color="getSeverityColor(item.value)"
                            text-color="white"
                            small
                          >
                            {{ item.text }}
                          </v-chip>
                        </template>
                        <template v-slot:item="{ item }">
                          <v-chip
                            :color="getSeverityColor(item.value)"
                            text-color="white"
                            small
                            class="mr-2"
                          >
                            {{ item.text }}
                          </v-chip>
                          {{ item.description }}
                        </template>
                      </v-select>
                    </v-col>
                  </v-row>
                </v-form>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row class="mt-4">
          <v-col cols="12">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="primary">mdi-text-box-outline</v-icon>
                Alert Details
              </v-card-title>
              <v-card-text>
                <v-text-field
                  v-model="alertName"
                  label="Alert Name (Optional)"
                  outlined
                  hint="Leave blank for auto-generated name"
                  persistent-hint
                ></v-text-field>

                <v-textarea
                  v-model="alertDescription"
                  label="Description (Optional)"
                  outlined
                  hint="Additional information about this alert"
                  persistent-hint
                  class="mt-4"
                  rows="2"
                  auto-grow
                ></v-textarea>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="showPreview" class="mt-4">
          <v-col cols="12">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="primary">mdi-eye</v-icon>
                Alert Preview
              </v-card-title>
              <v-card-text>
                <v-alert
                  :color="getSeverityColor(conditions.severity)"
                  border="left"
                  dark
                >
                  <div class="text-h6">{{ previewName }}</div>
                  <div>
                    This alert will trigger when
                    <strong>{{ getMetricName }}</strong>
                    is {{ getOperatorText }}
                    <strong
                      >{{ conditions.threshold }}{{ getMetricUnit }}</strong
                    >
                    {{ getDurationText }}.
                  </div>
                </v-alert>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="showHelp" class="mt-4">
          <v-col cols="12">
            <v-alert type="info" outlined>
              <h3 class="text-subtitle-1 font-weight-bold">
                Setting Alert Conditions
              </h3>
              <p class="mb-0">
                Choose a metric to monitor, an operator (like greater than or
                less than), and a threshold value. You can also set how long the
                condition must persist before triggering an alert and the
                severity level.
              </p>
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed, watch } from "vue";

export default {
  name: "AlertConditions",

  props: {
    alertData: {
      type: Object,
      required: true,
    },

    showHelp: {
      type: Boolean,
      default: true,
    },

    showPreview: {
      type: Boolean,
      default: true,
    },
  },

  setup(props, { emit }) {
    // State
    const isFormValid = ref(false);
    const alertName = ref(props.alertData.name || "");
    const alertDescription = ref(props.alertData.description || "");
    const conditions = ref({
      metric: props.alertData.conditions?.metric || "",
      operator: props.alertData.conditions?.operator || ">",
      threshold:
        props.alertData.conditions?.threshold !== undefined
          ? props.alertData.conditions.threshold
          : null,
      duration:
        props.alertData.conditions?.duration !== undefined
          ? props.alertData.conditions.duration
          : 0,
      severity: props.alertData.conditions?.severity || "medium",
    });

    // Computed properties
    const availableMetrics = computed(() => {
      const baseMetrics = [];

      switch (props.alertData.type) {
        case "performance":
          baseMetrics.push(
            "hashrate",
            "accepted_shares",
            "rejected_shares",
            "hardware_errors",
            "efficiency",
          );
          break;
        case "connectivity":
          baseMetrics.push(
            "status",
            "uptime",
            "connection_errors",
            "response_time",
          );
          break;
        case "temperature":
          baseMetrics.push("temperature", "fan_speed", "power_consumption");
          break;
        case "profitability":
          baseMetrics.push(
            "earnings",
            "earnings_per_th",
            "power_cost",
            "profit_margin",
          );
          break;
        case "system":
          baseMetrics.push(
            "cpu_usage",
            "memory_usage",
            "disk_usage",
            "network_traffic",
          );
          break;
      }

      return baseMetrics;
    });

    const operators = [
      { text: "Greater than (>)", value: ">" },
      { text: "Less than (<)", value: "<" },
      { text: "Greater than or equal to (≥)", value: ">=" },
      { text: "Less than or equal to (≤)", value: "<=" },
      { text: "Equal to (=)", value: "==" },
      { text: "Not equal to (≠)", value: "!=" },
    ];

    const durations = [
      { text: "Immediately", value: 0 },
      { text: "1 minute", value: 1 },
      { text: "5 minutes", value: 5 },
      { text: "15 minutes", value: 15 },
      { text: "30 minutes", value: 30 },
      { text: "1 hour", value: 60 },
      { text: "2 hours", value: 120 },
      { text: "6 hours", value: 360 },
      { text: "12 hours", value: 720 },
      { text: "24 hours", value: 1440 },
    ];

    const severities = [
      {
        text: "Low",
        value: "low",
        description: "Informational alerts that don't require immediate action",
      },
      {
        text: "Medium",
        value: "medium",
        description: "Important alerts that should be addressed soon",
      },
      {
        text: "High",
        value: "high",
        description: "Urgent alerts that require prompt attention",
      },
      {
        text: "Critical",
        value: "critical",
        description: "Severe issues that need immediate action",
      },
    ];

    const getMetricName = computed(() => {
      const metric = conditions.value.metric;
      if (!metric) return "";

      return metric
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
    });

    const getMetricUnit = computed(() => {
      const metric = conditions.value.metric;
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
    });

    const getOperatorText = computed(() => {
      switch (conditions.value.operator) {
        case ">":
          return "greater than";
        case "<":
          return "less than";
        case ">=":
          return "greater than or equal to";
        case "<=":
          return "less than or equal to";
        case "==":
          return "equal to";
        case "!=":
          return "not equal to";
        default:
          return conditions.value.operator;
      }
    });

    const getDurationText = computed(() => {
      const duration = conditions.value.duration;
      if (duration === 0) return "at any time";
      if (duration === 1) return "for 1 minute";
      if (duration < 60) return `for ${duration} minutes`;
      if (duration === 60) return "for 1 hour";
      if (duration < 1440) return `for ${duration / 60} hours`;
      return "for 24 hours";
    });

    const previewName = computed(() => {
      if (alertName.value) return alertName.value;

      return `${getMetricName.value} ${conditions.value.operator} ${conditions.value.threshold}${getMetricUnit.value}`;
    });

    // Methods
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

    // Watch for changes
    watch(
      [conditions, alertName, alertDescription],
      () => {
        emit("update-conditions", {
          ...conditions.value,
          name: alertName.value,
          description: alertDescription.value,
        });
      },
      { deep: true },
    );

    return {
      isFormValid,
      alertName,
      alertDescription,
      conditions,
      availableMetrics,
      operators,
      durations,
      severities,
      getMetricName,
      getMetricUnit,
      getOperatorText,
      getDurationText,
      previewName,
      getSeverityColor,
    };
  },
};
</script>
