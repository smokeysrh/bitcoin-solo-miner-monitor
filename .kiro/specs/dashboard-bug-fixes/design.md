# Design Document

## Overview

This design document outlines the technical approach for fixing 9 critical bugs identified in the Bitcoin Solo Miner Monitoring dashboard application. The fixes focus on restoring existing functionality without introducing new features, ensuring proper debugging procedures, and maintaining application stability during the final testing phase.

The application is built using Vue.js 3 with Vuetify for the frontend, Python FastAPI for the backend, and follows a component-based architecture. All fixes will be implemented with minimal code changes to reduce the risk of introducing new bugs.

## Architecture

### Frontend Architecture
- **Framework**: Vue.js 3 with Composition API
- **UI Library**: Vuetify 3.4.4
- **State Management**: Currently disabled (Pinia temporarily removed)
- **Routing**: Vue Router 4
- **Build Tool**: Vite

### Backend Architecture
- **Framework**: Python FastAPI
- **Database**: SQLite for configuration, InfluxDB for time-series data
- **WebSocket**: Real-time communication for status updates
- **Services**: Modular service architecture with MinerManager, DataStorage, APIService

### Current Application State
The application is in "Phase 1 Testing" mode with several features temporarily disabled to prevent browser crashes and connection timeouts during testing. This context is important for understanding the current implementation.

## Components and Interfaces

### 1. Information Bubble Component Enhancement

**Current State**: Information bubbles ("?") exist but lack interactivity
**Target Component**: Create new `InfoBubble.vue` component or enhance existing elements

**Interface Design**:
```vue
<template>
  <v-tooltip>
    <template v-slot:activator="{ props }">
      <v-btn
        icon
        size="small"
        v-bind="props"
        @mouseenter="handleHover"
        @mouseleave="handleHoverEnd"
        @click="handleClick"
        :class="['info-bubble', { 'info-bubble--hovered': isHovered }]"
      >
        <v-icon>mdi-help-circle</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltipText }}</span>
  </v-tooltip>
</template>
```

**Styling Requirements**:
- Hover effects: size increase (scale 1.1) and color change
- Smooth transitions using CSS transforms
- Proper sizing to not overwhelm interface
- Click handlers for detailed information display

### 2. Dashboard Button Functionality Restoration

**Current State**: Buttons exist but lack connected functionality
**Target Files**: 
- `src/frontend/src/views/Dashboard.vue`
- `src/frontend/src/components/` (potential new components)

**Button Implementations**:

**Scan Network Button**:
```javascript
const scanNetwork = async () => {
  try {
    // Show loading state
    scanningNetwork.value = true;
    
    // Call backend API
    const response = await axios.post('/api/network/scan', {
      network_range: discoveryNetwork.value
    });
    
    // Update UI with results
    showSnackbar('Network scan completed', 'success');
  } catch (error) {
    showSnackbar(`Scan failed: ${error.message}`, 'error');
  } finally {
    scanningNetwork.value = false;
  }
};
```

**Add Miner Button**:
```javascript
const addMiner = () => {
  // Open existing add miner dialog
  addMinerDialog.value = true;
};
```

**Analytics Button**:
```javascript
const navigateToAnalytics = () => {
  router.push('/analytics');
};
```

### 3. Theme Switching System

**Current State**: Theme toggle exists but doesn't apply changes
**Target Files**: 
- `src/frontend/src/main.js` (Vuetify theme configuration)
- `src/frontend/src/App.vue` (theme application)
- `src/frontend/src/views/Settings.vue` (settings interface)

**Implementation Strategy**:
```javascript
// Theme watcher restoration
watch(() => settings.theme, (newTheme) => {
  // Apply theme to Vuetify
  vuetify.theme.global.name.value = newTheme;
  
  // Persist theme choice
  localStorage.setItem('theme', newTheme);
  
  // Update CSS custom properties if needed
  document.documentElement.setAttribute('data-theme', newTheme);
}, { immediate: true });
```

### 4. Simple Mode Toggle System

**Current State**: Toggle exists but doesn't change dashboard view
**Target Files**:
- `src/frontend/src/views/Settings.vue`
- `src/frontend/src/App.vue` (menu items computation)
- `src/frontend/src/router/index.js` (routing logic)

**Implementation Strategy**:
```javascript
const handleModeChange = (simpleMode) => {
  // Update localStorage
  localStorage.setItem('uiMode', simpleMode ? 'simple' : 'advanced');
  
  // Update reactive UI mode
  uiMode.value = simpleMode ? 'simple' : 'advanced';
  
  // Navigate to appropriate dashboard
  const targetRoute = simpleMode ? '/dashboard-simple' : '/';
  if (route.path !== targetRoute) {
    router.push(targetRoute);
  }
};
```

### 5. Footer Consistency System

**Current State**: Footer has inconsistent sizing across pages
**Target Files**: 
- `src/frontend/src/App.vue` (main footer)
- CSS styling across all page components

**Standardization Approach**:
```css
.footer-fixed {
  position: relative !important;
  bottom: auto !important;
  height: 64px !important; /* Standardized height */
  min-height: 64px !important;
  max-height: 64px !important;
  padding: 12px 16px !important; /* Consistent padding */
}
```

### 6. Mock Data Removal System

**Current State**: Mock miners displayed in dashboard
**Target Files**:
- `src/frontend/src/views/Dashboard.vue`
- Any backend mock data services

**Removal Strategy**:
```javascript
// Replace mock data with empty state
const miners = ref([]);

// Add empty state messaging
const showEmptyState = computed(() => miners.value.length === 0);
```

