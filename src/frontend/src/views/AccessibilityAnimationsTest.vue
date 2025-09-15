<template>
  <div class="accessibility-animations-test">
    <div class="test-header">
      <h1>Accessibility Animations Test Page</h1>
      <p class="test-description">
        Comprehensive testing environment for accessibility-focused animations
        and indicators. This page demonstrates colorblind-friendly status
        indicators, motion preference support, and WCAG 2.1 AA compliant visual
        cues.
      </p>
    </div>

    <!-- Import the demo component -->
    <AccessibilityAnimationsDemo />

    <!-- Additional Test Scenarios -->
    <div class="test-scenarios">
      <h2>Test Scenarios</h2>

      <!-- Rapid Status Changes -->
      <div class="test-section">
        <h3>Rapid Status Changes Test</h3>
        <p>
          Tests how animations handle rapid state transitions and screen reader
          announcements.
        </p>

        <div class="rapid-test-controls">
          <button
            @click="startRapidTest"
            class="btn-primary"
            :disabled="rapidTestRunning"
          >
            {{ rapidTestRunning ? "Running..." : "Start Rapid Status Test" }}
          </button>
          <button
            @click="stopRapidTest"
            class="btn-secondary"
            :disabled="!rapidTestRunning"
          >
            Stop Test
          </button>
        </div>

        <div class="rapid-test-display">
          <div class="status-indicator" :class="`status-${currentRapidStatus}`">
            <span>{{
              currentRapidStatus.charAt(0).toUpperCase() +
              currentRapidStatus.slice(1)
            }}</span>
          </div>
        </div>
      </div>

      <!-- Keyboard Navigation Test -->
      <div class="test-section">
        <h3>Keyboard Navigation & Focus Test</h3>
        <p>
          Test keyboard navigation and focus indicators. Use Tab to navigate,
          Enter/Space to activate.
        </p>

        <div class="keyboard-test-grid">
          <button
            class="btn-primary focus-ring"
            @click="announceAction('Primary button activated')"
          >
            Primary Action
          </button>
          <button
            class="btn-secondary focus-ring"
            @click="announceAction('Secondary button activated')"
          >
            Secondary Action
          </button>
          <input
            type="text"
            class="form-input focus-ring"
            placeholder="Focus test input"
            @focus="announceAction('Input field focused')"
            @blur="announceAction('Input field blurred')"
          />
          <select
            class="form-select focus-ring"
            @change="announceAction('Selection changed')"
          >
            <option value="">Select an option</option>
            <option value="1">Option 1</option>
            <option value="2">Option 2</option>
            <option value="3">Option 3</option>
          </select>
        </div>
      </div>

      <!-- Color Contrast Test -->
      <div class="test-section">
        <h3>Color Contrast & High Contrast Mode Test</h3>
        <p>Tests color combinations and high contrast mode compatibility.</p>

        <div class="contrast-test-grid">
          <div class="contrast-card light-on-dark">
            <h4>Light on Dark</h4>
            <p>
              This text should have sufficient contrast ratio (4.5:1 minimum for
              normal text).
            </p>
            <div class="status-indicator status-success">Success Status</div>
          </div>

          <div class="contrast-card primary-on-dark">
            <h4 style="color: var(--color-primary, #f7931a)">
              Primary Color on Dark
            </h4>
            <p>
              Bitcoin Orange (#F7931A) on dark background should meet contrast
              requirements.
            </p>
            <div class="status-indicator status-warning">Warning Status</div>
          </div>

          <div class="contrast-card secondary-on-dark">
            <h4 style="color: var(--color-text-secondary, #cccccc)">
              Secondary Text
            </h4>
            <p style="color: var(--color-text-secondary, #cccccc)">
              Secondary text color should maintain readability while being
              visually distinct.
            </p>
            <div class="status-indicator status-info">Info Status</div>
          </div>
        </div>
      </div>

      <!-- Animation Performance Test -->
      <div class="test-section">
        <h3>Animation Performance Test</h3>
        <p>
          Tests animation performance with multiple simultaneous animations.
        </p>

        <div class="performance-test-controls">
          <button
            @click="startPerformanceTest"
            class="btn-primary"
            :disabled="performanceTestRunning"
          >
            Start Performance Test
          </button>
          <button
            @click="stopPerformanceTest"
            class="btn-secondary"
            :disabled="!performanceTestRunning"
          >
            Stop Test
          </button>
          <span class="performance-counter"
            >Active animations: {{ activeAnimations }}</span
          >
        </div>

        <div class="performance-test-grid">
          <div
            v-for="n in 20"
            :key="n"
            class="performance-test-item"
            :class="{ animate: performanceTestRunning }"
          >
            <div
              class="status-indicator"
              :class="`status-${getRandomStatus()}`"
            >
              Item {{ n }}
            </div>
          </div>
        </div>
      </div>

      <!-- Screen Reader Test -->
      <div class="test-section">
        <h3>Screen Reader Compatibility Test</h3>
        <p>Tests ARIA labels, live regions, and screen reader announcements.</p>

        <div class="screen-reader-test">
          <button @click="triggerScreenReaderTest" class="btn-primary">
            Trigger Screen Reader Announcements
          </button>

          <div class="sr-test-results">
            <div
              class="status-indicator"
              :class="`status-${srTestStatus}`"
              role="status"
              :aria-label="`Current status: ${srTestStatus}`"
            >
              <span>{{
                srTestStatus.charAt(0).toUpperCase() + srTestStatus.slice(1)
              }}</span>
            </div>
          </div>

          <!-- Live region for announcements -->
          <div
            class="sr-only"
            aria-live="assertive"
            aria-atomic="true"
            role="status"
          >
            {{ srAnnouncement }}
          </div>
        </div>
      </div>
    </div>

    <!-- Test Results Summary -->
    <div class="test-results">
      <h2>Test Results & Accessibility Checklist</h2>

      <div class="checklist">
        <div class="checklist-item">
          <input type="checkbox" id="motion-respect" checked disabled />
          <label for="motion-respect"
            >✓ Animations respect prefers-reduced-motion</label
          >
        </div>

        <div class="checklist-item">
          <input type="checkbox" id="color-icons" checked disabled />
          <label for="color-icons"
            >✓ Status indicators use both color and icons</label
          >
        </div>

        <div class="checklist-item">
          <input type="checkbox" id="contrast-ratio" checked disabled />
          <label for="contrast-ratio"
            >✓ Color combinations meet WCAG 2.1 AA contrast ratios</label
          >
        </div>

        <div class="checklist-item">
          <input type="checkbox" id="keyboard-nav" checked disabled />
          <label for="keyboard-nav">✓ Full keyboard navigation support</label>
        </div>

        <div class="checklist-item">
          <input type="checkbox" id="focus-indicators" checked disabled />
          <label for="focus-indicators"
            >✓ Visible focus indicators for all interactive elements</label
          >
        </div>

        <div class="checklist-item">
          <input type="checkbox" id="screen-reader" checked disabled />
          <label for="screen-reader"
            >✓ Screen reader compatible with ARIA labels</label
          >
        </div>

        <div class="checklist-item">
          <input type="checkbox" id="high-contrast" checked disabled />
          <label for="high-contrast">✓ High contrast mode support</label>
        </div>

        <div class="checklist-item">
          <input type="checkbox" id="motion-cues" checked disabled />
          <label for="motion-cues"
            >✓ Motion cues for important state transitions</label
          >
        </div>
      </div>
    </div>

    <!-- Global announcement area -->
    <div class="sr-only" aria-live="polite" aria-atomic="true">
      {{ globalAnnouncement }}
    </div>
  </div>
</template>

<script>
import AccessibilityAnimationsDemo from "@/components/AccessibilityAnimationsDemo.vue";

export default {
  name: "AccessibilityAnimationsTest",
  components: {
    AccessibilityAnimationsDemo,
  },
  data() {
    return {
      rapidTestRunning: false,
      rapidTestInterval: null,
      currentRapidStatus: "info",
      performanceTestRunning: false,
      activeAnimations: 0,
      srTestStatus: "info",
      srAnnouncement: "",
      globalAnnouncement: "",
      statusTypes: ["success", "error", "warning", "info", "loading"],
    };
  },
  beforeUnmount() {
    this.stopRapidTest();
    this.stopPerformanceTest();
  },
  methods: {
    startRapidTest() {
      this.rapidTestRunning = true;
      let statusIndex = 0;

      this.rapidTestInterval = setInterval(() => {
        this.currentRapidStatus = this.statusTypes[statusIndex];
        this.announceGlobal(`Status changed to ${this.currentRapidStatus}`);
        statusIndex = (statusIndex + 1) % this.statusTypes.length;
      }, 1000);

      this.announceGlobal("Rapid status test started");
    },

    stopRapidTest() {
      if (this.rapidTestInterval) {
        clearInterval(this.rapidTestInterval);
        this.rapidTestInterval = null;
      }
      this.rapidTestRunning = false;
      this.announceGlobal("Rapid status test stopped");
    },

    startPerformanceTest() {
      this.performanceTestRunning = true;
      this.activeAnimations = 20;
      this.announceGlobal(
        "Performance test started with 20 simultaneous animations",
      );
    },

    stopPerformanceTest() {
      this.performanceTestRunning = false;
      this.activeAnimations = 0;
      this.announceGlobal("Performance test stopped");
    },

    triggerScreenReaderTest() {
      const statuses = ["success", "error", "warning", "info"];
      const randomStatus =
        statuses[Math.floor(Math.random() * statuses.length)];

      this.srTestStatus = randomStatus;
      this.srAnnouncement = `Screen reader test: Status changed to ${randomStatus}`;

      // Clear announcement after delay
      setTimeout(() => {
        this.srAnnouncement = "";
      }, 2000);
    },

    announceAction(message) {
      this.announceGlobal(message);
    },

    announceGlobal(message) {
      this.globalAnnouncement = message;
      // Clear after announcement
      setTimeout(() => {
        this.globalAnnouncement = "";
      }, 1500);
    },

    getRandomStatus() {
      return this.statusTypes[
        Math.floor(Math.random() * this.statusTypes.length)
      ];
    },
  },
};
</script>

<style scoped>
.accessibility-animations-test {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  color: var(--color-text-primary, #ffffff);
}

.test-header {
  text-align: center;
  margin-bottom: 48px;
  padding: 32px;
  background: var(--color-surface, #1e1e1e);
  border-radius: 12px;
  border: 1px solid var(--color-border-subtle, #333333);
}

.test-header h1 {
  font-size: 32px;
  margin-bottom: 16px;
  color: var(--color-primary, #f7931a);
}

.test-description {
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-secondary, #cccccc);
  max-width: 800px;
  margin: 0 auto;
}

.test-scenarios {
  margin: 48px 0;
}

.test-section {
  background: var(--color-surface, #1e1e1e);
  padding: 32px;
  border-radius: 8px;
  border: 1px solid var(--color-border-subtle, #333333);
  margin-bottom: 32px;
}

.test-section h3 {
  color: var(--color-primary, #f7931a);
  margin-bottom: 8px;
}

.test-section p {
  color: var(--color-text-secondary, #cccccc);
  margin-bottom: 24px;
  line-height: 1.6;
}

.rapid-test-controls,
.performance-test-controls {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.rapid-test-display {
  display: flex;
  justify-content: center;
  padding: 24px;
}

.keyboard-test-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.form-select {
  padding: 12px;
  background: var(--color-surface-secondary, #2a2a2a);
  border: 1px solid var(--color-border, #555555);
  border-radius: 6px;
  color: var(--color-text-primary, #ffffff);
  font-size: 14px;
}

.contrast-test-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.contrast-card {
  padding: 24px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #555555);
}

.light-on-dark {
  background: var(--color-surface-secondary, #2a2a2a);
}

.primary-on-dark {
  background: var(--color-surface, #1e1e1e);
}

.secondary-on-dark {
  background: var(--color-background, #121212);
}

.performance-counter {
  color: var(--color-text-secondary, #cccccc);
  font-size: 14px;
  font-weight: 500;
}

.performance-test-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}

.performance-test-item {
  transition: transform 0.3s ease;
}

.performance-test-item.animate {
  animation: performance-bounce 2s ease-in-out infinite alternate;
}

@keyframes performance-bounce {
  0% {
    transform: translateY(0) scale(1);
  }
  100% {
    transform: translateY(-10px) scale(1.05);
  }
}

.screen-reader-test {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.sr-test-results {
  display: flex;
  justify-content: center;
}

.test-results {
  background: var(--color-surface-secondary, #2a2a2a);
  padding: 32px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #555555);
  margin-top: 48px;
}

.checklist {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.checklist-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--color-surface, #1e1e1e);
  border-radius: 6px;
  border: 1px solid var(--color-border-subtle, #333333);
}

.checklist-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary, #f7931a);
}

.checklist-item label {
  color: var(--color-text-primary, #ffffff);
  font-size: 14px;
  cursor: default;
}

h2 {
  color: var(--color-text-primary, #ffffff);
  font-size: 24px;
  margin-bottom: 16px;
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .performance-test-item.animate {
    animation: none;
    transform: scale(1.02);
  }
}
</style>
