<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Alert Summary</h2>
            <p class="text-body-1 mb-6">
              Review your alert configuration before saving.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12" md="6">
            <v-card outlined class="mb-4">
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-information-outline</v-icon>
                Alert Details
              </v-card-title>
              <v-card-text>
                <v-list dense>
                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Name</v-list-item-subtitle
                      >
                      <v-list-item-title>{{ displayName }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Type</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        getAlertTypeName
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Applies To</v-list-item-subtitle
                      >
                      <v-list-item-title>{{ getMinersText }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider v-if="alertData.description"></v-divider>

                  <v-list-item v-if="alertData.description">
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Description</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        alertData.description
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>

            <v-card outlined>
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-bell-outline</v-icon>
                Notification Settings
              </v-card-title>
              <v-card-text>
                <v-list dense>
                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Methods</v-list-item-subtitle
                      >
                      <v-list-item-title>
                        <v-chip
                          v-for="method in alertData.notifications.methods"
                          :key="method"
                          small
                          class="mr-1"
                        >
                          {{ getMethodName(method) }}
                        </v-chip>
                      </v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Frequency</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        getFrequencyName
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider
                    v-if="alertData.notifications.quiet_hours.enabled"
                  ></v-divider>

                  <v-list-item
                    v-if="alertData.notifications.quiet_hours.enabled"
                  >
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Quiet Hours</v-list-item-subtitle
                      >
                      <v-list-item-title>
                        {{ alertData.notifications.quiet_hours.start }} -
                        {{ alertData.notifications.quiet_hours.end }}
                      </v-list-item-title>
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
                Alert Conditions
              </v-card-title>
              <v-card-text>
                <v-alert
                  :color="getSeverityColor(alertData.conditions.severity)"
                  border="left"
                  dark
                >
                  <div>
                    Alert will trigger when
                    <strong>{{ getMetricName }}</strong>
                    is {{ getOperatorText }}
                    <strong
                      >{{ alertData.conditions.threshold
                      }}{{ getMetricUnit }}</strong
                    >
                    {{ getDurationText }}.
                  </div>
                </v-alert>

                <v-list dense class="mt-4">
                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Metric</v-list-item-subtitle
                      >
                      <v-list-item-title>{{ getMetricName }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Condition</v-list-item-subtitle
                      >
                      <v-list-item-title>
                        {{ getOperatorText }} {{ alertData.conditions.threshold
                        }}{{ getMetricUnit }}
                      </v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Duration</v-list-item-subtitle
                      >
                      <v-list-item-title>{{
                        getDurationText
                      }}</v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>

                  <v-divider></v-divider>

                  <v-list-item>
                    <v-list-item-content>
                      <v-list-item-subtitle class="text-caption"
                        >Severity</v-list-item-subtitle
                      >
                      <v-list-item-title>
                        <v-chip
                          :color="
                            getSeverityColor(alertData.conditions.severity)
                          "
                          text-color="white"
                          small
                        >
                          {{ getSeverityName }}
                        </v-chip>
                      </v-list-item-title>
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>

            <v-card outlined>
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-content-save-outline</v-icon>
                Save as Template
              </v-card-title>
              <v-card-text>
                <p class="text-body-2 mb-4">
                  Save these settings as a template for future alerts.
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
import { ref, computed } from "vue";
import { useMinersStore } from "../../stores/miners";

export default {
  name: "AlertSummary",

  props: {
    alertData: {
      type: Object,
      required: true,
    },

    isEditMode: {
      type: Boolean,
      default: false,
    },
  },

  setup(props, { emit }) {
    const minersStore = useMinersStore();

    // State
    const templateName = ref(
      props.isEditMode
        ? `${props.alertData.name} Template`
        : "My Alert Template",
    );

    // Computed properties
    const displayName = computed(() => {
      if (props.alertData.name) return props.alertData.name;

      const metricName = getMetricName.value;
      const operator = getOperatorText.value;
      const threshold = props.alertData.conditions.threshold;
      const unit = getMetricUnit.value;

      return `${metricName} ${operator} ${threshold}${unit}`;
    });

    const getAlertTypeName = computed(() => {
      switch (props.alertData.type) {
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
          return props.alertData.type;
      }
    });

    const getMinersText = computed(() => {
      if (props.alertData.type === "system") {
        return "System-wide";
      }

      if (
        props.alertData.miners.length === 1 &&
        props.alertData.miners[0] === "all"
      ) {
        return "All Miners";
      }

      if (props.alertData.miners.length === 0) {
        return "No miners selected";
      }

      if (props.alertData.miners.length <= 3) {
        return props.alertData.miners
          .map((id) => {
            const miner = minersStore.miners.find((m) => m.id === id);
            return miner ? miner.name : id;
          })
          .join(", ");
      }

      return `${props.alertData.miners.length} miners selected`;
    });

    const getMetricName = computed(() => {
      const metric = props.alertData.conditions.metric;
      if (!metric) return "";

      return metric
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
    });

    const getMetricUnit = computed(() => {
      const metric = props.alertData.conditions.metric;
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
      switch (props.alertData.conditions.operator) {
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
          return props.alertData.conditions.operator;
      }
    });

    const getDurationText = computed(() => {
      const duration = props.alertData.conditions.duration;
      if (duration === 0) return "at any time";
      if (duration === 1) return "for 1 minute";
      if (duration < 60) return `for ${duration} minutes`;
      if (duration === 60) return "for 1 hour";
      if (duration < 1440) return `for ${duration / 60} hours`;
      return "for 24 hours";
    });

    const getSeverityName = computed(() => {
      switch (props.alertData.conditions.severity) {
        case "low":
          return "Low";
        case "medium":
          return "Medium";
        case "high":
          return "High";
        case "critical":
          return "Critical";
        default:
          return props.alertData.conditions.severity;
      }
    });

    const getFrequencyName = computed(() => {
      switch (props.alertData.notifications.frequency) {
        case "once":
          return "Once";
        case "every_occurrence":
          return "Every Occurrence";
        case "hourly":
          return "Hourly Summary";
        case "daily":
          return "Daily Summary";
        default:
          return props.alertData.notifications.frequency;
      }
    });

    // Methods
    const getMethodName = (method) => {
      switch (method) {
        case "app":
          return "In-App";
        case "email":
          return "Email";
        case "sms":
          return "SMS";
        case "webhook":
          return "Webhook";
        default:
          return method;
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

    const saveTemplate = () => {
      if (!templateName.value) return;

      // Emit event to parent component to save template
      emit("save-as-template", templateName.value);

      // Show success message
      alert("Template saved successfully");
    };

    return {
      templateName,
      displayName,
      getAlertTypeName,
      getMinersText,
      getMetricName,
      getMetricUnit,
      getOperatorText,
      getDurationText,
      getSeverityName,
      getFrequencyName,
      getMethodName,
      getSeverityColor,
      saveTemplate,
    };
  },
};
</script>
