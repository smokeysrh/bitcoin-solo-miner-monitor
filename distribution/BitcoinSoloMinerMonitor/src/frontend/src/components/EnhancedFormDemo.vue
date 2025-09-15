<template>
  <div class="enhanced-form-demo">
    <div class="demo-header">
      <h2 class="text-h2">Enhanced Form Components Demo</h2>
      <p class="text-secondary">
        Demonstration of enhanced button and form styling with Bitcoin Orange
        theme
      </p>
    </div>

    <!-- Enhanced Buttons Section -->
    <v-card class="demo-section mb-6">
      <v-card-title>Enhanced Button System</v-card-title>
      <v-card-text>
        <div class="demo-grid">
          <!-- Primary Buttons -->
          <div class="demo-item">
            <h4 class="demo-subtitle">Primary Buttons</h4>
            <div class="button-group">
              <button
                class="btn-enhanced btn-enhanced-primary btn-enhanced-small"
              >
                Small Primary
              </button>
              <button class="btn-enhanced btn-enhanced-primary">
                Default Primary
              </button>
              <button
                class="btn-enhanced btn-enhanced-primary btn-enhanced-large"
              >
                Large Primary
              </button>
            </div>
            <div class="button-group mt-4">
              <button class="btn-enhanced btn-enhanced-primary" disabled>
                Disabled
              </button>
              <button
                class="btn-enhanced btn-enhanced-primary"
                :class="{ 'btn-enhanced-loading': isLoading }"
                @click="toggleLoading"
              >
                {{ isLoading ? "Loading..." : "Click for Loading" }}
              </button>
            </div>
          </div>

          <!-- Secondary Buttons -->
          <div class="demo-item">
            <h4 class="demo-subtitle">Secondary & Ghost Buttons</h4>
            <div class="button-group">
              <button class="btn-enhanced btn-enhanced-secondary">
                Secondary Button
              </button>
              <button class="btn-enhanced btn-enhanced-ghost">
                Ghost Button
              </button>
            </div>
            <div class="button-group mt-4">
              <button class="btn-enhanced btn-enhanced-icon">
                <v-icon>mdi-cog</v-icon>
              </button>
              <button class="btn-enhanced btn-enhanced-primary">
                Add Miner
              </button>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Enhanced Form Inputs Section -->
    <v-card class="demo-section mb-6">
      <v-card-title>Enhanced Form Inputs</v-card-title>
      <v-card-text>
        <v-form ref="demoForm" v-model="formValid">
          <div class="demo-grid">
            <!-- Basic Inputs -->
            <div class="demo-item">
              <h4 class="demo-subtitle">Text Inputs</h4>

              <div class="form-group-enhanced">
                <label class="form-label-enhanced">Miner Name</label>
                <input
                  v-model="formData.minerName"
                  type="text"
                  class="input-enhanced"
                  placeholder="Enter miner name..."
                />
                <div class="form-help-text">
                  Choose a unique name for your miner
                </div>
              </div>

              <div class="form-group-enhanced">
                <label class="form-label-enhanced required">IP Address</label>
                <div class="input-enhanced-with-icon">
                  <input
                    v-model="formData.ipAddress"
                    type="text"
                    class="input-enhanced"
                    :class="getInputValidationClass('ipAddress')"
                    placeholder="192.168.1.100"
                    @blur="validateIpAddress"
                  />
                  <span class="input-icon">🌐</span>
                </div>
                <div v-if="validationErrors.ipAddress" class="form-error-text">
                  ✗ {{ validationErrors.ipAddress }}
                </div>
              </div>

              <div class="form-group-enhanced">
                <label class="form-label-enhanced">Description</label>
                <textarea
                  v-model="formData.description"
                  class="input-enhanced textarea-enhanced"
                  placeholder="Optional description..."
                ></textarea>
              </div>
            </div>

            <!-- Select Dropdowns -->
            <div class="demo-item">
              <h4 class="demo-subtitle">Select Dropdowns</h4>

              <div class="form-group-enhanced">
                <label class="form-label-enhanced">Miner Type</label>
                <div class="select-enhanced">
                  <select v-model="formData.minerType">
                    <option value="">Select miner type...</option>
                    <option value="bitaxe">Bitaxe</option>
                    <option value="avalon_nano">Avalon Nano</option>
                    <option value="magic_miner">Magic Miner</option>
                  </select>
                </div>
              </div>

              <div class="form-group-enhanced">
                <label class="form-label-enhanced">Refresh Interval</label>
                <div class="select-enhanced">
                  <select v-model="formData.refreshInterval">
                    <option value="5">5 seconds</option>
                    <option value="10">10 seconds</option>
                    <option value="30">30 seconds</option>
                    <option value="60">1 minute</option>
                  </select>
                </div>
              </div>

              <div class="form-group-enhanced">
                <label class="form-label-enhanced">Port</label>
                <div class="select-enhanced">
                  <select v-model="formData.port">
                    <option value="80">80 (HTTP)</option>
                    <option value="443">443 (HTTPS)</option>
                    <option value="4028">4028 (CGMiner)</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

    <!-- Enhanced Checkboxes and Radio Buttons Section -->
    <v-card class="demo-section mb-6">
      <v-card-title>Enhanced Checkboxes and Radio Buttons</v-card-title>
      <v-card-text>
        <div class="demo-grid">
          <!-- Checkboxes -->
          <div class="demo-item">
            <h4 class="demo-subtitle">Checkboxes</h4>

            <div class="form-group-enhanced">
              <label class="checkbox-enhanced">
                <input v-model="formData.enableNotifications" type="checkbox" />
                <span class="checkbox-box"></span>
                <span class="checkbox-label">Enable notifications</span>
              </label>
            </div>

            <div class="form-group-enhanced">
              <label class="checkbox-enhanced">
                <input v-model="formData.autoRefresh" type="checkbox" />
                <span class="checkbox-box"></span>
                <span class="checkbox-label">Auto-refresh dashboard</span>
              </label>
            </div>

            <div class="form-group-enhanced">
              <label class="checkbox-enhanced">
                <input v-model="formData.logPerformance" type="checkbox" />
                <span class="checkbox-box"></span>
                <span class="checkbox-label">Log performance data</span>
              </label>
            </div>

            <div class="form-group-enhanced">
              <label class="checkbox-enhanced">
                <input type="checkbox" disabled />
                <span class="checkbox-box"></span>
                <span class="checkbox-label">Disabled option</span>
              </label>
            </div>
          </div>

          <!-- Radio Buttons -->
          <div class="demo-item">
            <h4 class="demo-subtitle">Radio Buttons</h4>

            <div class="form-group-enhanced">
              <label class="form-label-enhanced">Mining Mode</label>

              <div class="mb-3">
                <label class="radio-enhanced">
                  <input
                    v-model="formData.miningMode"
                    type="radio"
                    value="solo"
                  />
                  <span class="radio-circle"></span>
                  <span class="radio-label">Solo Mining</span>
                </label>
              </div>

              <div class="mb-3">
                <label class="radio-enhanced">
                  <input
                    v-model="formData.miningMode"
                    type="radio"
                    value="pool"
                  />
                  <span class="radio-circle"></span>
                  <span class="radio-label">Pool Mining</span>
                </label>
              </div>

              <div class="mb-3">
                <label class="radio-enhanced">
                  <input type="radio" value="disabled" disabled />
                  <span class="radio-circle"></span>
                  <span class="radio-label">Disabled Option</span>
                </label>
              </div>
            </div>

            <div class="form-group-enhanced">
              <label class="form-label-enhanced">Experience Level</label>

              <div class="mb-3">
                <label class="radio-enhanced">
                  <input
                    v-model="formData.experienceLevel"
                    type="radio"
                    value="beginner"
                  />
                  <span class="radio-circle"></span>
                  <span class="radio-label">Beginner</span>
                </label>
              </div>

              <div class="mb-3">
                <label class="radio-enhanced">
                  <input
                    v-model="formData.experienceLevel"
                    type="radio"
                    value="intermediate"
                  />
                  <span class="radio-circle"></span>
                  <span class="radio-label">Intermediate</span>
                </label>
              </div>

              <div class="mb-3">
                <label class="radio-enhanced">
                  <input
                    v-model="formData.experienceLevel"
                    type="radio"
                    value="advanced"
                  />
                  <span class="radio-circle"></span>
                  <span class="radio-label">Advanced</span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Form Actions -->
    <v-card class="demo-section">
      <v-card-title>Form Actions</v-card-title>
      <v-card-text>
        <div class="button-group">
          <button
            class="btn-enhanced btn-enhanced-primary"
            @click="submitForm"
            :disabled="!formValid"
          >
            Save Configuration
          </button>
          <button
            class="btn-enhanced btn-enhanced-secondary"
            @click="resetForm"
          >
            Reset Form
          </button>
          <button class="btn-enhanced btn-enhanced-ghost" @click="showFormData">
            Show Form Data
          </button>
        </div>

        <!-- Form Data Display -->
        <div v-if="showData" class="mt-6 p-4 bg-surface-secondary rounded-lg">
          <h4 class="demo-subtitle mb-3">Current Form Data:</h4>
          <pre class="text-small">{{ JSON.stringify(formData, null, 2) }}</pre>
        </div>
      </v-card-text>
    </v-card>

    <!-- Accessibility Testing Section -->
    <v-card class="demo-section mt-6">
      <v-card-title>Accessibility Testing</v-card-title>
      <v-card-text>
        <p class="text-secondary mb-4">
          Tab through the elements below to test focus indicators and keyboard
          navigation:
        </p>

        <div class="demo-grid">
          <div class="demo-item">
            <h4 class="demo-subtitle">Focus Testing</h4>
            <div class="button-group">
              <button class="btn-enhanced btn-enhanced-primary">
                Focusable Button
              </button>
              <input
                type="text"
                class="input-enhanced"
                placeholder="Focusable input"
              />
            </div>
            <div class="mt-4">
              <div class="select-enhanced">
                <select>
                  <option>Focusable select</option>
                  <option>Option 2</option>
                </select>
              </div>
            </div>
          </div>

          <div class="demo-item">
            <h4 class="demo-subtitle">Screen Reader Support</h4>
            <div class="form-group-enhanced">
              <label class="form-label-enhanced required" for="sr-test">
                Properly labeled input
              </label>
              <input
                id="sr-test"
                type="text"
                class="input-enhanced"
                placeholder="Screen reader accessible"
                aria-describedby="sr-help"
              />
              <div id="sr-help" class="form-help-text">
                This input has proper ARIA attributes for screen readers
              </div>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
