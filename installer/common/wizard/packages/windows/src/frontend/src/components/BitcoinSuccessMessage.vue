<template>
  <div
    :class="messageClasses"
    :style="messageStyles"
    role="alert"
    aria-live="polite"
  >
    <!-- Success icon with Bitcoin logo -->
    <div class="bitcoin-success__icon-container">
      <BitcoinLogo
        size="sm"
        variant="glow"
        :animated="animated"
        alt-text="Bitcoin Success"
        aria-label="Bitcoin Success Logo"
        class="bitcoin-success__logo"
        @logo-error="onLogoError"
        @logo-loaded="onLogoLoaded"
      />

      <!-- Success checkmark overlay -->
      <div class="bitcoin-success__checkmark" :style="checkmarkStyles">
        <svg
          :width="checkmarkSize"
          :height="checkmarkSize"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M9 12L11 14L15 10"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="bitcoin-success__checkmark-path"
          />
        </svg>
      </div>
    </div>

    <!-- Message content -->
    <div class="bitcoin-success__content">
      <h3 v-if="title" class="bitcoin-success__title" :style="titleStyles">
        {{ title }}
      </h3>

      <p
        v-if="message"
        class="bitcoin-success__message"
        :style="messageTextStyles"
      >
        {{ message }}
      </p>

      <!-- Action buttons -->
      <div v-if="showActions" class="bitcoin-success__actions">
        <slot name="actions">
          <v-btn
            v-if="primaryAction"
            color="primary"
            variant="elevated"
            @click="$emit('primary-action')"
            class="bitcoin-success__action-primary"
          >
            {{ primaryAction }}
          </v-btn>

          <v-btn
            v-if="secondaryAction"
            variant="text"
            @click="$emit('secondary-action')"
            class="bitcoin-success__action-secondary"
          >
            {{ secondaryAction }}
          </v-btn>
        </slot>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from "vue";
import BitcoinLogo from "./BitcoinLogo.vue";

export default {
  name: "BitcoinSuccessMessage",

  components: {
    BitcoinLogo,
  },

  emits: ["primary-action", "secondary-action", "logo-error", "logo-loaded"],

  props: {
    // Success message title
    title: {
      type: String,
      default: "Success!",
    },

    // Success message text
    message: {
      type: String,
      default: null,
    },

    // Size variants: 'sm', 'md', 'lg'
    size: {
      type: String,
      default: "md",
      validator: (value) => ["sm", "md", "lg"].includes(value),
    },

    // Whether to animate the logo
    animated: {
      type: Boolean,
      default: true,
    },

    // Primary action button text
    primaryAction: {
      type: String,
      default: null,
    },

    // Secondary action button text
    secondaryAction: {
      type: String,
      default: null,
    },

    // Whether to show action buttons
    showActions: {
      type: Boolean,
      default: true,
    },

    // Layout variant: 'vertical', 'horizontal'
    layout: {
      type: String,
      default: "vertical",
      validator: (value) => ["vertical", "horizontal"].includes(value),
    },

    // Whether to center the message
    centered: {
      type: Boolean,
      default: false,
    },
  },

  setup(props, { emit }) {
    // Size mappings
    const iconSizeMap = {
      sm: 48,
      md: 64,
      lg: 96,
    };

    const checkmarkSizeMap = {
      sm: 16,
      md: 20,
      lg: 24,
    };

    const titleSizeMap = {
      sm: "1.25rem",
      md: "1.5rem",
      lg: "2rem",
    };

    const messageSizeMap = {
      sm: "0.875rem",
      md: "1rem",
      lg: "1.125rem",
    };

    // Computed sizes
    const iconSize = computed(() => iconSizeMap[props.size]);
    const checkmarkSize = computed(() => checkmarkSizeMap[props.size]);

    // Message classes
    const messageClasses = computed(() => {
      const classes = ["bitcoin-success"];

      classes.push(`bitcoin-success--${props.layout}`);
      classes.push(`bitcoin-success--${props.size}`);

      if (props.centered) {
        classes.push("bitcoin-success--centered");
      }

      return classes;
    });

    // Message styles
    const messageStyles = computed(() => {
      return {};
    });

    // Checkmark styles
    const checkmarkStyles = computed(() => {
      const size = checkmarkSize.value;
      const offset = Math.round(iconSize.value * 0.15); // 15% offset from bottom-right

      return {
        width: `${size + 8}px`, // Add padding for background
        height: `${size + 8}px`,
        bottom: `${offset}px`,
        right: `${offset}px`,
      };
    });

    // Title styles
    const titleStyles = computed(() => {
      return {
        fontSize: titleSizeMap[props.size],
      };
    });

    // Message text styles
    const messageTextStyles = computed(() => {
      return {
        fontSize: messageSizeMap[props.size],
      };
    });

    // Logo event handlers
    const onLogoError = (errorData) => {
      console.warn('Bitcoin logo failed to load in success message:', errorData);
      emit('logo-error', errorData);
    };

    const onLogoLoaded = (loadData) => {
      emit('logo-loaded', loadData);
    };

    return {
      iconSize,
      checkmarkSize,
      messageClasses,
      messageStyles,
      checkmarkStyles,
      titleStyles,
      messageTextStyles,
      onLogoError,
      onLogoLoaded,
    };
  },
};
</script>

