<template>
  <v-dialog v-model="show" persistent max-width="800px" scrollable>
    <v-card>
      <v-card-title class="primary white--text">
        <span class="text-h5">{{
          isEditMode ? "Edit Alert" : "Create New Alert"
        }}</span>
        <v-spacer></v-spacer>
        <v-btn icon dark @click="closeWizard" v-if="allowClose">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-stepper v-model="currentStep" class="elevation-0">
        <!-- Stepper Header -->
        <v-stepper-header>
          <v-stepper-step :complete="currentStep > 1" step="1">
            Alert Type
          </v-stepper-step>

          <v-divider></v-divider>

          <v-stepper-step :complete="currentStep > 2" step="2">
            Conditions
          </v-stepper-step>

          <v-divider></v-divider>

          <v-stepper-step :complete="currentStep > 3" step="3">
            Notifications
          </v-stepper-step>

          <v-divider></v-divider>

          <v-stepper-step step="4"> Summary </v-stepper-step>
        </v-stepper-header>

        <!-- Stepper Content -->
        <v-stepper-items>
          <!-- Step 1: Alert Type Selection -->
          <v-stepper-content step="1">
            <alert-type-selection
              :selected-type="alertData.type"
              :initial-selected-miners="alertData.miners"
              @type-selected="setAlertType"
              @miners-selected="setSelectedMiners"
            ></alert-type-selection>

            <v-divider class="my-4"></v-divider>

            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn text @click="closeWizard" :disabled="!allowClose">
                Cancel
              </v-btn>
              <v-btn
                color="primary"
                @click="nextStep"
                :disabled="
                  !alertData.type ||
                  (alertData.type !== 'system' && alertData.miners.length === 0)
                "
              >
                Continue
                <v-icon right>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-stepper-content>

          <!-- Step 2: Alert Conditions -->
          <v-stepper-content step="2">
            <alert-conditions
              :alert-data="alertData"
              @update-conditions="updateConditions"
            ></alert-conditions>

            <v-divider class="my-4"></v-divider>

            <v-card-actions>
              <v-btn text @click="prevStep">
                <v-icon left>mdi-arrow-left</v-icon>
                Back
              </v-btn>
              <v-spacer></v-spacer>
              <v-btn text @click="closeWizard" :disabled="!allowClose">
                Cancel
              </v-btn>
              <v-btn
                color="primary"
                @click="nextStep"
                :disabled="!isConditionsValid"
              >
                Continue
                <v-icon right>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-stepper-content>

          <!-- Step 3: Notification Settings -->
          <v-stepper-content step="3">
            <alert-notifications
              :alert-data="alertData"
              @update-notifications="updateNotifications"
            ></alert-notifications>

            <v-divider class="my-4"></v-divider>

            <v-card-actions>
              <v-btn text @click="prevStep">
                <v-icon left>mdi-arrow-left</v-icon>
                Back
              </v-btn>
              <v-spacer></v-spacer>
              <v-btn text @click="closeWizard" :disabled="!allowClose">
                Cancel
              </v-btn>
              <v-btn
                color="primary"
                @click="nextStep"
                :disabled="!isNotificationsValid"
              >
                Continue
                <v-icon right>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-stepper-content>

          <!-- Step 4: Summary -->
          <v-stepper-content step="4">
            <alert-summary
              :alert-data="alertData"
              :is-edit-mode="isEditMode"
              @save-as-template="saveAsTemplate"
            ></alert-summary>

            <v-divider class="my-4"></v-divider>

            <v-card-actions>
              <v-btn text @click="prevStep">
                <v-icon left>mdi-arrow-left</v-icon>
                Back
              </v-btn>
              <v-spacer></v-spacer>
              <v-btn text @click="closeWizard" :disabled="!allowClose">
                Cancel
              </v-btn>
              <v-btn color="success" @click="saveAlert" :loading="isSaving">
                {{ isEditMode ? "Update Alert" : "Create Alert" }}
                <v-icon right>mdi-check</v-icon>
              </v-btn>
            </v-card-actions>
          </v-stepper-content>
        </v-stepper-items>
      </v-stepper>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from "vue";
import { useAlertsStore } from "../../stores/alerts";
import AlertTypeSelection from "./AlertTypeSelection.vue";
import AlertConditions from "./AlertConditions.vue";
import AlertNotifications from "./AlertNotifications.vue";
import AlertSummary from "./AlertSummary.vue";