export default {
  name: "EnhancedFormDemo",

  data() {
    return {
      formValid: false,
      isLoading: false,
      showData: false,
      formData: {
        minerName: "",
        ipAddress: "",
        description: "",
        minerType: "",
        refreshInterval: "10",
        port: "4028",
        enableNotifications: true,
        autoRefresh: false,
        logPerformance: true,
        miningMode: "solo",
        experienceLevel: "beginner",
      },
      validationErrors: {},
    };
  },

  methods: {
    toggleLoading() {
      this.isLoading = true;
      setTimeout(() => {
        this.isLoading = false;
      }, 2000);
    },

    validateIpAddress() {
      const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
      if (this.formData.ipAddress && !ipRegex.test(this.formData.ipAddress)) {
        this.validationErrors.ipAddress = "Invalid IP address format";
      } else {
        delete this.validationErrors.ipAddress;
      }
    },

    getInputValidationClass(field) {
      if (this.validationErrors[field]) {
        return "input-enhanced-error";
      }
      return "";
    },

    submitForm() {
      this.validateIpAddress();

      if (Object.keys(this.validationErrors).length === 0) {
        this.$emit("form-submitted", this.formData);
        // Show success message or handle form submission
        console.log("Form submitted:", this.formData);
      }
    },

    resetForm() {
      this.formData = {
        minerName: "",
        ipAddress: "",
        description: "",
        minerType: "",
        refreshInterval: "10",
        port: "4028",
        enableNotifications: true,
        autoRefresh: false,
        logPerformance: true,
        miningMode: "solo",
        experienceLevel: "beginner",
      };
      this.validationErrors = {};
      this.showData = false;
    },

    showFormData() {
      this.showData = !this.showData;
    },
  },
};
</script>

<style scoped>
.enhanced-form-demo {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}

.demo-header {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.demo-section {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
}

.demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: var(--spacing-lg);
  margin-top: var(--spacing-lg);
}

.demo-item {
  padding: var(--spacing-md);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
}

.demo-subtitle {
  color: var(--color-primary);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-h4);
  font-weight: var(--font-weight-medium);
}

.button-group {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  align-items: center;
}

.bg-surface-secondary {
  background-color: var(--color-surface-secondary);
}

.rounded-lg {
  border-radius: var(--radius-lg);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .demo-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }

  .enhanced-form-demo {
    padding: var(--spacing-md);
  }

  .button-group {
    flex-direction: column;
    align-items: stretch;
  }

  .button-group button {
    width: 100%;
  }
}
</style>