<style scoped>
.bitcoin-success {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--color-surface, #1e1e1e);
  border: 1px solid var(--color-success, #4caf50);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.1);
}

.bitcoin-success--vertical {
  flex-direction: column;
  text-align: center;
}

.bitcoin-success--horizontal {
  flex-direction: row;
  text-align: left;
}

.bitcoin-success--centered {
  margin: 0 auto;
  max-width: fit-content;
}

.bitcoin-success--sm {
  padding: 1rem;
  gap: 0.75rem;
}

.bitcoin-success--lg {
  padding: 2rem;
  gap: 1.5rem;
}

.bitcoin-success__icon-container {
  position: relative;
  flex-shrink: 0;
}

.bitcoin-success__logo {
  display: block;
  position: relative;
  z-index: 1;
}

.bitcoin-success__checkmark {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-success, #4caf50);
  color: white;
  border-radius: 50%;
  border: 2px solid var(--color-surface, #1e1e1e);
  animation: bitcoin-success-checkmark 0.6s ease-out;
  z-index: 2;
}

.bitcoin-success__checkmark-path {
  animation: bitcoin-success-checkmark-draw 0.4s ease-out 0.2s both;
  stroke-dasharray: 20;
  stroke-dashoffset: 20;
}

.bitcoin-success__content {
  flex: 1;
  min-width: 0;
}

.bitcoin-success__title {
  margin: 0 0 0.5rem 0;
  font-weight: 600;
  color: var(--color-success, #4caf50);
  line-height: 1.2;
}

.bitcoin-success__message {
  margin: 0 0 1rem 0;
  color: var(--color-text-primary, #ffffff);
  line-height: 1.4;
}

.bitcoin-success__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.bitcoin-success--vertical .bitcoin-success__actions {
  justify-content: center;
}

.bitcoin-success--horizontal .bitcoin-success__actions {
  justify-content: flex-start;
}

.bitcoin-success__action-primary {
  min-width: 120px;
}

.bitcoin-success__action-secondary {
  min-width: 100px;
}

/* Animations */
@keyframes bitcoin-success-checkmark {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes bitcoin-success-checkmark-draw {
  to {
    stroke-dashoffset: 0;
  }
}

/* Accessibility: Respect reduced motion preferences */
@media (prefers-reduced-motion: reduce) {
  .bitcoin-success__checkmark,
  .bitcoin-success__checkmark-path {
    animation: none !important;
  }

  .bitcoin-success__checkmark {
    opacity: 1;
    transform: scale(1);
  }

  .bitcoin-success__checkmark-path {
    stroke-dashoffset: 0;
  }
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .bitcoin-success--horizontal {
    flex-direction: column;
    text-align: center;
  }

  .bitcoin-success__actions {
    justify-content: center !important;
  }
}
</style>
