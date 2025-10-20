# Design Document - Network Scan and Miner Display Fixes

## Overview

This design document outlines the technical approach for fixing critical bugs in the Network Scan functionality and miner display components of the Bitcoin Solo Miner Monitor application. The fixes address inconsistent dialog behavior, redundant UI elements, non-functional progress visualization, and inaccurate miner data display, particularly for NerdQaxe miners.

## Architecture

### Current System Architecture
- **Frontend**: Vue.js 3 with Vuetify component library
- **State Management**: Pinia stores for miners and settings
- **Network Scanning**: Composable-based network scan service (`useNetworkScan`)
- **Backend Communication**: REST API and WebSocket connections for real-time updates
- **Styling**: Vuetify theme system with custom CSS variables

### Affected Components
```
src/frontend/src/
├── views/
│   ├── Dashboard.vue (Network Discovery section + NetworkScanner dialog)
│   ├── SimpleDashboard.vue (NetworkScanner dialog)
│   └── MinerDetail.vue (Efficiency calculation, model display, temperature)
├── components/
│   ├── QuickActions.vue (NetworkScanner dialog trigger)
│   └── NetworkScanner.vue (Progress bar, dialog implementation)
├── composables/
│   └── useNetworkScan.js (Network scanning logic)
└── stores/
    └── miners.js (Miner data management, type detection)
```

## Components and Interfaces

### 1. Consistent Network Scan Dialog Display

#### Problem Analysis
The NetworkScanner dialog is embedded in multiple locations:
- `Dashboard.vue`: Has its own `networkScannerDialog` ref and `<v-dialog>` wrapper
- `SimpleDashboard.vue`: Has its own `networkScannerDialog` ref and `<v-dialog>` wrapper
- `QuickActions.vue`: Has its own `networkScannerDialog` ref and `<v-dialog>` wrapper
- Empty state buttons in Dashboard: Call `startDiscovery()` which doesn't open the dialog

This creates inconsistent behavior where some buttons open the dialog and others don't.

#### Solution Design
**Centralized Dialog Management**:
- Keep the NetworkScanner dialog in `QuickActions.vue` as the single source of truth
- Remove duplicate dialog implementations from `Dashboard.vue` and `SimpleDashboard.vue`
- Update empty state "Scan Network" buttons to emit events that trigger the QuickActions dialog
- Ensure all network scan entry points use the same dialog instance

**Implementation Strategy**:
```javascript
// Dashboard.vue - Remove duplicate dialog, use QuickActions
const handleQuickScanNetwork = () => {
  // QuickActions component handles dialog display
}

const startDiscovery = () => {
  // Delegate to QuickActions scan network handler
  handleQuickScanNetwork()
}

// Empty state button
<v-btn @click="handleQuickScanNetwork">Scan Network</v-btn>
```

### 2. Remove Duplicate Network Discovery Section

#### Problem Analysis
The Dashboard has two network discovery interfaces:
1. **Quick Actions Section** (line 68-77): Modern, consistent UI with dialog-based scanning
2. **Network Discovery Section** (line 196-289): Legacy form-based interface at bottom of page

The legacy section duplicates functionality and creates confusion.

#### Solution Design
**Complete Removal Strategy**:
- Remove the entire "Network Discovery Section" from `Dashboard.vue` (lines 196-289)
- Remove associated reactive state:
  - `discoveryForm` ref
  - `discoveryFormValid` ref
  - `discoveryNetwork` ref (keep for QuickActions prop)
  - `discoveryLoading` ref
  - `discoveryStatus` ref
- Remove methods:
  - `startDiscovery()` method (replace with delegation to QuickActions)
  - `pollDiscoveryStatus()` method
  - `addDiscoveredMiner()` method (functionality exists in NetworkScanner)
- Update empty state buttons to use QuickActions dialog

**Code Cleanup**:
```vue
<!-- REMOVE THIS ENTIRE SECTION -->
<!-- Network Discovery Section -->
<v-row class="mt-4">
  <v-col cols="12">
    <v-card>
      <!-- ... entire legacy discovery form ... -->
    </v-card>
  </v-col>
</v-row>
```

### 3. Functional Network Scan Progress Bar

#### Problem Analysis
In `NetworkScanner.vue`, the progress bar is defined as:
```vue
<v-progress-linear
  :value="scanProgress.percentage"
  color="primary"
  height="20"
  striped
  class="mb-2"
>
```

The `scanProgress` object comes from the `useNetworkScan` composable. The issue is likely:
1. The `percentage` value is updating correctly (counter works)
2. But the progress bar color fill is not rendering
3. Possible CSS override or Vuetify theme issue preventing color display

