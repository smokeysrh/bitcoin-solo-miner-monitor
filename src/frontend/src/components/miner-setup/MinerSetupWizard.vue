<template>
  <v-dialog v-model="show" persistent max-width="800px" scrollable>
    <v-card>
      <v-card-title class="primary white--text">
        <span class="text-h5">{{
          isEditMode ? "Edit Miner" : "Add New Miner"
        }}</span>
        <v-spacer></v-spacer>
        <v-btn icon dark @click="closeWizard" v-if="allowClose">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-stepper v-model="currentStep" class="elevation-0">
        <!-- Stepper Header -->
        <v-stepper-header>
          <v-stepper-step
            :complete="currentStep > 1"
            step="1"
            :editable="!isScanning"
          >
            Miner Type
          </v-stepper-step>

          <v-divider></v-divider>

          <v-stepper-step
            :complete="currentStep > 2"
            step="2"
            :editable="currentStep >= 2 && !isScanning"
          >
            Connection
          </v-stepper-step>

          <v-divider></v-divider>

          <v-stepper-step
            :complete="currentStep > 3"
            step="3"
            :editable="currentStep >= 3 && !isScanning"
          >
            Configuration
          </v-stepper-step>

          <v-divider></v-divider>

          <v-stepper-step step="4" :editable="currentStep >= 4 && !isScanning">
            Verification
          </v-stepper-step>
        </v-stepper-header>

        <!-- Stepper Content -->
        <v-stepper-items>
          <!-- Step 1: Miner Type Selection -->
          <v-stepper-content step="1">
            <miner-type-selection
              :selected-type="minerData.type"
              @type-selected="setMinerType"
              @auto-detect="startAutoDetection"
            ></miner-type-selection>

            <v-divider class="my-4"></v-divider>

            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn text @click="closeWizard" :disabled="!allowClose">
                Cancel
              </v-btn>
              <v-btn
                color="primary"
                @click="nextStep"
                :disabled="!minerData.type"
              >
                Continue
                <v-icon right>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-stepper-content>

          <!-- Step 2: Connection Settings -->
          <v-stepper-content step="2">
            <connection-settings
              :miner-data="minerData"
              :is-scanning="isScanning"
              :scan-results="scanResults"
              @update-connection="updateConnection"
              @scan-network="scanNetwork"
            ></connection-settings>

            <v-divider class="my-4"></v-divider>

            <v-card-actions>
              <v-btn text @click="prevStep" :disabled="isScanning">
                <v-icon left>mdi-arrow-left</v-icon>
                Back
              </v-btn>
              <v-spacer></v-spacer>
              <v-btn
                text
                @click="closeWizard"
                :disabled="!allowClose || isScanning"
              >
                Cancel
              </v-btn>
              <v-btn
                color="primary"
                @click="testConnection"
                :loading="isTestingConnection"
                :disabled="!isConnectionValid || isScanning"
              >
                Test Connection
              </v-btn>
              <v-btn
                color="primary"
                @click="nextStep"
                :disabled="!isConnectionValid || isScanning"
              >
                Continue
                <v-icon right>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-stepper-content>

          <!-- Step 3: Miner Configuration -->
          <v-stepper-content step="3">
            <miner-configuration
              :miner-data="minerData"
              :connection-status="connectionStatus"
              :detected-features="detectedFeatures"
              @update-configuration="updateConfiguration"
            ></miner-configuration>

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
                :disabled="!isConfigValid"
              >
                Continue
                <v-icon right>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-stepper-content>

          <!-- Step 4: Verification and Summary -->
          <v-stepper-content step="4">
            <verification-summary
              :miner-data="minerData"
              :connection-status="connectionStatus"
              :is-edit-mode="isEditMode"
              @save-as-template="saveAsTemplate"
            ></verification-summary>

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
              <v-btn color="success" @click="saveMiner" :loading="isSaving">
                {{ isEditMode ? "Update Miner" : "Add Miner" }}
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
import { useMinersStore } from "../../stores/miners";
import MinerTypeSelection from "./MinerTypeSelection.vue";
import ConnectionSettings from "./ConnectionSettings.vue";
import MinerConfiguration from "./MinerConfiguration.vue";
import VerificationSummary from "./VerificationSummary.vue";

