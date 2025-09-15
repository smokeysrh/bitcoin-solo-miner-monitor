<template>
  <div
    :class="spinnerClasses"
    :style="spinnerStyles"
    :aria-label="ariaLabel"
    role="status"
    aria-live="polite"
  >
    <!-- Bitcoin logo centered within the spinning ring -->
    <BitcoinLogo
      :size="logoSize"
      variant="default"
      :animated="false"
      :aria-label="`Bitcoin logo ${logoSize}px`"
      class="bitcoin-spinner__logo"
    />

    <!-- Spinning ring -->
    <div class="bitcoin-spinner__ring" :style="ringStyles"></div>

    <!-- Optional loading text -->
    <div v-if="showText" class="bitcoin-spinner__text" :style="textStyles">
      {{ loadingText }}
    </div>
  </div>
</template>

<script>
import { computed } from "vue";
import BitcoinLogo from "./BitcoinLogo.vue";

export default {
  name: "BitcoinLoadingSpinner",

  components: {
    BitcoinLogo,
  },

  props: {
    // Size variants: 'sm', 'md', 'lg', 'xl' or custom number
    size: {
      type: [String, Number],
      default: "md",
      validator: (value) => {
        if (typeof value === "number") return value > 0;
        return ["sm", "md", "lg", "xl"].includes(value);
      },
    },

    // Loading text to display
    loadingText: {
      type: String,
      default: "Loading...",
    },

    // Whether to show loading text
    showText: {
      type: Boolean,
      default: true,
    },

    // Spinner color (defaults to primary color)
    color: {
      type: String,
      default: null,
    },

    // Animation speed: 'slow', 'normal', 'fast'
    speed: {
      type: String,
      default: "normal",
      validator: (value) => ["slow", "normal", "fast"].includes(value),
    },

    // Accessibility label
    ariaLabel: {
      type: String,
      default: "Loading",
    },

    // Whether to center the spinner
    centered: {
      type: Boolean,
      default: false,
    },
  },

  setup(props) {
    // Size mapping for container
    const sizeMap = {
      sm: 48,
      md: 64,
      lg: 96,
      xl: 128,
    };

    // Logo size mapping (smaller than container)
    const logoSizeMap = {
      sm: 24,
      md: 32,
      lg: 48,
      xl: 64,
    };

    // Animation duration mapping
    const speedMap = {
      slow: "2s",
      normal: "1.5s",
      fast: "1s",
    };

    // Computed container size
    const containerSize = computed(() => {
      if (typeof props.size === "number") {
        return props.size;
      }
      return sizeMap[props.size] || sizeMap.md;
    });

    // Computed logo size
    const logoSize = computed(() => {
      if (typeof props.size === "number") {
        return Math.round(props.size * 0.5); // Logo is 50% of container
      }
      return logoSizeMap[props.size] || logoSizeMap.md;
    });

    // Spinner classes
    const spinnerClasses = computed(() => {
      const classes = ["bitcoin-spinner"];

      if (props.centered) {
        classes.push("bitcoin-spinner--centered");
      }

      return classes;
    });

    // Spinner styles
    const spinnerStyles = computed(() => {
      const size = containerSize.value;

      return {
        width: `${size}px`,
        height: `${size}px`,
      };
    });

    // Ring styles
    const ringStyles = computed(() => {
      const size = containerSize.value;
      const borderWidth = Math.max(2, Math.round(size * 0.03)); // 3% of size, min 2px
      const color = props.color || "var(--color-primary, #F7931A)";
      const duration = speedMap[props.speed];

      return {
        width: `${size}px`,
        height: `${size}px`,
        borderWidth: `${borderWidth}px`,
        borderTopColor: color,
        animationDuration: duration,
      };
    });

    // Text styles
    const textStyles = computed(() => {
      const size = containerSize.value;
      const fontSize = Math.max(12, Math.round(size * 0.125)); // 12.5% of size, min 12px
      const marginTop = Math.round(size * 0.125); // 12.5% of size

      return {
        fontSize: `${fontSize}px`,
        marginTop: `${marginTop}px`,
      };
    });

    return {
      logoSize,
      spinnerClasses,
      spinnerStyles,
      ringStyles,
      textStyles,
    };
  },
};
</script>

<style scoped>
.bitcoin-spinner {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.bitcoin-spinner--centered {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.bitcoin-spinner__logo {
  position: relative;
  z-index: 2;
}

.bitcoin-spinner__ring {
  position: absolute;
  top: 0;
  left: 0;
  border: 2px solid transparent;
  border-top: 2px solid var(--color-primary, #f7931a);
  border-radius: 50%;
  animation: bitcoin-spinner-rotate 1.5s linear infinite;
  z-index: 1;
}

.bitcoin-spinner__text {
  color: var(--color-text-secondary, #cccccc);
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  margin-top: 8px;
  white-space: nowrap;
}

@keyframes bitcoin-spinner-rotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Accessibility: Respect reduced motion preferences */
@media (prefers-reduced-motion: reduce) {
  .bitcoin-spinner__ring {
    animation: none !important;
    border-top-color: transparent;
    border-left-color: var(--color-primary, #f7931a);
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .bitcoin-spinner__ring {
    border-top-color: currentColor;
  }

  .bitcoin-spinner__text {
    color: currentColor;
  }
}
</style>