#### Solution Design
**Diagnosis and Fix Strategy**:
1. **Verify Data Flow**: Ensure `scanProgress.percentage` is a number between 0-100
2. **CSS Investigation**: Check for CSS overrides blocking the progress bar fill color
3. **Vuetify Configuration**: Verify `v-progress-linear` color prop is properly applied
4. **Theme Variables**: Ensure `--color-primary` CSS variable is defined and accessible

**Potential Fixes**:
```vue
<!-- Option 1: Explicit color value -->
<v-progress-linear
  :model-value="scanProgress.percentage"
  color="primary"
  bg-color="grey-lighten-3"
  height="20"
  class="mb-2"
>
  <template v-slot:default="{ value }">
    <strong>{{ Math.ceil(value) }}%</strong>
  </template>
</v-progress-linear>

<!-- Option 2: Inline style override if CSS is blocking -->
<v-progress-linear
  :model-value="scanProgress.percentage"
  height="20"
  class="mb-2 scan-progress-bar"
>
  <template v-slot:default="{ value }">
    <strong>{{ Math.ceil(value) }}%</strong>
  </template>
</v-progress-linear>

<style scoped>
.scan-progress-bar :deep(.v-progress-linear__determinate) {
  background-color: var(--color-primary) !important;
}
</style>
```

**Composable Verification**:
Ensure `useNetworkScan.js` properly updates percentage:
```javascript
const scanProgress = ref({
  visible: false,
  percentage: 0,  // Must be 0-100
  statusText: '',
  scannedHosts: 0,
  totalHosts: 0,
  foundCount: 0
})

// Update logic
scanProgress.value.percentage = (scannedHosts / totalHosts) * 100
```

### 4. Accurate NerdQaxe Miner Display

#### Problem Analysis
**Name Column Issue**: Shows "NerdQaxe_" with trailing underscore
**Type Column Issue**: Shows "bitaxe" instead of "NerdQaxe"

The issue is in miner type detection logic. NerdQaxe miners are based on Bitaxe firmware but should be distinguished.

#### Solution Design
**Miner Type Detection Enhancement**:

Location: `src/backend/services/miner_service.py` or equivalent detection logic

```python
def detect_miner_type(device_info, api_response):
    """
    Enhanced miner type detection with NerdQaxe support
    """
    # Check for NerdQaxe-specific identifiers
    if 'nerdqaxe' in str(device_info.get('model', '')).lower():
        return 'NerdQaxe'
    
    if 'nerdqaxe' in str(api_response.get('version', '')).lower():
        return 'NerdQaxe'
    
    # Check device name/hostname
    hostname = device_info.get('hostname', '').lower()
    if 'nerdqaxe' in hostname or 'nerd-qaxe' in hostname:
        return 'NerdQaxe'
    
    # Fallback to Bitaxe if it matches Bitaxe patterns
    if 'bitaxe' in str(device_info.get('model', '')).lower():
        return 'Bitaxe'
    
    return 'Unknown'

def clean_miner_name(name):
    """
    Remove trailing underscores and clean up miner names
    """
    if not name:
        return name
    
    # Remove trailing underscores
    name = name.rstrip('_')
    
    # Remove trailing whitespace
    name = name.strip()
    
    return name
```

**Frontend Display Logic**:
```javascript
// In miners store or component
const displayMinerName = (miner) => {
  let name = miner.name || miner.type
  // Remove trailing underscores
  return name.replace(/_+$/, '')
}

const displayMinerType = (miner) => {
  // Use the detected type from backend
  return miner.type || 'Unknown'
}
```

### 5. Accurate Temperature Display for NerdQaxe

#### Problem Analysis
Temperature shows "0" in the Miner Status table but displays correctly on the detail page. This indicates:
1. Temperature data IS being retrieved from the API
2. The mapping/parsing in the table view is incorrect
3. The detail page uses a different data path that works

#### Solution Design
**Data Flow Investigation**:
```
API Response → Miners Store → Dashboard Table → Display
                            ↓
                     MinerDetail Page → Display (works)
```

**Temperature Field Mapping**:
Location: `Dashboard.vue` temperature column template

Current implementation:
```vue
<template v-slot:item.temperature="{ item }">
  <v-progress-linear
    :value="item.temperature"
    :color="getTemperatureColor(item.temperature)"
    height="20"
  >
    <template v-slot:default="{ value }">
      <strong>{{ formatTemperature(value) }}</strong>
    </template>
  </v-progress-linear>
</template>
```

