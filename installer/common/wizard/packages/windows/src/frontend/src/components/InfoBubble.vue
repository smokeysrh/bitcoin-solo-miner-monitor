<template>
  <div class="info-bubble-container">
    <v-tooltip 
      :model-value="showTooltip" 
      location="bottom"
      :open-on-hover="true"
      :open-on-click="false"
    >
      <template v-slot:activator="{ props }">
        <v-btn
          icon
          size="small"
          variant="text"
          v-bind="props"
          @mouseenter="handleHover"
          @mouseleave="handleHoverEnd"
          @click="handleClick"
          :class="['info-bubble', { 'info-bubble--hovered': isHovered, 'info-bubble--clicked': isClicked }]"
          :aria-label="`Information about ${ariaLabel}`"
        >
          <v-icon 
            :class="['info-bubble-icon', { 'info-bubble-icon--hovered': isHovered }]"
            :color="iconColor"
          >
            mdi-help-circle-outline
          </v-icon>
        </v-btn>
      </template>
      <div class="info-bubble-tooltip">
        {{ tooltipText }}
      </div>
    </v-tooltip>

    <!-- Detailed Information Dialog -->
    <v-dialog 
      v-model="showDialog" 
      max-width="500px"
      :persistent="false"
    >
      <v-card class="info-bubble-dialog">
        <v-card-title class="info-bubble-dialog-title">
          <v-icon left color="primary">mdi-information-outline</v-icon>
          {{ dialogTitle }}
        </v-card-title>
        <v-card-text class="info-bubble-dialog-content">
          <div v-if="dialogContent" v-html="dialogContent"></div>
          <div v-else>{{ tooltipText }}</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn 
            color="primary" 
            variant="text" 
            @click="closeDialog"
          >
            Got it
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed } from 'vue';

export default {
  name: 'InfoBubble',
  props: {
    tooltipText: {
      type: String,
      required: true,
      default: 'Information'
    },
    dialogTitle: {
      type: String,
      default: 'Information'
    },
    dialogContent: {
      type: String,
      default: null
    },
    ariaLabel: {
      type: String,
      default: 'this section'
    },
    size: {
      type: String,
      default: 'small',
      validator: (value) => ['x-small', 'small', 'default', 'large'].includes(value)
    },
    hoverColor: {
      type: String,
      default: 'primary'
    }
  },
  emits: ['click', 'hover', 'hover-end'],
  setup(props, { emit }) {
    // Reactive state
    const isHovered = ref(false);
    const isClicked = ref(false);
    const showTooltip = ref(false);
    const showDialog = ref(false);

    // Computed properties
    const iconColor = computed(() => {
      if (isClicked.value) return props.hoverColor;
      if (isHovered.value) return props.hoverColor;
      return 'grey-lighten-1';
    });

    // Methods
    const handleHover = () => {
      isHovered.value = true;
      showTooltip.value = true;
      emit('hover');
    };

    const handleHoverEnd = () => {
      isHovered.value = false;
      // Keep tooltip visible for a short time to allow interaction
      setTimeout(() => {
        if (!isHovered.value) {
          showTooltip.value = false;
        }
      }, 100);
      emit('hover-end');
    };

    const handleClick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      
      isClicked.value = true;
      showDialog.value = true;
      
      // Reset clicked state after animation
      setTimeout(() => {
        isClicked.value = false;
      }, 200);
      
      emit('click');
    };

    const closeDialog = () => {
      showDialog.value = false;
    };

    return {
      // State
      isHovered,
      isClicked,
      showTooltip,
      showDialog,
      
      // Computed
      iconColor,
      
      // Methods
      handleHover,
      handleHoverEnd,
      handleClick,
      closeDialog
    };
  }
};
</script>

<style scoped>
.info-bubble-container {
  display: inline-block;
  position: relative;
}

.info-bubble {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 50%;
  min-width: 24px !important;
  width: 24px !important;
  height: 24px !important;
}

.info-bubble:hover {
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
}

.info-bubble--hovered {
  transform: scale(1.15);
  background-color: rgba(var(--v-theme-primary), 0.12) !important;
}

.info-bubble--clicked {
  transform: scale(0.95);
}

.info-bubble-icon {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 18px !important;
}

.info-bubble-icon--hovered {
  transform: scale(1.1);
  filter: drop-shadow(0 2px 4px rgba(var(--v-theme-primary), 0.3));
}

.info-bubble-tooltip {
  font-size: 14px;
  line-height: 1.4;
  max-width: 250px;
  padding: 8px 12px;
  background-color: var(--v-theme-surface-variant);
  color: var(--v-theme-on-surface-variant);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(var(--v-theme-outline), 0.2);
}

.info-bubble-dialog {
  background-color: var(--v-theme-surface);
  border: 1px solid rgba(var(--v-theme-outline), 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.info-bubble-dialog-title {
  background-color: var(--v-theme-surface-variant);
  color: var(--v-theme-on-surface-variant);
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.2);
  font-weight: 600;
  padding: 16px 24px;
}

.info-bubble-dialog-content {
  padding: 20px 24px;
  color: var(--v-theme-on-surface);
  line-height: 1.6;
}

.info-bubble-dialog-content :deep(ul) {
  margin: 12px 0;
  padding-left: 20px;
}

.info-bubble-dialog-content :deep(li) {
  margin: 6px 0;
}

.info-bubble-dialog-content :deep(strong) {
  font-weight: 600;
  color: var(--v-theme-primary);
}

/* Accessibility improvements */
.info-bubble:focus-visible {
  outline: 2px solid var(--v-theme-primary);
  outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .info-bubble {
    border: 1px solid var(--v-theme-outline);
  }
  
  .info-bubble-tooltip {
    border-width: 2px;
  }
  
  .info-bubble-dialog {
    border-width: 2px;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .info-bubble,
  .info-bubble-icon {
    transition: none;
  }
  
  .info-bubble--hovered,
  .info-bubble--clicked {
    transform: none;
  }
  
  .info-bubble-icon--hovered {
    transform: none;
    filter: none;
  }
}

/* Dark theme adjustments */
@media (prefers-color-scheme: dark) {
  .info-bubble-tooltip {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }
  
  .info-bubble-dialog {
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  }
}
</style>