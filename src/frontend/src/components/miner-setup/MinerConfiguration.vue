<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Miner Configuration</h2>
            <p class="text-body-1 mb-6">
              Configure your {{ getMinerTypeName }} miner settings.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12" md="6">
            <v-card outlined class="mb-4">
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-server-network</v-icon>
                Pool Configuration
              </v-card-title>
              <v-card-text>
                <v-form ref="poolForm" v-model="isPoolFormValid">
                  <v-text-field
                    v-model="configData.pool_url"
                    label="Pool URL"
                    :rules="[(v) => !!v || 'Pool URL is required']"
                    hint="e.g. solo.ckpool.org"
                    persistent-hint
                    outlined
                    dense
                  ></v-text-field>

                  <v-text-field
                    v-model="configData.pool_port"
                    label="Pool Port"
                    type="number"
                    :rules="[(v) => !!v || 'Pool port is required', portRule]"
                    hint="e.g. 3333"
                    persistent-hint
                    outlined
                    dense
                    class="mt-4"
                  ></v-text-field>

                  <v-text-field
                    v-model="configData.pool_user"
                    label="Worker Username"
                    :rules="[(v) => !!v || 'Worker username is required']"
                    hint="Your Bitcoin address or worker name"
                    persistent-hint
                    outlined
                    dense
                    class="mt-4"
                  ></v-text-field>

                  <v-text-field
                    v-model="configData.pool_pass"
                    label="Worker Password"
                    hint="Usually 'x' or your worker name"
                    persistent-hint
                    outlined
                    dense
                    class="mt-4"
                  ></v-text-field>
                </v-form>
              </v-card-text>
            </v-card>

            <v-card outlined v-if="showTemplateOptions">
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-content-save-outline</v-icon>
                Configuration Templates
              </v-card-title>
              <v-card-text>
                <v-select
                  v-model="selectedTemplate"
                  :items="templates"
                  item-text="name"
                  item-value="id"
                  label="Load Template"
                  outlined
                  dense
                  @change="loadTemplate"
                ></v-select>

                <v-checkbox
                  v-model="configData.use_template"
                  label="Use template for this miner"
                  dense
                ></v-checkbox>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="6">
            <v-card outlined>
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-tune</v-icon>
                Hardware Settings
              </v-card-title>
              <v-card-text>
                <v-alert
                  v-if="connectionStatus.status !== 'success'"
                  type="warning"
                  outlined
                  dense
                  class="mb-4"
                >
                  <div class="text-caption">
                    <strong>Connection not verified.</strong> Some hardware
                    settings may not be available until connection is tested.
                  </div>
                </v-alert>

                <div v-if="hasFeature('fan_control')">
                  <h3 class="subtitle-2 mb-2">Fan Speed</h3>
                  <v-slider
                    v-model="configData.fan_speed"
                    label="Fan Speed"
                    hint="Higher values may increase noise but improve cooling"
                    persistent-hint
                    min="0"
                    max="100"
                    thumb-label="always"
                    :disabled="!hasFeature('fan_control')"
                  >
                    <template v-slot:append>
                      <v-text-field
                        v-model="configData.fan_speed"
                        type="number"
                        style="width: 60px"
                        dense
                        hide-details
                        :disabled="!hasFeature('fan_control')"
                      ></v-text-field>
                      <span class="ml-1">%</span>
                    </template>
                  </v-slider>
                </div>

                <div v-if="hasFeature('frequency_control')" class="mt-4">
                  <h3 class="subtitle-2 mb-2">Frequency</h3>
                  <v-slider
                    v-model="configData.frequency"
                    label="Frequency"
                    hint="Higher values may increase hashrate but also power consumption"
                    persistent-hint
                    :min="getMinFrequency"
                    :max="getMaxFrequency"
                    thumb-label="always"
                    :disabled="!hasFeature('frequency_control')"
                  >
                    <template v-slot:append>
                      <v-text-field
                        v-model="configData.frequency"
                        type="number"
                        style="width: 70px"
                        dense
                        hide-details
                        :disabled="!hasFeature('frequency_control')"
                      ></v-text-field>
                      <span class="ml-1">MHz</span>
                    </template>
                  </v-slider>
                </div>

                <div v-if="hasFeature('power_limit')" class="mt-4">
                  <h3 class="subtitle-2 mb-2">Power Limit</h3>
                  <v-slider
                    v-model="configData.power_limit"
                    label="Power Limit"
                    hint="Lower values reduce power consumption but may affect performance"
                    persistent-hint
                    :min="getMinPower"
                    :max="getMaxPower"
                    thumb-label="always"
                    :disabled="!hasFeature('power_limit')"
                  >
                    <template v-slot:append>
                      <v-text-field
                        v-model="configData.power_limit"
                        type="number"
                        style="width: 60px"
                        dense
                        hide-details
                        :disabled="!hasFeature('power_limit')"
                      ></v-text-field>
                      <span class="ml-1">W</span>
                    </template>
                  </v-slider>
                </div>

                <div v-if="!hasAnyFeature" class="text-center mt-4">
                  <v-icon color="grey" size="64">mdi-tune</v-icon>
                  <p class="text-body-2 grey--text mt-2">
                    Hardware settings will be available after connection is
                    verified.
                  </p>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="showHelp" class="mt-4">
          <v-col cols="12">
            <v-alert type="info" outlined>
              <h3 class="text-subtitle-1 font-weight-bold">
                Configuration Help
              </h3>
              <p>
                <strong>Pool Configuration:</strong> Enter the details of your
                mining pool. For solo mining, use a solo pool like
                solo.ckpool.org and your Bitcoin address as the username.
              </p>
              <p class="mb-0">
                <strong>Hardware Settings:</strong> These settings control how
                your miner operates. Higher frequencies may increase hashrate
                but also power consumption and heat. Adjust fan speed to
                maintain safe temperatures.
              </p>
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: "MinerConfiguration",

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

    detectedFeatures: {
      type: Array,
      default: () => [],
    },

    showHelp: {
      type: Boolean,
      default: true,
    },
  },

  data() {
    return {
      isPoolFormValid: false,
      configData: {
        pool_url: this.minerData.pool_url || "solo.ckpool.org",
        pool_port: this.minerData.pool_port || 3333,
        pool_user: this.minerData.pool_user || "",
        pool_pass: this.minerData.pool_pass || "x",
        fan_speed: this.minerData.fan_speed || 80,
        frequency: this.minerData.frequency || "",
        power_limit: this.minerData.power_limit || "",
        use_template: this.minerData.use_template || false,
        template_id: this.minerData.template_id || null,
      },
      selectedTemplate: null,
      templates: [
        {
          id: 1,
          name: "Default Solo Mining",
          pool_url: "solo.ckpool.org",
          pool_port: 3333,
        },
        {
          id: 2,
          name: "Slush Pool",
          pool_url: "stratum.slushpool.com",
          pool_port: 3333,
        },
        { id: 3, name: "F2Pool", pool_url: "btc.f2pool.com", pool_port: 3333 },
      ],
      showTemplateOptions: true,
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
          return "Bitcoin";
      }
    },

    getMinFrequency() {
      switch (this.minerData.type) {
        case "bitaxe":
          return 100;
        case "avalon_nano":
          return 200;
        case "magic_miner":
          return 300;
        default:
          return 100;
      }
    },

    getMaxFrequency() {
      switch (this.minerData.type) {
        case "bitaxe":
          return 500;
        case "avalon_nano":
          return 800;
        case "magic_miner":
          return 1200;
        default:
          return 1000;
      }
    },

    getDefaultFrequency() {
      switch (this.minerData.type) {
        case "bitaxe":
          return 350;
        case "avalon_nano":
          return 500;
        case "magic_miner":
          return 800;
        default:
          return 500;
      }
    },

    getMinPower() {
      return 50;
    },

    getMaxPower() {
      switch (this.minerData.type) {
        case "bitaxe":
          return 200;
        case "avalon_nano":
          return 150;
        case "magic_miner":
          return 300;
        default:
          return 200;
      }
    },

    getDefaultPower() {
      switch (this.minerData.type) {
        case "bitaxe":
          return 150;
        case "avalon_nano":
          return 100;
        case "magic_miner":
          return 200;
        default:
          return 150;
      }
    },

    hasAnyFeature() {
      return (
        this.hasFeature("fan_control") ||
        this.hasFeature("frequency_control") ||
        this.hasFeature("power_limit")
      );
    },
  },

  watch: {
    minerData: {
      handler(newValue) {
        // Update local data when minerData prop changes
        this.configData = {
          pool_url: newValue.pool_url || "solo.ckpool.org",
          pool_port: newValue.pool_port || 3333,
          pool_user: newValue.pool_user || "",
          pool_pass: newValue.pool_pass || "x",
          fan_speed: newValue.fan_speed || 80,
          frequency: newValue.frequency || this.getDefaultFrequency,
          power_limit: newValue.power_limit || this.getDefaultPower,
          use_template: newValue.use_template || false,
          template_id: newValue.template_id || null,
        };
      },
      deep: true,
    },

    configData: {
      handler(newValue) {
        // Emit updated configuration data to parent
        this.$emit("update-configuration", newValue);
      },
      deep: true,
    },
  },

  methods: {
    portRule(value) {
      if (!value) return true;
      const port = parseInt(value);
      return (port >= 1 && port <= 65535) || "Port must be between 1 and 65535";
    },

    hasFeature(feature) {
      // Check if feature is in the detected features array
      return (
        this.detectedFeatures.includes(feature) ||
        // If connection is not tested yet, show all features
        this.connectionStatus.status === "unknown"
      );
    },

    loadTemplate(templateId) {
      if (!templateId) return;

      const template = this.templates.find((t) => t.id === templateId);
      if (template) {
        // Update configuration with template values
        this.configData = {
          ...this.configData,
          pool_url: template.pool_url,
          pool_port: template.pool_port,
          template_id: templateId,
          use_template: true,
        };
      }
    },
  },
};
</script>

<style scoped>
.v-slider__thumb-label {
  background-color: var(--v-primary-base) !important;
}
</style>