**Potential Issues**:
1. `item.temperature` might be nested in `item.device_info.temperature`
2. Temperature might be in a different field for NerdQaxe
3. Data type mismatch (string vs number)

**Solution**:
```javascript
// In miners store - normalize temperature field
const normalizeMinerData = (minerData) => {
  return {
    ...minerData,
    temperature: extractTemperature(minerData),
    // ... other fields
  }
}

const extractTemperature = (minerData) => {
  // Try multiple possible temperature field locations
  const temp = minerData.temperature 
    || minerData.device_info?.temperature
    || minerData.temp
    || minerData.device_info?.temp
    || 0
  
  // Ensure it's a number
  return typeof temp === 'number' ? temp : parseFloat(temp) || 0
}
```

### 6. Correct Model Name Display on Miner Detail Page

#### Problem Analysis
In `MinerDetail.vue`, the model is retrieved via:
```javascript
const getDeviceInfo = (key) => {
  if (!miner.value) return "N/A";
  
  if (miner.value[key]) return miner.value[key];
  
  // Check in device_info if available
  if (miner.value.device_info && miner.value.device_info[key]) {
    return miner.value.device_info[key];
  }
  
  return "N/A";
}
```

For NerdQaxe, the model field might be:
- Empty/null in both locations
- Named differently (e.g., `device_model`, `hardware_model`)
- Needs to fallback to type name

#### Solution Design
**Enhanced Device Info Retrieval**:
```javascript
const getDeviceInfo = (key) => {
  if (!miner.value) return "N/A";
  
  // Direct property check
  if (miner.value[key]) return miner.value[key];
  
  // Check in device_info
  if (miner.value.device_info && miner.value.device_info[key]) {
    return miner.value.device_info[key];
  }
  
  // Special handling for model field
  if (key === 'model') {
    // Try alternative field names
    const modelAliases = [
      'device_model',
      'hardware_model',
      'product_name',
      'model_name'
    ]
    
    for (const alias of modelAliases) {
      if (miner.value[alias]) return miner.value[alias]
      if (miner.value.device_info?.[alias]) return miner.value.device_info[alias]
    }
    
    // Fallback to type name for NerdQaxe
    if (miner.value.type === 'NerdQaxe') {
      return 'NerdQaxe'
    }
    
    // Fallback to type for other miners
    if (miner.value.type) {
      return miner.value.type
    }
  }
  
  return "N/A";
}
```

### 7. Correct Efficiency Metric Calculation and Display

#### Problem Analysis
Current implementation in `MinerDetail.vue`:
```javascript
const calculateEfficiency = (hashrate, power) => {
  if (!hashrate || !power || power === 0) return "N/A";
  
  // Convert to TH/s per watt
  const efficiency = hashrate / power / 1000000000;
  
  return `${efficiency.toFixed(6)} TH/s/W`;
};
```

**Issues**:
1. **Formula is inverted**: Shows TH/s/W (hashrate per watt) instead of W/TH (watts per terahash)
2. **Industry standard**: Efficiency is measured as W/TH (lower is better)
3. **Conversion factor**: Hashrate needs proper unit conversion to TH/s first

#### Solution Design
**Corrected Efficiency Calculation**:
```javascript
const calculateEfficiency = (hashrate, power) => {
  if (!hashrate || !power || power === 0) return "N/A";
  
  // Convert hashrate to TH/s
  // Assuming hashrate is in H/s (hashes per second)
  const hashrateInTH = hashrate / 1000000000000; // 1 TH = 10^12 H
  
  if (hashrateInTH === 0) return "N/A";
  
  // Calculate efficiency as watts per terahash (W/TH)
  // Lower values are better
  const efficiency = power / hashrateInTH;
  
  return `${efficiency.toFixed(2)} W/TH`;
};
```

**Alternative with Unit Detection**:
```javascript
const calculateEfficiency = (hashrate, power, hashrateUnit = 'H/s') => {
  if (!hashrate || !power || power === 0) return "N/A";
  
  // Convert to TH/s based on current unit
  let hashrateInTH;
  switch(hashrateUnit) {
    case 'TH/s':
      hashrateInTH = hashrate;
      break;
    case 'GH/s':
      hashrateInTH = hashrate / 1000;
      break;
    case 'MH/s':
      hashrateInTH = hashrate / 1000000;
      break;
    case 'H/s':
    default:
      hashrateInTH = hashrate / 1000000000000;
  }
  
  if (hashrateInTH === 0) return "N/A";
  
  // Efficiency = Power (W) / Hashrate (TH/s)
  const efficiency = power / hashrateInTH;
  
  return `${efficiency.toFixed(2)} W/TH`;
};
```

