# Design Document

## Overview

This design addresses critical UI/UX issues in the setup wizard that are preventing users from completing the onboarding process successfully. The fixes focus on navigation responsiveness, visual consistency, proper asset usage, and removing unnecessary complexity while maintaining the existing Vue.js/Vuetify architecture.

The setup wizard consists of 5 screens (Welcome, Discovery, Settings, Preferences, Complete) managed by the `FirstRunWizard.vue` component, with individual screen components in the `wizard/` directory. The current implementation has several issues that need to be resolved to provide a smooth user experience.

## Architecture

### Current Structure
- **Main Component**: `FirstRunWizard.vue` - Orchestrates the wizard flow
- **Screen Components**: Individual Vue components for each step
- **Service Layer**: `firstRunService.js` - Handles setup data persistence
- **Asset Management**: `BitcoinLogo.vue` component for logo display

### Component Hierarchy
```
FirstRunSetup.vue (View)
└── FirstRunWizard.vue (Main Wizard)
    ├── WelcomeScreen.vue
    ├── NetworkDiscoveryScreen.vue
    ├── SettingsConfigScreen.vue
    ├── UserPreferencesScreen.vue
    └── CompletionScreen.vue
```

## Components and Interfaces

### 1. Navigation Bar Positioning System

**Problem**: Navigation buttons (continue/back) are currently stuck and unresponsive to scrolling.

**Solution**: Implement a footer-based navigation system where buttons are positioned at the bottom of each page content.

**Interface Changes**:
- Modify each screen component's footer structure
- Ensure navigation bar is positioned at bottom of page content (not viewport)
- Remove any fixed positioning that interferes with scrolling

**CSS Architecture**:
```css
.screen-container {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.screen-content {
  flex: 1;
  overflow: visible;
}

.screen-footer {
  flex-shrink: 0;
  position: static; /* Not fixed */
  margin-top: auto;
}
```

### 2. Bitcoin Logo Asset Management System

**Problem**: Multiple logo implementations using custom-built logos with off-center "B".

**Solution**: Centralize logo usage through the existing `BitcoinLogo.vue` component and update it to use the provided assets.

**Asset Integration**:
- Update `BitcoinLogo.vue` to use `bitcoin-symbol.png` and `bitcoin-symbol.svg` from root directory
- Create asset mapping system for different sizes
- Audit all components for direct logo usage and replace with `BitcoinLogo` component

**Component Interface**:
```javascript
// Updated logoSrc computation in BitcoinLogo.vue
const logoSrc = computed(() => {
  // Use root directory assets instead of assets/images
  if (size <= 32) {
    return '/bitcoin-symbol.svg';
  } else {
    return '/bitcoin-symbol.png';
  }
});
```

### 3. Widget Selection Highlighting System

**Problem**: Step 4 dashboard widget selection doesn't highlight selected widgets.

**Solution**: Enhance the `v-item-group` implementation in `UserPreferencesScreen.vue` with proper visual feedback.

**Implementation**:
- Fix the `v-item` selection state binding
- Add distinct visual indicators for selected/unselected states
- Ensure multiple selection works correctly

**CSS Classes**:
```css
.widget-card--selected {
  background: rgb(var(--v-theme-primary));
  color: white;
  border: 2px solid rgb(var(--v-theme-primary));
}

.widget-card--unselected {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-outline-variant));
}
```

### 4. Dropdown Menu Overlay System

**Problem**: Dropdown menu titles are clouded by dropdown box outlines when hovering.

**Solution**: Fix z-index layering and improve text contrast in dropdown menus.

**Z-Index Architecture**:
```css
.v-overlay { z-index: 10001; }
.v-menu { z-index: 10002; }
.v-list { z-index: 10003; }
.v-list-item-title { 
  color: inherit;
  position: relative;
  z-index: 1;
}
```

### 5. Chart Selection Simplification System

**Problem**: Dropdown for chart selection offers multiple options when only line charts are supported.

**Solution**: Remove chart type dropdown and default to line charts only.

**Implementation**:
- Remove `chart_type` selection from `UserPreferencesScreen.vue`
- Update `chartTypeOptions` to only include line charts
- Simplify the preferences data model

### 6. Completion Page Content Management

**Problem**: References to unavailable video tutorials on completion page.

**Solution**: Remove video tutorial references and clean up completion page content.

**Content Updates**:
- Remove "Video Tutorials" button from help section
- Update help section to only show available resources
- Streamline completion page content

### 7. Dashboard Navigation System

**Problem**: "Launch Dashboard" button doesn't navigate to dashboard.

**Solution**: Fix the navigation logic in `CompletionScreen.vue`.

**Implementation**:
```javascript
// In CompletionScreen.vue
methods: {
  launchDashboard() {
    this.$emit('finish'); // This should trigger navigation
  }
}
```

**Router Integration**:
- Ensure `FirstRunSetup.vue` properly handles the `setup-complete` event
- Verify `firstRunService.getInitialRoute()` returns correct dashboard route

### 8. Information Bubble Styling System

**Problem**: Information bubbles have inconsistent colors throughout the wizard.

**Solution**: Standardize all information bubbles to match step 3 "settings" info bubble styling.