### 7. Status Indicator Restoration

**Current State**: Shows "Phase 1 Testing" instead of connection status
**Target Files**:
- `src/frontend/src/App.vue` (status display logic)
- `src/frontend/src/services/websocket.js` (connection management)

**Status Logic Restoration**:
```javascript
const connectionStatusText = computed(() => {
  switch (connectionStatus.value) {
    case 'connected': return 'Connected';
    case 'connecting': return 'Connecting';
    case 'reconnecting': return 'Reconnecting';
    case 'disconnected': return 'Disconnected';
    case 'error': return 'Connection Error';
    default: return 'Unknown';
  }
});
```

### 8. Refresh Button Functionality

**Current State**: Button disabled with mock message
**Target Files**:
- `src/frontend/src/App.vue` (refresh button handler)

**Functionality Restoration**:
```javascript
const refreshData = async () => {
  try {
    refreshing.value = true;
    
    // Force WebSocket reconnection if needed
    if (connectionStatus.value === 'disconnected' || connectionStatus.value === 'error') {
      forceReconnect();
    }
    
    // Refresh all data sources
    await Promise.all([
      // Add actual refresh calls here
    ]);
    
    showSnackbar('Data refreshed', 'success');
  } catch (error) {
    showSnackbar(`Refresh failed: ${error.message}`, 'error');
  } finally {
    refreshing.value = false;
  }
};
```

### 9. Temperature Display Formatting

**Current State**: Shows decimal values (e.g., 65.7°C)
**Target Files**:
- `src/frontend/src/views/Dashboard.vue`
- Any miner card components

**Formatting Function**:
```javascript
const formatTemperature = (temp) => {
  if (!temp || isNaN(temp)) return '0°C';
  return `${Math.round(temp)}°C`;
};
```

## Data Models

### Settings Data Model
```javascript
const settings = {
  theme: 'dark' | 'light',
  simple_mode: boolean,
  refresh_interval: number,
  // ... other settings
};
```

### Miner Data Model
```javascript
const miner = {
  id: string,
  name: string,
  type: string,
  ip_address: string,
  status: 'online' | 'offline' | 'error',
  hashrate: number,
  temperature: number, // Will be formatted as integer
  // ... other properties
};
```

### Connection Status Model
```javascript
const connectionStatus = 'connected' | 'connecting' | 'reconnecting' | 'disconnected' | 'error';
```

## Error Handling

### Graceful Degradation Strategy
1. **Network Errors**: Show user-friendly messages, maintain UI responsiveness
2. **Theme Application Errors**: Fall back to default theme
3. **Data Refresh Errors**: Show error message but don't break UI
4. **WebSocket Errors**: Implement automatic reconnection with exponential backoff

### Error Logging
```javascript
const logError = (context, error) => {
  console.error(`[${context}] Error:`, error);
  // Add structured logging if needed
};
```

### User Feedback
- Use Vuetify snackbar for non-critical errors
- Use dialog modals for critical errors requiring user action
- Provide clear, actionable error messages

## Testing Strategy

### Manual Testing Approach
Each bug fix will require comprehensive manual testing:

1. **Functionality Testing**: Verify the specific bug is fixed
2. **Regression Testing**: Ensure no existing functionality is broken
3. **Cross-browser Testing**: Test in Chrome, Firefox, Edge
4. **Responsive Testing**: Verify fixes work on different screen sizes

### Testing Checklist Template
```markdown
## Bug Fix Testing Checklist

### Pre-Testing Setup
- [ ] Application running on localhost:8000
- [ ] Browser developer tools open
- [ ] Screenshots taken of current state

### Functionality Testing
- [ ] Bug reproduction steps no longer produce the issue
- [ ] New functionality works as expected
- [ ] Error cases handled gracefully

### Regression Testing
- [ ] Navigation between pages works
- [ ] Other buttons/controls still function
- [ ] No console errors introduced
- [ ] Performance not degraded

### Documentation
- [ ] Screenshots of fixed functionality
- [ ] Any new issues discovered noted
```

### Debugging Tools Integration
- Use browser developer tools for CSS and JavaScript debugging
- Implement console logging for state changes during testing
- Use Vue DevTools for component state inspection

### Performance Considerations
- Minimize DOM manipulations
- Use CSS transforms for animations (better performance)
- Implement proper cleanup for event listeners
- Avoid memory leaks in reactive watchers

## Implementation Priority

### Phase 1: Critical UI Fixes
1. Information bubble functionality (Requirement 1)
2. Dashboard button functionality (Requirement 2)
3. Theme switching (Requirement 3)

### Phase 2: Mode and Display Fixes
4. Simple mode toggle (Requirement 4)
5. Footer consistency (Requirement 5)
6. Temperature formatting (Requirement 9)

### Phase 3: Data and Status Fixes
7. Mock data removal (Requirement 6)
8. Status indicator restoration (Requirement 7)
9. Refresh button functionality (Requirement 8)

## Security Considerations

### Input Validation
- Validate all user inputs in forms
- Sanitize data before display
- Implement proper error boundaries

### State Management
- Avoid storing sensitive data in localStorage
- Implement proper session management
- Use secure defaults for all settings

## Accessibility Compliance

### WCAG 2.1 Guidelines
- Maintain proper color contrast ratios
- Ensure keyboard navigation works
- Provide proper ARIA labels
- Support screen readers

### Implementation Details
- Use semantic HTML elements
- Implement focus management
- Provide alternative text for icons
- Ensure sufficient color contrast

This design provides a comprehensive technical roadmap for fixing all identified bugs while maintaining code quality and application stability.