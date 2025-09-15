<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Select Alert Type</h2>
            <p class="text-body-1 mb-6">
              Choose the type of alert you want to create.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col
            cols="12"
            md="4"
            v-for="(type, index) in alertTypes"
            :key="index"
          >
            <v-card
              :class="{ 'selected-card': selectedType === type.value }"
              @click="selectType(type.value)"
              height="100%"
              :elevation="selectedType === type.value ? 8 : 2"
              :color="selectedType === type.value ? 'primary lighten-4' : ''"
            >
              <v-card-text class="text-center">
                <v-avatar size="80" class="mb-4">
                  <v-icon
                    size="64"
                    :color="selectedType === type.value ? 'primary' : ''"
                  >
                    {{ type.icon }}
                  </v-icon>
                </v-avatar>
                <h3 class="text-h6 mb-2">{{ type.name }}</h3>
                <p class="text-body-2">{{ type.description }}</p>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row class="mt-6" v-if="selectedType && selectedType !== 'system'">
          <v-col cols="12">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="primary">mdi-server-network</v-icon>
                Select Miners
              </v-card-title>
              <v-card-text>
                <p class="text-body-2 mb-4">
                  Choose which miners this alert will monitor.
                </p>

                <v-radio-group v-model="minerSelection" row>
                  <v-radio label="All Miners" value="all"></v-radio>
                  <v-radio label="Specific Miners" value="specific"></v-radio>
                </v-radio-group>

                <v-expand-transition>
                  <div v-if="minerSelection === 'specific'">
                    <v-autocomplete
                      v-model="selectedMiners"
                      :items="availableMiners"
                      item-text="name"
                      item-value="id"
                      label="Select Miners"
                      multiple
                      chips
                      outlined
                      :rules="[
                        (v) =>
                          v.length > 0 || 'At least one miner must be selected',
                      ]"
                    >
                      <template v-slot:selection="{ item, index }">
                        <v-chip v-if="index < 3">
                          <span>{{ item.name }}</span>
                        </v-chip>
                        <span
                          v-if="index === 3"
                          class="grey--text text-caption"
                        >
                          (+{{ selectedMiners.length - 3 }} more)
                        </span>
                      </template>
                    </v-autocomplete>

                    <v-btn
                      text
                      color="primary"
                      class="mt-2"
                      @click="selectAllMiners"
                    >
                      <v-icon left>mdi-checkbox-multiple-marked</v-icon>
                      Select All
                    </v-btn>
                  </div>
                </v-expand-transition>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="showHelp" class="mt-4">
          <v-col cols="12">
            <v-alert type="info" outlined>
              <h3 class="text-subtitle-1 font-weight-bold">
                About Alert Types
              </h3>
              <p class="mb-2">
                Different alert types monitor different aspects of your mining
                operation:
              </p>
              <ul class="mb-0">
                <li>
                  <strong>Performance Alerts:</strong> Monitor hashrate, shares,
                  and other performance metrics
                </li>
                <li>
                  <strong>Connectivity Alerts:</strong> Notify when miners go
                  offline or have connection issues
                </li>
                <li>
                  <strong>Temperature Alerts:</strong> Monitor hardware
                  temperatures to prevent overheating
                </li>
                <li>
                  <strong>Profitability Alerts:</strong> Track earnings and
                  notify of significant changes
                </li>
                <li>
                  <strong>System Alerts:</strong> Monitor the monitoring system
                  itself (CPU, memory, disk)
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
import { ref, computed, watch, onMounted } from "vue";
import { useMinersStore } from "../../stores/miners";

export default {
  name: "AlertTypeSelection",

  props: {
    selectedType: {
      type: String,
      default: "",
    },

    initialSelectedMiners: {
      type: Array,
      default: () => [],
    },

    showHelp: {
      type: Boolean,
      default: true,
    },
  },

  setup(props, { emit }) {
    const minersStore = useMinersStore();

    // State
    const minerSelection = ref(
      props.initialSelectedMiners.length === 0 ||
        (props.initialSelectedMiners.length === 1 &&
          props.initialSelectedMiners[0] === "all")
        ? "all"
        : "specific",
    );
    const internalSelectedMiners = ref([]);

    // Alert types
    const alertTypes = [
      {
        name: "Performance",
        value: "performance",
        icon: "mdi-speedometer",
        description: "Monitor hashrate, shares, and other performance metrics",
      },
      {
        name: "Connectivity",
        value: "connectivity",
        icon: "mdi-lan-connect",
        description:
          "Get notified when miners go offline or have connection issues",
      },
      {
        name: "Temperature",
        value: "temperature",
        icon: "mdi-thermometer",
        description: "Monitor hardware temperatures to prevent overheating",
      },
      {
        name: "Profitability",
        value: "profitability",
        icon: "mdi-currency-btc",
        description: "Track earnings and get notified of significant changes",
      },
      {
        name: "System",
        value: "system",
        icon: "mdi-desktop-tower-monitor",
        description: "Monitor the monitoring system itself (CPU, memory, disk)",
      },
    ];

    // Computed properties
    const availableMiners = computed(() => {
      return minersStore.miners.map((miner) => ({
        id: miner.id,
        name: miner.name || `${miner.type} (${miner.ip_address})`,
      }));
    });

    const computedSelectedMiners = computed({
      get: () => {
        if (minerSelection.value === "all") {
          return ["all"];
        }
        return internalSelectedMiners.value;
      },
      set: (value) => {
        internalSelectedMiners.value = value;
        emitSelectedMiners();
      },
    });

    // Methods
    const selectType = (type) => {
      emit("type-selected", type);
    };

    const selectAllMiners = () => {
      internalSelectedMiners.value = availableMiners.value.map(
        (miner) => miner.id,
      );
      emitSelectedMiners();
    };

    const emitSelectedMiners = () => {
      if (minerSelection.value === "all") {
        emit("miners-selected", ["all"]);
      } else {
        emit("miners-selected", internalSelectedMiners.value);
      }
    };

    // Watch for changes
    watch(
      () => minerSelection.value,
      (_newValue) => {
        emitSelectedMiners();
      },
    );

    watch(
      () => props.initialSelectedMiners,
      (newValue) => {
        if (newValue.length === 1 && newValue[0] === "all") {
          minerSelection.value = "all";
        } else if (newValue.length > 0) {
          minerSelection.value = "specific";
          internalSelectedMiners.value = newValue;
        }
      },
      { immediate: true },
    );

    // Lifecycle hooks
    onMounted(() => {
      // Fetch miners if not already loaded
      if (minersStore.miners.length === 0) {
        minersStore.fetchMiners();
      }
    });

    return {
      alertTypes,
      minerSelection,
      availableMiners,
      selectedMiners: computedSelectedMiners,
      selectType,
      selectAllMiners,
    };
  },
};
</script>

<style scoped>
.selected-card {
  border: 2px solid var(--v-primary-base);
  transform: translateY(-4px);
  transition: all 0.3s ease;
}

.v-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.v-card:hover:not(.selected-card) {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}
</style>