**CSS Variables**:
```css
:root {
  --info-bubble-bg: rgb(var(--v-theme-info-container));
  --info-bubble-text: rgb(var(--v-theme-on-info-container));
  --info-bubble-border: rgb(var(--v-theme-info));
}

.info-bubble {
  background: var(--info-bubble-bg);
  color: var(--info-bubble-text);
  border: 1px solid var(--info-bubble-border);
}
```

### 9. Email Settings Integration System

**Problem**: Email notifications offered without corresponding settings section.

**Solution**: Add email configuration to settings or remove email notification options.

**Implementation Options**:
1. Add email field to notification preferences
2. Remove email notification references until email system is implemented

**Recommended Approach**: Add email input field to `UserPreferencesScreen.vue`:
```javascript
preferences: {
  email_notifications: false,
  email_address: '',
  // ... other preferences
}
```

### 10. Accent Color Theme Integration

**Problem**: Accent color choices don't match the rest of the application theme.

**Solution**: Update accent color options to use theme-consistent colors.

**Color Palette**:
```javascript
accentColorOptions: [
  { title: "Bitcoin Orange", value: "#f7931a" },
  { title: "Primary Blue", value: "rgb(var(--v-theme-primary))" },
  { title: "Success Green", value: "rgb(var(--v-theme-success))" },
  { title: "Warning Amber", value: "rgb(var(--v-theme-warning))" },
  // Remove colors that don't match theme
]
```

### 11. Progress Bar Visual Feedback System

**Problem**: Progress bar doesn't fill with orange color as steps are completed.

**Solution**: Fix the progress bar styling and color application.

**CSS Implementation**:
```css
.progress-bar-custom :deep(.v-progress-linear__determinate) {
  background-color: #ff9800 !important; /* Orange color */
}

.progress-bar-custom :deep(.v-progress-linear__background) {
  background-color: rgba(255, 152, 0, 0.2) !important;
}
```

## Data Models

### Setup Wizard State
```javascript
{
  currentStep: Number,           // 1-5
  experienceLevel: String,       // 'beginner', 'intermediate', 'advanced'
  foundMiners: Array,           // Discovered miners
  settings: {
    simple_mode: Boolean,
    alerts: {
      enabled: Boolean
    },
    default_view: String
  },
  preferences: {
    dashboard_layout: String,    // 'grid', 'list', 'dashboard'
    widgets: Array,             // Selected widget IDs
    desktop_notifications: Boolean,
    email_notifications: Boolean,
    email_address: String,      // New field
    accent_color: String,       // Theme-consistent color
    // ... other preferences
  }
}
```

### Navigation State
```javascript
{
  canGoBack: Boolean,
  canContinue: Boolean,
  isLastStep: Boolean,
  navigationVisible: Boolean    // Always true for static positioning
}
```

## Error Handling

### Navigation Errors
- **Stuck Navigation**: Ensure footer positioning is static, not fixed
- **Scroll Interference**: Remove any scroll event listeners that might block navigation
- **Button Responsiveness**: Verify click handlers are properly bound

### Asset Loading Errors
- **Missing Logos**: Fallback to default SVG if PNG/SVG assets not found
- **Path Resolution**: Use absolute paths for root directory assets
- **Component Integration**: Ensure all logo usage goes through `BitcoinLogo.vue`

### Selection State Errors
- **Widget Selection**: Validate `v-item-group` binding and selection persistence
- **Dropdown State**: Ensure proper z-index and overlay management
- **Form Validation**: Maintain form state during navigation

### Navigation Flow Errors
- **Route Resolution**: Verify dashboard route exists and is accessible
- **Setup Completion**: Ensure proper cleanup of wizard state
- **Data Persistence**: Validate localStorage operations

## Testing Strategy

### Unit Testing
1. **Component Isolation**: Test each wizard screen component independently
2. **Navigation Logic**: Test step progression and back navigation
3. **Asset Loading**: Verify logo component renders with correct assets
4. **Form Validation**: Test preference selection and validation

### Integration Testing
1. **Wizard Flow**: Complete end-to-end wizard navigation
2. **Asset Integration**: Verify all logos use consistent assets
3. **Theme Integration**: Test accent color application across components
4. **Navigation Integration**: Test dashboard launch functionality

### Visual Testing
1. **Progress Bar**: Verify orange color fills correctly
2. **Widget Selection**: Confirm visual feedback for selected widgets
3. **Dropdown Menus**: Test title visibility and contrast
4. **Information Bubbles**: Verify consistent styling across all screens

### Responsive Testing
1. **Mobile Navigation**: Test footer positioning on mobile devices
2. **Tablet Layout**: Verify wizard layout on medium screens
3. **Desktop Experience**: Confirm optimal layout on large screens

### Accessibility Testing
1. **Keyboard Navigation**: Ensure all interactive elements are keyboard accessible
2. **Screen Reader**: Test with screen readers for proper announcements
3. **Color Contrast**: Verify sufficient contrast in all UI elements
4. **Reduced Motion**: Test with reduced motion preferences

### Performance Testing
1. **Asset Loading**: Measure logo loading performance
2. **Component Rendering**: Test wizard screen transition performance
3. **Memory Usage**: Monitor for memory leaks during navigation
4. **Bundle Size**: Verify changes don't significantly increase bundle size