## Data Models

### Miner Data Model Enhancement
```javascript
interface Miner {
  id: string;
  name: string;  // Cleaned, no trailing underscores
  type: string;  // 'NerdQaxe' | 'Bitaxe' | 'Avalon Nano' | etc.
  ip_address: string;
  port: number;
  status: 'online' | 'offline' | 'restarting' | 'error';
  
  // Performance metrics
  hashrate: number;  // in H/s
  temperature: number;  // in Celsius, normalized from various sources
  power: number;  // in Watts
  fan_speed: number;  // percentage
  
  // Device information
  device_info: {
    model: string;  // Device model name
    firmware_version: string;
    mac_address: string;
    hostname: string;
    // ... other device-specific fields
  };
  
  // Calculated fields
  efficiency: string;  // Formatted as "X.XX W/TH"
  
  // Timestamps
  added_at: string;
  last_updated: string;
  uptime: number;  // in seconds
}
```

### Network Scan Progress Model
```javascript
interface ScanProgress {
  visible: boolean;
  percentage: number;  // 0-100, must be numeric
  statusText: string;
  scannedHosts: number;
  totalHosts: number;
  foundCount: number;
  currentIP?: string;
}
```

## Error Handling

### Temperature Data Errors
- **Missing Data**: Return 0 and log warning, don't crash display
- **Invalid Format**: Parse and convert, fallback to 0
- **API Timeout**: Show last known value with staleness indicator

### Efficiency Calculation Errors
- **Division by Zero**: Return "N/A" when power is 0
- **Invalid Hashrate**: Return "N/A" when hashrate is 0 or negative
- **Missing Data**: Return "N/A" gracefully

### Miner Type Detection Errors
- **Unknown Type**: Fallback to "Unknown" instead of crashing
- **Missing Device Info**: Use available data, don't require all fields
- **API Response Variations**: Handle multiple response formats

## Testing Strategy

### Unit Testing
- **Efficiency Calculation**: Test with various hashrate/power combinations
- **Temperature Extraction**: Test with different data structures
- **Name Cleaning**: Test removal of trailing underscores
- **Type Detection**: Test NerdQaxe vs Bitaxe differentiation

### Integration Testing
- **Network Scan Dialog**: Verify all entry points open the same dialog
- **Progress Bar**: Verify color fill updates with percentage
- **Miner Display**: Verify NerdQaxe shows correct name, type, temp, model
- **Efficiency Display**: Verify W/TH calculation and display

### Visual Testing
- **Progress Bar Color**: Verify blue fill appears and grows
- **Dialog Consistency**: Verify same dialog appearance from all buttons
- **Temperature Display**: Verify non-zero values in table
- **Model Display**: Verify "NerdQaxe" instead of "N/A"

## Performance Considerations

### Optimization Strategies
- **Miner Data Normalization**: Normalize once in store, not in every component
- **Temperature Caching**: Cache extracted temperature values
- **Type Detection**: Cache detection results, don't re-detect on every render
- **Dialog Reuse**: Single dialog instance reduces memory usage

### Monitoring
- **Progress Bar Updates**: Ensure smooth updates without excessive re-renders
- **Data Extraction**: Monitor performance of temperature/model extraction
- **Type Detection**: Log detection results for debugging

## Security Considerations

### Data Validation
- **Temperature Values**: Validate range (0-150°C) to prevent display issues
- **Efficiency Values**: Validate positive numbers only
- **Miner Names**: Sanitize to prevent XSS in name display
- **Type Detection**: Validate against known types list

### API Response Handling
- **Malformed Data**: Handle gracefully without crashing
- **Missing Fields**: Use safe defaults
- **Type Coercion**: Safely convert strings to numbers

## Implementation Priority

### Phase 1: Critical Fixes (High Priority)
1. Fix Network Scan dialog consistency (all buttons open same dialog)
2. Fix progress bar color fill visualization
3. Fix NerdQaxe type detection and display

### Phase 2: Data Display Fixes (Medium Priority)
4. Fix temperature display in Miner Status table
5. Fix model name display on detail page
6. Fix efficiency calculation (W/TH instead of TH/s/W)

### Phase 3: Cleanup (Low Priority)
7. Remove duplicate Network Discovery section from Dashboard

## Migration Notes

### Breaking Changes
- None - all fixes are backwards compatible

### Data Migration
- No database changes required
- Existing miner data will display correctly after fixes

### Rollback Plan
- All changes are in frontend components
- Can rollback individual component files if issues arise
- No backend changes required for most fixes
