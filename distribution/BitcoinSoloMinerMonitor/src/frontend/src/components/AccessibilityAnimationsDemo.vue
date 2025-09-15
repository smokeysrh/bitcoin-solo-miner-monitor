<template>
  <div class="accessibility-animations-demo">
    <h2>Accessibility-Focused Animations & Indicators</h2>
    <p class="demo-description">
      This demo showcases animations and indicators designed for accessibility,
      including colorblind-friendly status indicators and motion preference
      support.
    </p>

    <!-- Motion Preference Toggle -->
    <div class="motion-preference-section">
      <h3>Motion Preferences</h3>
      <button
        @click="toggleReducedMotion"
        class="btn-secondary motion-toggle"
        :class="{ 'reduced-motion': reducedMotion }"
      >
        {{ reducedMotion ? "Enable Animations" : "Reduce Motion" }}
      </button>
      <p class="motion-info">
        <span class="sr-only">Current motion setting: </span>
        {{
          reducedMotion ? "Reduced motion enabled" : "Full animations enabled"
        }}
      </p>
    </div>

    <!-- Status Indicators Section -->
    <div class="status-section">
      <h3>Status Indicators with Icons & Animations</h3>
      <div class="status-grid">
        <div class="status-indicator status-success">
          <span>Success</span>
          <span class="sr-only">Operation completed successfully</span>
        </div>

        <div class="status-indicator status-error">
          <span>Error</span>
          <span class="sr-only">Error occurred, please try again</span>
        </div>

        <div class="status-indicator status-warning">
          <span>Warning</span>
          <span class="sr-only">Warning: attention required</span>
        </div>

        <div class="status-indicator status-info">
          <span>Information</span>
          <span class="sr-only">Informational message</span>
        </div>

        <div class="status-indicator status-loading">
          <span>Loading</span>
          <span class="sr-only">Loading, please wait</span>
        </div>
      </div>
    </div>

    <!-- Connection Status Section -->
    <div class="connection-section">
      <h3>Connection Status Indicators</h3>
      <div class="connection-grid">
        <div class="status-indicator status-online">
          <span>Online</span>
          <span class="sr-only">Connection is active</span>
        </div>

        <div class="status-indicator status-offline">
          <span>Offline</span>
          <span class="sr-only">Connection lost</span>
        </div>
      </div>

      <button @click="toggleConnectionStatus" class="btn-primary">
        Toggle Connection Status
      </button>
    </div>

    <!-- State Transition Animations -->
    <div class="transitions-section">
      <h3>State Transition Animations</h3>
      <div class="transition-controls">
        <button
          @click="triggerAnimation('slide-in-right')"
          class="btn-secondary"
        >
          Slide In Right
        </button>
        <button
          @click="triggerAnimation('slide-in-left')"
          class="btn-secondary"
        >
          Slide In Left
        </button>
        <button @click="triggerAnimation('fade-in')" class="btn-secondary">
          Fade In
        </button>
        <button @click="triggerAnimation('scale-in')" class="btn-secondary">
          Scale In
        </button>
      </div>

      <div
        class="animation-target"
        :class="currentAnimation"
        :key="animationKey"
      >
        <div class="demo-card">
          <h4>Animated Content</h4>
          <p>
            This content demonstrates the
            {{ currentAnimation || "default" }} animation.
          </p>
        </div>
      </div>
    </div>

    <!-- Progress Indicators -->
    <div class="progress-section">
      <h3>Progress Indicators</h3>
      <div class="progress-demo">
        <label for="progress-bar">Loading Progress:</label>
        <div
          class="progress-bar"
          role="progressbar"
          :aria-valuenow="progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <span class="progress-text">{{ progress }}%</span>

        <button
          @click="startProgress"
          class="btn-primary"
          :disabled="progressRunning"
        >
          {{ progressRunning ? "Running..." : "Start Progress" }}
        </button>
      </div>
    </div>

    <!-- Interactive Elements -->
    <div class="interactive-section">
      <h3>Interactive Element Animations</h3>
      <div class="interactive-grid">
        <button class="btn-primary btn-press btn-glow focus-ring">
          Primary Button
        </button>

        <button class="btn-secondary btn-press focus-ring">
          Secondary Button
        </button>

        <div class="form-group">
          <label for="demo-input">Input with Focus Animation:</label>
          <input
            id="demo-input"
            type="text"
            class="form-input focus-ring"
            placeholder="Focus me to see animation"
          />
        </div>
      </div>
    </div>

    <!-- Loading States -->
    <div class="loading-section">
      <h3>Loading States</h3>
      <div class="loading-grid">
        <div class="loading-demo">
          <h4>Spinner Loading</h4>
          <div class="spinner" role="status" aria-label="Loading"></div>
        </div>

        <div class="loading-demo">
          <h4>Skeleton Loading</h4>
          <div class="skeleton-container">
            <div class="skeleton skeleton-text"></div>
            <div class="skeleton skeleton-text short"></div>
            <div class="skeleton skeleton-button"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Toast Notifications -->
    <div class="toast-section">
      <h3>Toast Notifications</h3>
      <div class="toast-controls">
        <button @click="showToast('success')" class="btn-secondary">
          Show Success Toast
        </button>
        <button @click="showToast('error')" class="btn-secondary">
          Show Error Toast
        </button>
        <button @click="showToast('warning')" class="btn-secondary">
          Show Warning Toast
        </button>
      </div>

      <div class="toast-container">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'toast',
            `toast-${toast.type}`,
            toast.entering ? 'toast-enter' : 'toast-exit',
          ]"
          role="alert"
          :aria-live="toast.type === 'error' ? 'assertive' : 'polite'"
        >
          <div class="status-indicator" :class="`status-${toast.type}`">
            <span>{{ toast.message }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Accessibility Information -->
    <div class="accessibility-info">
      <h3>Accessibility Features</h3>
      <ul>
        <li>
          ✓ All animations respect <code>prefers-reduced-motion</code> settings
        </li>
        <li>
          ✓ Status indicators use both color and icons for colorblind
          accessibility
        </li>
        <li>✓ Screen reader announcements for status changes</li>
        <li>✓ High contrast mode support</li>
        <li>✓ Keyboard navigation with focus indicators</li>
        <li>✓ ARIA labels and roles for assistive technologies</li>
        <li>✓ Motion cues for important state transitions</li>
      </ul>
    </div>

    <!-- Status Announcements for Screen Readers -->
    <div class="status-announcement" aria-live="polite" aria-atomic="true">
      {{ statusAnnouncement }}
    </div>
  </div>
</template>

<script>
export default {
  name: "AccessibilityAnimationsDemo",
  data() {
    return {
      reducedMotion: false,
      currentAnimation: "",
      animationKey: 0,
      progress: 0,
      progressRunning: false,
      toasts: [],
      toastId: 0,
      statusAnnouncement: "",
      connectionOnline: true,
    };
  },
  mounted() {
    // Check user's motion preference
    this.checkMotionPreference();

    // Apply reduced motion class if needed
    this.updateMotionPreference();
  },
  methods: {
    checkMotionPreference() {
      if (window.matchMedia) {
        const mediaQuery = window.matchMedia(
          "(prefers-reduced-motion: reduce)",
        );
        this.reducedMotion = mediaQuery.matches;

        // Listen for changes
        mediaQuery.addEventListener("change", (e) => {
          this.reducedMotion = e.matches;
          this.updateMotionPreference();
        });
      }
    },

    toggleReducedMotion() {
      this.reducedMotion = !this.reducedMotion;
      this.updateMotionPreference();
      this.announceStatus(
        `Motion ${this.reducedMotion ? "reduced" : "enabled"}`,
      );
    },

    updateMotionPreference() {
      if (this.reducedMotion) {
        document.body.classList.add("reduced-motion");
      } else {
        document.body.classList.remove("reduced-motion");
      }
    },

    triggerAnimation(animationType) {
      this.currentAnimation = animationType;
      this.animationKey++;
      this.announceStatus(`${animationType} animation triggered`);

      // Reset animation after it completes
      setTimeout(() => {
        this.currentAnimation = "";
      }, 500);
    },

    startProgress() {
      if (this.progressRunning) return;

      this.progressRunning = true;
      this.progress = 0;
      this.announceStatus("Progress started");

      const interval = setInterval(() => {
        this.progress += 2;

        if (this.progress >= 100) {
          clearInterval(interval);
          this.progressRunning = false;
          this.announceStatus("Progress completed");
        }
      }, 50);
    },

    toggleConnectionStatus() {
      this.connectionOnline = !this.connectionOnline;
      const status = this.connectionOnline ? "online" : "offline";
      this.announceStatus(`Connection is now ${status}`);
    },

    showToast(type) {
      const messages = {
        success: "Operation completed successfully!",
        error: "An error occurred. Please try again.",
        warning: "Warning: Please review your input.",
      };

      const toast = {
        id: this.toastId++,
        type,
        message: messages[type],
        entering: true,
      };

      this.toasts.push(toast);
      this.announceStatus(toast.message);

      // Remove toast after 3 seconds
      setTimeout(() => {
        toast.entering = false;
        setTimeout(() => {
          const index = this.toasts.indexOf(toast);
          if (index > -1) {
            this.toasts.splice(index, 1);
          }
        }, 300);
      }, 3000);
    },

    announceStatus(message) {
      this.statusAnnouncement = message;
      // Clear after announcement
      setTimeout(() => {
        this.statusAnnouncement = "";
      }, 1000);
    },
  },
};
</script>

<style scoped>
.accessibility-animations-demo {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.demo-description {
  color: var(--color-text-secondary, #cccccc);
  margin-bottom: 32px;
  font-size: 16px;
  line-height: 1.6;
}

.motion-preference-section {
  background: var(--color-surface, #1e1e1e);
  padding: 24px;
  border-radius: 8px;
  margin-bottom: 32px;
  border: 1px solid var(--color-border-subtle, #333333);
}

.motion-toggle {
  margin-right: 16px;
}

.motion-toggle.reduced-motion {
  background-color: var(--color-warning, #fb8c00);
  border-color: var(--color-warning, #fb8c00);
}

.motion-info {
  color: var(--color-text-secondary, #cccccc);
  font-size: 14px;
  margin-top: 8px;
}

.status-section,
.connection-section,
.transitions-section,
.progress-section,
.interactive-section,
.loading-section,
.toast-section {
  margin-bottom: 32px;
  background: var(--color-surface, #1e1e1e);
  padding: 24px;
  border-radius: 8px;
  border: 1px solid var(--color-border-subtle, #333333);
}

.status-grid,
.connection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.transition-controls,
.toast-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.animation-target {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.demo-card {
  background: var(--color-surface-secondary, #2a2a2a);
  padding: 24px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #555555);
  text-align: center;
  max-width: 300px;
}

.progress-demo {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-demo label {
  font-weight: 500;
  color: var(--color-text-primary, #ffffff);
}

.progress-text {
  font-size: 14px;
  color: var(--color-text-secondary, #cccccc);
  text-align: center;
}

.interactive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  align-items: start;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 500;
  color: var(--color-text-primary, #ffffff);
}

.form-input {
  padding: 12px;
  background: var(--color-surface-secondary, #2a2a2a);
  border: 1px solid var(--color-border, #555555);
  border-radius: 6px;
  color: var(--color-text-primary, #ffffff);
  font-size: 14px;
}

.form-input::placeholder {
  color: var(--color-text-hint, #999999);
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
}

.loading-demo {
  text-align: center;
}

.skeleton-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.skeleton-text {
  height: 16px;
  border-radius: 4px;
}

.skeleton-text.short {
  width: 60%;
}

.skeleton-button {
  height: 40px;
  width: 120px;
  border-radius: 6px;
  margin-top: 8px;
}

.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toast {
  min-width: 300px;
  background: var(--color-surface, #1e1e1e);
  border: 1px solid var(--color-border, #555555);
  border-radius: 8px;
  padding: 16px;
  box-shadow: var(--shadow-3, 0 8px 16px rgba(0, 0, 0, 0.4));
}

.accessibility-info {
  background: var(--color-surface-secondary, #2a2a2a);
  padding: 24px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #555555);
}

.accessibility-info ul {
  list-style: none;
  padding: 0;
  margin: 16px 0 0 0;
}

.accessibility-info li {
  padding: 8px 0;
  color: var(--color-text-secondary, #cccccc);
}

.accessibility-info code {
  background: var(--color-surface, #1e1e1e);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: "Courier New", monospace;
  color: var(--color-primary, #f7931a);
}

h2,
h3,
h4 {
  color: var(--color-text-primary, #ffffff);
  margin-bottom: 16px;
}

h2 {
  font-size: 28px;
  margin-bottom: 8px;
}

h3 {
  font-size: 20px;
  margin-bottom: 16px;
}

h4 {
  font-size: 16px;
  margin-bottom: 8px;
}

/* Reduced motion styles */
.reduced-motion * {
  animation-duration: 0.01s !important;
  animation-iteration-count: 1 !important;
  transition-duration: 0.01s !important;
}
</style>
