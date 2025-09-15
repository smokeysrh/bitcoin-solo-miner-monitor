<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Select Miner Type</h2>
            <p class="text-body-1 mb-6">
              Choose the type of miner you want to add to your monitoring
              dashboard.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col
            cols="12"
            md="4"
            v-for="(type, index) in minerTypes"
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

        <v-row class="mt-6">
          <v-col cols="12" class="text-center">
            <v-btn
              color="secondary"
              large
              @click="startAutoDetection"
              :loading="isAutoDetecting"
              :disabled="isAutoDetecting"
            >
              <v-icon left>mdi-radar</v-icon>
              Auto-Detect Miners
            </v-btn>
          </v-col>
        </v-row>

        <v-row v-if="isAutoDetecting">
          <v-col cols="12">
            <v-progress-linear
              indeterminate
              color="primary"
              height="6"
            ></v-progress-linear>
            <p class="text-center mt-2">Scanning network for miners...</p>
          </v-col>
        </v-row>

        <v-row v-if="showHelp" class="mt-4">
          <v-col cols="12">
            <v-alert type="info" outlined>
              <h3 class="text-subtitle-1 font-weight-bold">
                About Miner Types
              </h3>
              <p class="mb-0">
                Different miners have different capabilities and connection
                methods. Select the type that matches your hardware or use the
                auto-detection feature to scan your network for compatible
                miners.
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
  name: "MinerTypeSelection",

  props: {
    selectedType: {
      type: String,
      default: "",
    },

    showHelp: {
      type: Boolean,
      default: true,
    },
  },

  data() {
    return {
      isAutoDetecting: false,
      minerTypes: [
        {
          name: "Bitaxe",
          value: "bitaxe",
          icon: "mdi-pickaxe",
          description: "Open-source Bitcoin ASIC miner with web interface",
        },
        {
          name: "Avalon Nano",
          value: "avalon_nano",
          icon: "mdi-chip",
          description: "Compact USB Bitcoin miner using cgminer API",
        },
        {
          name: "Magic Miner",
          value: "magic_miner",
          icon: "mdi-lightning-bolt",
          description: "High-performance Bitcoin miner with web dashboard",
        },
      ],
    };
  },

  methods: {
    selectType(type) {
      this.$emit("type-selected", type);
    },

    async startAutoDetection() {
      this.isAutoDetecting = true;

      try {
        // Emit event to parent component to handle auto-detection
        this.$emit("auto-detect");
      } catch (error) {
        console.error("Error during auto-detection:", error);
      }
    },
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
