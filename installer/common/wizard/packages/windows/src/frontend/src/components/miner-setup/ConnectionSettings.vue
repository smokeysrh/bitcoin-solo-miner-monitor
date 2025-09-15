<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Connection Settings</h2>
            <p class="text-body-1 mb-6">
              Configure how to connect to your {{ getMinerTypeName }} miner.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12" md="6">
            <v-card outlined class="mb-4">
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-connection</v-icon>
                Connection Details
              </v-card-title>
              <v-card-text>
                <v-form ref="connectionForm" v-model="isFormValid">
                  <v-text-field
                    v-model="connectionData.ip_address"
                    label="IP Address"
                    :rules="[
                      (v) => !!v || 'IP address is required',
                      ipAddressRule,
                    ]"
                    hint="e.g. 10.0.0.100"
                    persistent-hint
                    outlined
                    dense
                  ></v-text-field>

                  <v-text-field
                    v-model="connectionData.port"
                    label="Port"
                    type="number"
                    :rules="[portRule]"
                    :hint="getDefaultPortHint"
                    persistent-hint
                    outlined
                    dense
                    class="mt-4"
                  ></v-text-field>

                  <v-text-field
                    v-model="connectionData.name"
                    label="Miner Name"
                    :rules="[(v) => !!v || 'Miner name is required']"
                    hint="A friendly name to identify this miner"
                    persistent-hint
                    outlined
                    dense
                    class="mt-4"
                  ></v-text-field>

                  <v-expand-transition>
                    <div v-if="showAdvancedOptions">
                      <v-text-field
                        v-model="connectionData.username"
                        label="Username (Optional)"
                        hint="Leave empty if not required"
                        persistent-hint
                        outlined
                        dense
                        class="mt-4"
                      ></v-text-field>

                      <v-text-field
                        v-model="connectionData.password"
                        label="Password (Optional)"
                        type="password"
                        hint="Leave empty if not required"
                        persistent-hint
                        outlined
                        dense
                        class="mt-4"
                      ></v-text-field>

                      <v-text-field
                        v-model="connectionData.mac_address"
                        label="MAC Address (Optional)"
                        hint="For Wake-on-LAN functionality"
                        persistent-hint
                        outlined
                        dense
                        class="mt-4"
                      ></v-text-field>
                    </div>
                  </v-expand-transition>

                  <v-btn
                    text
                    color="primary"
                    class="mt-2 px-0"
                    @click="showAdvancedOptions = !showAdvancedOptions"
                  >
                    {{ showAdvancedOptions ? "Hide" : "Show" }} Advanced Options
                    <v-icon right>
                      {{
                        showAdvancedOptions
                          ? "mdi-chevron-up"
                          : "mdi-chevron-down"
                      }}
                    </v-icon>
                  </v-btn>
                </v-form>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="6">
            <v-card outlined>
              <v-card-title class="subtitle-1">
                <v-icon left color="primary">mdi-magnify</v-icon>
                Network Discovery
              </v-card-title>
              <v-card-text>
                <p class="text-body-2 mb-4">
                  Scan your network to find {{ getMinerTypeName }} miners
                  automatically.
                </p>

                <v-text-field
                  v-model="scanRange"
                  label="IP Range"
                  hint="e.g. 192.168.1.1-254"
                  persistent-hint
                  outlined
                  dense
                  :disabled="isScanning"
                ></v-text-field>

                <v-btn
                  color="primary"
                  block
                  class="mt-4"
                  @click="startNetworkScan"
                  :loading="isScanning"
                  :disabled="isScanning"
                >
                  <v-icon left>mdi-radar</v-icon>
                  Scan Network
                </v-btn>

                <v-divider class="my-4"></v-divider>

                <h3 class="subtitle-2 mb-2">Scan Results</h3>
                <v-data-table
                  :headers="scanResultHeaders"
                  :items="scanResults"
                  :loading="isScanning"
                  :no-data-text="isScanning ? 'Scanning...' : 'No miners found'"
                  height="200px"
                  dense
                  class="elevation-1"
                  :items-per-page="5"
                >
                  <template v-slot:item.status="{ item }">
                    <v-chip
                      x-small
                      :color="item.status === 'online' ? 'success' : 'error'"
                      dark
                    >
                      {{ item.status }}
                    </v-chip>
                  </template>

                  <template v-slot:item.actions="{ item }">
                    <v-btn
                      x-small
                      text
                      color="primary"
                      @click="selectMiner(item)"
                    >
                      Select
                    </v-btn>
                  </template>
                </v-data-table>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="showHelp" class="mt-4">
          <v-col cols="12">
            <v-alert type="info" outlined>
              <h3 class="text-subtitle-1 font-weight-bold">Connection Help</h3>
              <p>
                To connect to your miner, you need its IP address and port. If
                you don't know these details:
              </p>
              <ul class="mb-0">
                <li>
                  Use the "Scan Network" button to automatically discover miners
                </li>
                <li>Check your router's connected devices list</li>
                <li>
                  The default port for {{ getMinerTypeName }} is typically
                  {{ getDefaultPort }}
                </li>
              </ul>
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: "ConnectionSettings",

  props: {
    minerData: {
      type: Object,
      required: true,
    },

    isScanning: {
      type: Boolean,
      default: false,
    },

    scanResults: {
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
      isFormValid: false,
      showAdvancedOptions: false,
      scanRange: "192.168.1.1-254",
      connectionData: {
        ip_address: this.minerData.ip_address || "",
        port: this.minerData.port || "",
        name: this.minerData.name || "",
        username: this.minerData.username || "",
        password: this.minerData.password || "",
        mac_address: this.minerData.mac_address || "",
      },
      scanResultHeaders: [
        { text: "Name", value: "name" },
        { text: "IP", value: "ip" },
        { text: "Type", value: "type" },
        { text: "Status", value: "status" },
        { text: "Actions", value: "actions", sortable: false },
      ],
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

    getDefaultPort() {
      switch (this.minerData.type) {
        case "bitaxe":
          return 80;
        case "avalon_nano":
          return 4028;
        case "magic_miner":
          return 80;
        default:
          return 80;
      }
    },

    getDefaultPortHint() {
      return `Default port for ${this.getMinerTypeName}: ${this.getDefaultPort}`;
    },
  },

  watch: {
    minerData: {
      handler(newValue) {
        // Update local data when minerData prop changes
        this.connectionData = {
          ip_address: newValue.ip_address || "",
          port: newValue.port || this.getDefaultPort,
          name: newValue.name || "",
          username: newValue.username || "",
          password: newValue.password || "",
          mac_address: newValue.mac_address || "",
        };
      },
      deep: true,
    },

    connectionData: {
      handler(newValue) {
        // Emit updated connection data to parent
        this.$emit("update-connection", newValue);
      },
      deep: true,
    },
  },

  methods: {
    ipAddressRule(value) {
      const pattern =
        /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
      return pattern.test(value) || "Invalid IP address format";
    },

    portRule(value) {
      if (!value) return true;
      const port = parseInt(value);
      return (port >= 1 && port <= 65535) || "Port must be between 1 and 65535";
    },

    startNetworkScan() {
      // Parse IP range
      let range = this.scanRange;

      // Default to full subnet if no range specified
      if (!range) {
        range = "192.168.1.1-254";
      }

      // Emit event to parent component to handle network scanning
      this.$emit("scan-network", range);
    },

    selectMiner(miner) {
      // Update connection data with selected miner
      this.connectionData.ip_address = miner.ip;
      this.connectionData.name = miner.name;

      // If the miner has a type, update it in the parent component
      if (miner.type) {
        const minerType = miner.type.toLowerCase().replace(" ", "_");
        this.$emit("update-type", minerType);
      }

      // Emit updated connection data to parent
      this.$emit("update-connection", this.connectionData);
    },
  },
};
</script>

<style scoped>
.v-data-table {
  border-radius: 4px;
}
</style>
