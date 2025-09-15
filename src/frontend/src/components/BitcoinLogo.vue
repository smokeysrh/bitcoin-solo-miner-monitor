<template>
  <img
    :src="logoSrc"
    :alt="altText"
    :aria-label="ariaLabel"
    :class="componentClasses"
    :style="componentStyles"
    @load="onLogoLoad"
    @error="onLogoError"
  />
</template>

<script>
import { computed, ref } from 'vue'

export default {
  name: 'BitcoinLogo',
  
  props: {
    // Size in pixels or preset ('xs', 'sm', 'md', 'lg', 'xl', 'hero')
    size: {
      type: [Number, String],
      default: 'md',
      validator: (value) => {
        if (typeof value === 'number') return value > 0 && value <= 256
        return ['xs', 'sm', 'md', 'lg', 'xl', 'hero'].includes(value)
      }
    },
    
    // Visual variant ('default', 'glow', 'subtle')
    variant: {
      type: String,
      default: 'default',
      validator: (value) => ['default', 'glow', 'subtle'].includes(value)
    },
    
    // Animation support
    animated: {
      type: Boolean,
      default: false
    },
    
    // Accessibility
    ariaLabel: {
      type: String,
      default: 'Bitcoin Logo'
    },
    
    // Custom alt text
    altText: {
      type: String,
      default: 'Bitcoin'
    }
  },

  emits: ['logo-error', 'logo-loaded'],

  setup(props, { emit }) {
    // Size mapping for preset values
    const SIZE_MAP = {
      xs: 16,
      sm: 24,
      md: 32,
      lg: 48,
      xl: 64,
      hero: 96
    }

    // State for error handling
    const logoError = ref(false)
    const logoLoaded = ref(false)

    // Computed property for logo source with smart size logic
    const logoSrc = computed(() => {
      const pixelSize = typeof props.size === 'number' ? props.size : SIZE_MAP[props.size]
      
      // Use SVG for sizes ≤32px (crisp rendering)
      // Use PNG for larger sizes (better quality)
      return pixelSize <= 32 ? '/bitcoin-symbol.svg' : '/bitcoin-symbol.png'
    })

    // Computed property for logo size in pixels
    const logoSize = computed(() => {
      return typeof props.size === 'number' ? props.size : SIZE_MAP[props.size]
    })

    // Computed classes for styling
    const componentClasses = computed(() => {
      const classes = ['bitcoin-logo']
      
      // Add size class
      if (typeof props.size === 'string') {
        classes.push(`bitcoin-logo--${props.size}`)
      }
      
      // Add variant class
      if (props.variant !== 'default') {
        classes.push(`bitcoin-logo--${props.variant}`)
      }
      
      // Add animation class
      if (props.animated) {
        classes.push('bitcoin-logo--animated')
      }
      
      return classes
    })

    // Computed styles for custom sizing
    const componentStyles = computed(() => {
      const styles = {}
      
      // Apply custom size if numeric
      if (typeof props.size === 'number') {
        styles.width = `${props.size}px`
        styles.height = `${props.size}px`
      }
      
      return styles
    })

    // Error handling methods
    const onLogoError = () => {
      logoError.value = true
      logoLoaded.value = false
      console.warn('Bitcoin logo failed to load:', logoSrc.value)
      emit('logo-error', { src: logoSrc.value, size: logoSize.value })
    }

    const onLogoLoad = () => {
      logoLoaded.value = true
      logoError.value = false
      emit('logo-loaded', { src: logoSrc.value, size: logoSize.value })
    }

    return {
      logoSrc,
      logoSize,
      componentClasses,
      componentStyles,
      logoError,
      logoLoaded,
      onLogoError,
      onLogoLoad
    }
  }
}
</script>

<style scoped>
/* Base logo styles */
.bitcoin-logo {
  display: inline-block;
  max-width: 100%;
  height: auto;
  transition: all 0.3s ease;
  object-fit: contain;
}

/* Size variants */
.bitcoin-logo--xs {
  width: 16px;
  height: 16px;
}

.bitcoin-logo--sm {
  width: 24px;
  height: 24px;
}

.bitcoin-logo--md {
  width: 32px;
  height: 32px;
}

.bitcoin-logo--lg {
  width: 48px;
  height: 48px;
}

.bitcoin-logo--xl {
  width: 64px;
  height: 64px;
}

.bitcoin-logo--hero {
  width: 96px;
  height: 96px;
}

/* Visual variants */
.bitcoin-logo--glow {
  filter: drop-shadow(0 0 8px rgba(247, 147, 26, 0.4));
}

.bitcoin-logo--subtle {
  opacity: 0.8;
}

/* Animation support */
.bitcoin-logo--animated {
  animation: bitcoin-logo-pulse 2s ease-in-out infinite;
}

@keyframes bitcoin-logo-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

/* Responsive design */
@media (max-width: 768px) {
  .bitcoin-logo--hero {
    width: 64px;
    height: 64px;
  }
  
  .bitcoin-logo--xl {
    width: 48px;
    height: 48px;
  }
}

/* Accessibility: Respect reduced motion preferences */
@media (prefers-reduced-motion: reduce) {
  .bitcoin-logo--animated {
    animation: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .bitcoin-logo--glow {
    filter: contrast(1.2) brightness(1.1);
  }
}

/* Focus styles for accessibility */
.bitcoin-logo:focus {
  outline: 2px solid var(--color-primary, #F7931A);
  outline-offset: 2px;
}
</style>