<template>
  <div class="enhanced-components-test">
    <v-container fluid>
      <v-row>
        <v-col cols="12">
          <div class="page-header mb-6">
            <h1 class="text-h3 mb-2">Enhanced Components Test</h1>
            <p class="text-subtitle-1 text-medium-emphasis">
              Testing enhanced button and form component styling with Bitcoin
              Orange theme
            </p>
          </div>

          <!-- Enhanced Form Demo Component -->
          <EnhancedFormDemo @form-submitted="handleFormSubmit" />

          <!-- Additional Test Sections -->
          <v-card class="mt-6">
            <v-card-title>Integration with Vuetify Components</v-card-title>
            <v-card-text>
              <p class="text-body-2 text-medium-emphasis mb-4">
                Comparison between enhanced components and standard Vuetify
                components:
              </p>

              <div class="comparison-grid">
                <!-- Enhanced Components Column -->
                <div class="comparison-column">
                  <h4 class="text-h6 mb-3 text-primary">Enhanced Components</h4>

                  <div class="mb-4">
                    <button class="btn-enhanced btn-enhanced-primary mb-2">
                      Enhanced Primary Button
                    </button>
                    <br />
                    <button class="btn-enhanced btn-enhanced-secondary">
                      Enhanced Secondary Button
                    </button>
                  </div>

                  <div class="form-group-enhanced mb-4">
                    <label class="form-label-enhanced">Enhanced Input</label>
                    <input
                      type="text"
                      class="input-enhanced"
                      placeholder="Enhanced input field"
                      v-model="testInput"
                    />
                  </div>

                  <div class="form-group-enhanced mb-4">
                    <label class="checkbox-enhanced">
                      <input type="checkbox" v-model="testCheckbox" />
                      <span class="checkbox-box"></span>
                      <span class="checkbox-label">Enhanced Checkbox</span>
                    </label>
                  </div>

                  <div class="form-group-enhanced">
                    <label class="form-label-enhanced">Enhanced Select</label>
                    <div class="select-enhanced">
                      <select v-model="testSelect">
                        <option value="">Select option...</option>
                        <option value="option1">Option 1</option>
                        <option value="option2">Option 2</option>
                      </select>
                    </div>
                  </div>
                </div>

                <!-- Vuetify Components Column -->
                <div class="comparison-column">
                  <h4 class="text-h6 mb-3 text-primary">Vuetify Components</h4>

                  <div class="mb-4">
                    <v-btn color="primary" class="mb-2 mr-2">
                      Vuetify Primary Button
                    </v-btn>
                    <br />
                    <v-btn variant="outlined" color="primary">
                      Vuetify Outlined Button
                    </v-btn>
                  </div>

                  <div class="mb-4">
                    <v-text-field
                      v-model="testInputVuetify"
                      label="Vuetify Input"
                      placeholder="Vuetify input field"
                      variant="outlined"
                      density="comfortable"
                    ></v-text-field>
                  </div>

                  <div class="mb-4">
                    <v-checkbox
                      v-model="testCheckboxVuetify"
                      label="Vuetify Checkbox"
                      color="primary"
                    ></v-checkbox>
                  </div>

                  <div>
                    <v-select
                      v-model="testSelectVuetify"
                      :items="selectItems"
                      label="Vuetify Select"
                      variant="outlined"
                      density="comfortable"
                    ></v-select>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>

          <!-- Performance and Accessibility Notes -->
          <v-card class="mt-6">
            <v-card-title>Implementation Notes</v-card-title>
            <v-card-text>
              <div class="notes-grid">
                <div class="note-section">
                  <h4 class="text-h6 mb-2 text-success">
                    ✓ Implemented Features
                  </h4>
                  <ul class="text-body-2">
                    <li>
                      Comprehensive button system (primary, secondary, ghost,
                      icon variants)
                    </li>
                    <li>Enhanced form inputs with proper focus states</li>
                    <li>Custom checkbox and radio button styling</li>
                    <li>Enhanced select dropdowns with custom styling</li>
                    <li>
                      Validation state indicators (success, warning, error)
                    </li>
                    <li>Smooth transitions and hover effects</li>
                    <li>Accessibility-compliant focus indicators</li>
                    <li>Support for reduced motion preferences</li>
                    <li>High contrast mode compatibility</li>
                    <li>Bitcoin Orange theme integration</li>
                  </ul>
                </div>

                <div class="note-section">
                  <h4 class="text-h6 mb-2 text-info">
                    📋 Requirements Coverage
                  </h4>
                  <ul class="text-body-2">
                    <li>
                      <strong>Requirement 3.1:</strong> Professional visual
                      hierarchy ✓
                    </li>
                    <li>
                      <strong>Requirement 3.2:</strong> Clear visual states
                      (hover, active, disabled) ✓
                    </li>
                    <li>
                      <strong>Requirement 3.3:</strong> Clear focus states and
                      validation styling ✓
                    </li>
                    <li>
                      <strong>Requirement 7.2:</strong> Clear focus indicators
                      for accessibility ✓
                    </li>
                    <li>
                      <strong>Requirement 9.1:</strong> Animation cues for
                      status changes ✓
                    </li>
                  </ul>
                </div>

                <div class="note-section">
                  <h4 class="text-h6 mb-2 text-warning">
                    ⚡ Performance Features
                  </h4>
                  <ul class="text-body-2">
                    <li>CSS-only implementations for better performance</li>
                    <li>Hardware-accelerated transitions where appropriate</li>
                    <li>Minimal JavaScript for enhanced functionality</li>
                    <li>Respects user motion preferences</li>
                    <li>Efficient CSS custom properties system</li>
                  </ul>
                </div>

                <div class="note-section">
                  <h4 class="text-h6 mb-2 text-primary">🎨 Design System</h4>
                  <ul class="text-body-2">
                    <li>Consistent Bitcoin Orange (#F7931A) primary color</li>
                    <li>Dark theme optimized color palette</li>
                    <li>Systematic spacing and typography scale</li>
                    <li>Elevation system with proper shadows</li>
                    <li>Responsive design considerations</li>
                  </ul>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script>
import { ref } from "vue";
import { useGlobalSnackbar } from "../composables/useGlobalSnackbar";
import EnhancedFormDemo from "../components/EnhancedFormDemo.vue";

export default {
  name: "EnhancedComponentsTest",

  components: {
    EnhancedFormDemo,
  },

  setup() {
    const { showSuccess, showError, showWarning, showInfo } = useGlobalSnackbar();

    // Reactive data
    const testInput = ref("");
    const testCheckbox = ref(false);
    const testSelect = ref("");
    const testInputVuetify = ref("");
    const testCheckboxVuetify = ref(false);
    const testSelectVuetify = ref("");
    const selectItems = ref([
      { title: "Option 1", value: "option1" },
      { title: "Option 2", value: "option2" },
      { title: "Option 3", value: "option3" },
    ]);

    // Methods
    const handleFormSubmit = (formData) => {
      console.log("Form submitted from demo:", formData);
      showSuccess("Form submitted successfully!");
    };

    return {
      testInput,
      testCheckbox,
      testSelect,
      testInputVuetify,
      testCheckboxVuetify,
      testSelectVuetify,
      selectItems,
      handleFormSubmit,
    };
  },
};
</script>

<style scoped>
.enhanced-components-test {
  min-height: 100vh;
  background-color: var(--color-background);
}

.page-header {
  text-align: center;
  padding: var(--spacing-xl) 0;
}

.comparison-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
  margin-top: var(--spacing-lg);
}

.comparison-column {
  padding: var(--spacing-lg);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
}

.notes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
  margin-top: var(--spacing-lg);
}

.note-section {
  padding: var(--spacing-md);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
}

.note-section ul {
  margin: 0;
  padding-left: var(--spacing-lg);
}

.note-section li {
  margin-bottom: var(--spacing-xs);
  line-height: 1.5;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .comparison-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-lg);
  }

  .notes-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }

  .comparison-column {
    padding: var(--spacing-md);
  }
}
</style>