export default {
  name: "MinerSetupWizard",

  components: {
    MinerTypeSelection,
    ConnectionSettings,
    MinerConfiguration,
    VerificationSummary,
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

    editMiner: {
      type: Object,
      default: null,
    },
  },

  setup(props, { emit }) {
    const minersStore = useMinersStore();

    // State
    const currentStep = ref(1);
    const isScanning = ref(false);
    const isTestingConnection = ref(false);
    const isSaving = ref(false);
    const scanResults = ref([]);
    const connectionStatus = ref({
      status: "unknown",
      message: "",
      details: {},
    });
    const detectedFeatures = ref([]);

    // Miner data
    const minerData = ref({
      id: null,
      name: "",
      type: "",
      ip_address: "",
      port: null,
      mac_address: "",
      username: "",
      password: "",
      pool_url: "solo.ckpool.org",
      pool_port: 3333,
      pool_user: "",
      pool_pass: "x",
      fan_speed: 80,
      frequency: null,
      power_limit: null,
      use_template: false,
      template_id: null,
    });

    // Computed properties
    const show = computed({
      get: () => props.value,
      set: (value) => emit("input", value),
    });

    const isEditMode = computed(() => !!props.editMiner);

    const isConnectionValid = computed(() => {
      return (
        minerData.value.type &&
        minerData.value.ip_address &&
        /^(\d{1,3}\.){3}\d{1,3}$/.test(minerData.value.ip_address)
      );
    });

    const isConfigValid = computed(() => {
      return (
        minerData.value.name &&
        minerData.value.pool_url &&
        minerData.value.pool_port &&
        minerData.value.pool_user
      );
    });

    // Methods
    const setMinerType = (type) => {
      minerData.value.type = type;

      // Set default port based on miner type
      switch (type) {
        case "bitaxe":
          minerData.value.port = 80;
          break;
        case "avalon_nano":
          minerData.value.port = 4028;
          break;
        case "magic_miner":
          minerData.value.port = 80;
          break;
        default:
          minerData.value.port = null;
      }
    };

    const updateConnection = (connectionData) => {
      Object.assign(minerData.value, connectionData);
    };

    const updateConfiguration = (configData) => {
      Object.assign(minerData.value, configData);
    };

    const startAutoDetection = async () => {
      isScanning.value = true;

      try {
        // Start network discovery to find miners
        const discoveryResults = await minersStore.startDiscovery();

        // Process discovery results
        scanResults.value = discoveryResults.map((result) => ({
          ip: result.ip,
          type: result.type,
          name: result.name || `${result.type} (${result.ip})`,
          status: result.status || "unknown",
        }));

        // If miners were found, select the first one
        if (scanResults.value.length > 0) {
          const firstMiner = scanResults.value[0];
          setMinerType(firstMiner.type);
          minerData.value.ip_address = firstMiner.ip;
          minerData.value.name = firstMiner.name;
        }
      } catch (error) {
        console.error("Error during auto-detection:", error);
      } finally {
        isScanning.value = false;
      }
    };

    const scanNetwork = async (ipRange) => {
      isScanning.value = true;

      try {
        // Start network discovery with specific IP range
        const discoveryResults = await minersStore.startDiscovery(ipRange);

        // Process discovery results
        scanResults.value = discoveryResults.map((result) => ({
          ip: result.ip,
          type: result.type,
          name: result.name || `${result.type} (${result.ip})`,
          status: result.status || "unknown",
        }));
      } catch (error) {
        console.error("Error scanning network:", error);
      } finally {
        isScanning.value = false;
      }
    };

    const testConnection = async () => {
      isTestingConnection.value = true;

      try {
        // Test connection to the miner
        const result = await minersStore.testMinerConnection({
          type: minerData.value.type,
          ip_address: minerData.value.ip_address,
          port: minerData.value.port,
          username: minerData.value.username,
          password: minerData.value.password,
        });

        // Update connection status
        connectionStatus.value = {
          status: result.success ? "success" : "error",
          message: result.message,
          details: result.details || {},
        };

        // If connection was successful, update detected features
        if (
          result.success &&
          result.details &&
          result.details.supported_features
        ) {
          detectedFeatures.value = result.details.supported_features;
        }

        // If connection was successful and no name is set, use the detected name
        if (
          result.success &&
          result.details &&
          result.details.name &&
          !minerData.value.name
        ) {
          minerData.value.name = result.details.name;
        }
      } catch (error) {
        connectionStatus.value = {
          status: "error",
          message: error.message || "Connection failed",
          details: {},
        };
      } finally {
        isTestingConnection.value = false;
      }
    };

    const saveAsTemplate = (templateName) => {
      // Create a template from the current miner configuration
      const template = {
        name: templateName,
        type: minerData.value.type,
        pool_url: minerData.value.pool_url,
        pool_port: minerData.value.pool_port,
        pool_user: minerData.value.pool_user,
        pool_pass: minerData.value.pool_pass,
        fan_speed: minerData.value.fan_speed,
        frequency: minerData.value.frequency,
        power_limit: minerData.value.power_limit,
      };

      // Save the template (this would typically be stored in a store or API)
      // For now, we'll just emit an event
      emit("save-template", template);
    };

    const saveMiner = async () => {
      isSaving.value = true;

      try {
        // Prepare miner data for saving
        const minerToSave = {
          name: minerData.value.name,
          type: minerData.value.type,
          ip_address: minerData.value.ip_address,
          port: minerData.value.port,
          username: minerData.value.username,
          password: minerData.value.password,
          settings: {
            pool_url: minerData.value.pool_url,
            pool_port: minerData.value.pool_port,
            pool_user: minerData.value.pool_user,
            pool_pass: minerData.value.pool_pass,
            fan_speed: minerData.value.fan_speed,
            frequency: minerData.value.frequency,
            power_limit: minerData.value.power_limit,
          },
        };

        if (isEditMode.value) {
          // Update existing miner
          await minersStore.updateMiner(props.editMiner.id, minerToSave);
        } else {
          // Add new miner
          await minersStore.addMiner(minerToSave);
        }

        // Close the wizard
        show.value = false;

        // Emit completion event
        emit("setup-complete");
      } catch (error) {
        console.error("Error saving miner:", error);
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

    // Watch for edit miner changes
    watch(
      () => props.editMiner,
      (newMiner) => {
        if (newMiner) {
          // Populate form with existing miner data
          minerData.value = {
            id: newMiner.id,
            name: newMiner.name,
            type: newMiner.type,
            ip_address: newMiner.ip_address,
            port: newMiner.port,
            mac_address: newMiner.mac_address || "",
            username: newMiner.username || "",
            password: newMiner.password || "",
            pool_url: newMiner.settings?.pool_url || "solo.ckpool.org",
            pool_port: newMiner.settings?.pool_port || 3333,
            pool_user: newMiner.settings?.pool_user || "",
            pool_pass: newMiner.settings?.pool_pass || "x",
            fan_speed: newMiner.settings?.fan_speed || 80,
            frequency: newMiner.settings?.frequency || null,
            power_limit: newMiner.settings?.power_limit || null,
            use_template: false,
            template_id: null,
          };

          // Reset connection status
          connectionStatus.value = {
            status: "unknown",
            message: "",
            details: {},
          };

          // Reset detected features
          detectedFeatures.value = newMiner.supported_features || [];
        }
      },
    );

    return {
      // State
      currentStep,
      minerData,
      isScanning,
      isTestingConnection,
      isSaving,
      scanResults,
      connectionStatus,
      detectedFeatures,

      // Computed
      show,
      isEditMode,
      isConnectionValid,
      isConfigValid,

      // Methods
      setMinerType,
      updateConnection,
      updateConfiguration,
      startAutoDetection,
      scanNetwork,
      testConnection,
      saveAsTemplate,
      saveMiner,
      nextStep,
      prevStep,
      closeWizard,
    };
  },
};
</script>
