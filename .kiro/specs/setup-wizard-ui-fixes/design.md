# Design Document

## Overview

This design addresses four critical UI issues in the setup wizard that prevent proper user interaction and navigation. The solution focuses on fixing Vuetify component rendering, CSS styling conflicts, layout overflow issues, and progress indicator state management. The fixes will ensure the setup wizard provides a smooth, functional user experience across all steps.

## Architecture

The setup wizard is built using Vue.js with Vuetify components in a fullscreen layout. The main components involved are:

- **FirstRunWizard.vue**: Main wizard container with progress tracking
- **Individual Screen Components**: WelcomeScreen, NetworkDiscoveryScreen, SettingsConfigScreen, UserPreferencesScreen, CompletionScreen
- **Vuetify Components**: v-select (dropdowns), v-switch (sliders), v-progress-linear (progress bar)

The issues stem from CSS z-index conflicts, incomplete CSS state management, layout overflow, and progress state synchronization problems.

## Components and Interfaces

### 1. Dropdown Menu Component Fixes

**Problem**: v-select dropdowns show arrow animation but no menu options appear.

**Root Cause Analysis**: 
- Z-index conflicts with wizard overlay positioning
- Vuetify overlay content being rendered behind wizard elements
- Potential CSS pointer-events interference

**Solution**:
- Ensure v-select overlay content has proper z-index hierarchy
- Fix CSS deep selectors for dropdown positioning
- Verify menu attachment and portal rendering
- Add explicit z-index values for dropdown overlays

**Implementation Details**:
```css
/* Ensure dropdown overlays appear above wizard content */
:deep(.v-overlay__content) {
  z-index: 10001 !important;
}

:deep(.v-menu > .v-overlay__content) {
  z-index: 10001 !important;
}

:deep(.v-select__content) {
  z-index: 10001 !important;
}

/* Ensure proper menu attachment */
:deep(.v-select .v-overlay__content) {
  position: fixed !important;
}
```

### 2. Switch/Slider Visual State Component

**Problem**: v-switch components remain orange regardless of on/off state.

**Root Cause Analysis**:
- CSS selectors not properly targeting different switch states
- Vuetify's state classes may have changed or are being overridden
- Color inheritance from theme variables

**Solution**:
- Update CSS selectors to properly target switch states
- Use correct Vuetify state classes for on/off states
- Implement proper color transitions between states

**Implementation Details**:
```css
/* Off state - Grey track */
:deep(.v-switch .v-switch__track) {
  background-color: #9e9e9e !important;
  opacity: 1 !important;
}

/* On state - Orange track */
:deep(.v-switch.v-input--dirty .v-switch__track),
:deep(.v-switch input:checked + .v-switch__track) {
  background-color: #ff9800 !important;
  opacity: 1 !important;
}

/* Ensure thumb remains white in both states */
:deep(.v-switch .v-switch__thumb) {
  background-color: #ffffff !important;
}
```

### 3. Scrollable Content Layout Component

**Problem**: Setup wizard steps have no scrolling, hiding content and Continue buttons.

**Root Cause Analysis**:
- Fixed height containers without overflow handling
- CSS flex layout preventing proper scrolling
- Content exceeding viewport height without scroll containers

**Solution**:
- Implement proper overflow-y: auto on step content containers
- Ensure flex layout allows content to scroll while maintaining header/footer
- Add minimum heights and proper container sizing

**Implementation Details**:
```css
.step-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: var(--spacing-lg);
  max-height: calc(100vh - 280px); /* Account for header and footer */
}

/* Ensure scrollable content on mobile */
@media (max-width: 960px) {
  .step-content {
    max-height: calc(100vh - 320px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }
}
```

### 4. Progress Indicator State Management

**Problem**: Progress bar doesn't fill with color as user progresses through steps.

**Root Cause Analysis**:
- Progress calculation not updating properly
- CSS styling overriding progress bar colors
- State management not triggering visual updates

**Solution**:
- Ensure progress calculation is reactive to currentStep changes
- Fix CSS that may be overriding progress bar styling
- Add proper color transitions and visual feedback

**Implementation Details**:
```javascript
// Ensure reactive progress calculation
computed: {
  progressPercentage() {
    return (this.currentStep / 5) * 100;
  }
}

// Update progress bar binding
<v-progress-linear
  :value="progressPercentage"
  color="primary"
  height="6"
  class="mb-0"
></v-progress-linear>
```

## Data Models

### Wizard State Model
```javascript
{
  currentStep: Number,        // 1-5, tracks current wizard step
  experienceLevel: String,    // User's selected experience level
  foundMiners: Array,         // Discovered miners from network scan
  settings: Object,           // Configuration settings from step 3
  preferences: Object         // User preferences from step 4
}
```

### Progress State Model
```javascript
{
  totalSteps: 5,
  currentStep: Number,
  completedSteps: Array,      // Array of completed step numbers
  progressPercentage: Number  // Calculated percentage for progress bar
}
```

## Error Handling

### Dropdown Rendering Failures
- Fallback to native select elements if Vuetify dropdowns fail to render
- Console logging for debugging z-index and overlay issues
- Graceful degradation for accessibility

### Switch State Inconsistencies
- Validate switch state on component mount
- Force re-render if visual state doesn't match data state
- Provide keyboard navigation alternatives

### Scroll Container Issues
- Detect viewport height changes and adjust container sizing
- Provide scroll indicators when content overflows
- Ensure touch scrolling works on mobile devices

### Progress Tracking Errors
- Validate step transitions and prevent invalid states
- Persist progress state to localStorage for recovery
- Handle browser refresh scenarios gracefully

## Testing Strategy

### Unit Tests
- Test dropdown menu rendering and option selection
- Verify switch component state changes and visual updates
- Test scroll container behavior with varying content heights
- Validate progress bar calculations and visual updates

### Integration Tests
- Test complete wizard flow with all UI interactions
- Verify responsive behavior across different screen sizes
- Test keyboard navigation and accessibility features
- Validate state persistence across browser sessions

### Visual Regression Tests
- Screenshot comparisons for dropdown menu appearance
- Switch component visual states (on/off)
- Progress bar color filling at each step
- Scroll behavior on different content lengths

### Browser Compatibility Tests
- Test dropdown functionality across major browsers
- Verify CSS styling consistency
- Test touch scrolling on mobile devices
- Validate z-index behavior in different browser engines

### Accessibility Tests
- Screen reader compatibility for all interactive elements
- Keyboard navigation through wizard steps
- High contrast mode support
- Focus management during step transitions

## Implementation Approach

1. **Phase 1**: Fix dropdown z-index and overlay positioning issues
2. **Phase 2**: Correct switch component visual state styling
3. **Phase 3**: Implement proper scrollable layout containers
4. **Phase 4**: Fix progress bar state management and visual updates
5. **Phase 5**: Add comprehensive testing and validation

Each phase will be implemented incrementally with testing to ensure no regressions are introduced while fixing the identified issues.