export default {
  name: "AlertConfigWizard",

  components: {
    AlertTypeSelection,
    AlertConditions,
    AlertNotifications,
    AlertSummary,
  },

  props: {
    value: {
      type: Boolean,
      default: false,
    },

    allowClose: {
      type: Boolean,
      default: true,
    },

    editAlert: {
      type: Object,
      default: null,
    },
  },

  setup(props, { emit }) {
    const alertsStore = useAlertsStore();

    // State
    const currentStep = ref(1);
    const isSaving = ref(false);

    // Alert data
    const alertData = ref({
      id: null,
      name: "",
      type: "", // 'performance', 'connectivity', 'temperature', 'profitability', 'system'
      miners: [], // Array of miner IDs or 'all'
      conditions: {
        metric: "", // 'hashrate', 'temperature', 'accepted_shares', 'rejected_shares', 'uptime', etc.
        operator: "", // '>', '<', '>=', '<=', '==', '!='
        threshold: null,
        duration: 0, // Duration in minutes, 0 means immediate
        severity: "medium", // 'low', 'medium', 'high', 'critical'
      },
      notifications: {
        methods: [], // 'app', 'email', 'sms', 'webhook'
        email: "",
        phone: "",
        webhook_url: "",
        frequency: "once", // 'once', 'every_occurrence', 'hourly', 'daily'
        quiet_hours: {
          enabled: false,
          start: "22:00",
          end: "08:00",
        },
      },
      enabled: true,
      use_template: false,
      template_id: null,
    });

    // Computed properties
    const show = computed({
      get: () => props.value,
      set: (value) => emit("input", value),
    });

    const isEditMode = computed(() => !!props.editAlert);

    const isConditionsValid = computed(() => {
      const conditions = alertData.value.conditions;
      return (
        conditions.metric &&
        conditions.operator &&
        conditions.threshold !== null
      );
    });

    const isNotificationsValid = computed(() => {
      const notifications = alertData.value.notifications;

      if (notifications.methods.length === 0) {
        return false;
      }

      if (notifications.methods.includes("email") && !notifications.email) {
        return false;
      }

      if (notifications.methods.includes("sms") && !notifications.phone) {
        return false;
      }

      if (
        notifications.methods.includes("webhook") &&
        !notifications.webhook_url
      ) {
        return false;
      }

      return true;
    });

    // Methods
    const setAlertType = (type) => {
      alertData.value.type = type;

      // Set default metric based on alert type
      switch (type) {
        case "performance":
          alertData.value.conditions.metric = "hashrate";
          break;
        case "connectivity":
          alertData.value.conditions.metric = "status";
          break;
        case "temperature":
          alertData.value.conditions.metric = "temperature";
          break;
        case "profitability":
          alertData.value.conditions.metric = "earnings";
          break;
        case "system":
          alertData.value.conditions.metric = "cpu_usage";
          break;
      }
    };

    const setSelectedMiners = (miners) => {
      alertData.value.miners = miners;
    };

    const updateConditions = (conditions) => {
      alertData.value.conditions = {
        ...alertData.value.conditions,
        ...conditions,
      };
    };

    const updateNotifications = (notifications) => {
      alertData.value.notifications = {
        ...alertData.value.notifications,
        ...notifications,
      };
    };

    const saveAsTemplate = (templateName) => {
      // Create a template from the current alert configuration
      const template = {
        name: templateName,
        type: alertData.value.type,
        conditions: { ...alertData.value.conditions },
        notifications: { ...alertData.value.notifications },
      };

      // Save the template (this would typically be stored in a store or API)
      // For now, we'll just emit an event
      emit("save-template", template);
    };

    const saveAlert = async () => {
      isSaving.value = true;

      try {
        // Generate a name if not provided
        if (!alertData.value.name) {
          const metricName = alertData.value.conditions.metric.replace(
            "_",
            " ",
          );
          const operator = alertData.value.conditions.operator;
          const threshold = alertData.value.conditions.threshold;

          alertData.value.name = `${metricName} ${operator} ${threshold}`;
        }

        // Prepare alert data for saving
        const alertToSave = { ...alertData.value };

        if (isEditMode.value) {
          // Update existing alert
          await alertsStore.updateAlert(props.editAlert.id, alertToSave);
        } else {
          // Add new alert
          await alertsStore.addAlert(alertToSave);
        }

        // Close the wizard
        show.value = false;

        // Emit completion event
        emit("config-complete");
      } catch (error) {
        console.error("Error saving alert:", error);
      } finally {
        isSaving.value = false;
      }
    };

    const nextStep = () => {
      if (currentStep.value < 4) {
        currentStep.value++;
      }
    };

    const prevStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--;
      }
    };

    const closeWizard = () => {
      show.value = false;
    };

    // Watch for edit alert changes
    watch(
      () => props.editAlert,
      (newAlert) => {
        if (newAlert) {
          // Populate form with existing alert data
          alertData.value = {
            id: newAlert.id,
            name: newAlert.name,
            type: newAlert.type,
            miners: [...newAlert.miners],
            conditions: { ...newAlert.conditions },
            notifications: { ...newAlert.notifications },
            enabled: newAlert.enabled,
            use_template: newAlert.use_template || false,
            template_id: newAlert.template_id || null,
          };
        }
      },
      { deep: true },
    );

    return {
      // State
      currentStep,
      alertData,
      isSaving,

      // Computed
      show,
      isEditMode,
      isConditionsValid,
      isNotificationsValid,

      // Methods
      setAlertType,
      setSelectedMiners,
      updateConditions,
      updateNotifications,
      saveAsTemplate,
      saveAlert,
      nextStep,
      prevStep,
      closeWizard,
    };
  },
};
</script>
